"""public-web shows every published product, and visitors don't wait while it loads them all.

The products come from core a page at a time. Once loaded, they stay cached: older than the TTL,
they are still shown while they load again in the background. After a reset (core says something
changed), they are loaded again before anyone sees them, and a load that started before the reset
is not kept, as it may show a product unpublished since.
"""

from __future__ import annotations

import threading

import pytest
from cachelib import SimpleCache
from flask import Flask, g
from lib import config
from lib.web import cache as web_cache
from lib.web import site as web_site


def _attribute(key: str, value: str, attribute_type: str = "STRING") -> dict:
    return {"key": key, "type": attribute_type, "value": value, "description": None}


def _product(product_id: int, title: str = "Bulletin") -> dict:
    intro = {
        "title": "Intro",
        "type": "Vulnerability Report - Intro",
        "attributes": [
            _attribute("description", "Overview"),
            _attribute("tlp", "CLEAR", "ENUM"),
            _attribute("generate_events", "generate", "RADIO"),
        ],
    }
    item = {
        "title": "Kernel bug",
        "type": "Vulnerability Report",
        "attributes": [
            _attribute("description", "An attacker can run code."),
            _attribute("tlp", "CLEAR", "ENUM"),
            _attribute("affected_systems", "Linux: kernel; <6.1"),
            _attribute("affected_versions_parsability", "Parse", "RADIO"),
        ],
    }
    return {
        "id": product_id,
        "title": f"{title} {product_id}",
        "description": "",
        "links": [],
        "created": "2026-10-01T10:00:00",
        "user": {"name": "Analyst", "username": "analyst"},
        "report_items": [intro, item],
    }


class _Core:
    """Core with ``count`` published products, newest first, that pages them."""

    def __init__(self, count: int, title: str = "Bulletin") -> None:
        self.products = [_product(product_id, title) for product_id in range(count, 0, -1)]
        self.pages: list[tuple[int, int]] = []
        self.one_by_one: list[int] = []
        self.loading: threading.Event | None = None

    def list_published_products(self, offset: int, limit: int, **_options: object) -> tuple[list[dict], int]:
        if self.loading is not None:
            self.loading.wait(5)
        self.pages.append((offset, limit))
        return self.products[offset : offset + limit], len(self.products)

    def list_published_product_ids(self, limit: int, web_id: int | None = None) -> list[int]:  # noqa: ARG002
        return [product["id"] for product in self.products[:limit]]

    def get_product(self, product_id: int, web_id: int | None = None, language: str | None = None) -> dict:  # noqa: ARG002
        self.one_by_one.append(product_id)
        return next(product for product in self.products if product["id"] == product_id)


class _OldCore(_Core):
    """Core from before paging: it ignores offset and ``full``, and lists ids and titles only."""

    def list_published_products(self, offset: int, limit: int, **_options: object) -> tuple[list[dict], int]:
        self.pages.append((offset, limit))
        page = [{"id": product["id"], "title": product["title"]} for product in self.products[:limit]]
        return page, len(page)


@pytest.fixture(autouse=True)
def _in_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    shared = SimpleCache()
    monkeypatch.setattr(web_cache, "FileSystemCache", lambda **_options: shared)
    monkeypatch.delenv("PUBLIC_WEB_MAX_REPORTS", raising=False)
    monkeypatch.setattr(web_cache, "_asked", set())
    monkeypatch.setattr(web_cache, "_remembered", {})


def _ids(reports: list) -> list[int]:
    return [int(report.get_id()) for report in reports]


def _join_loads() -> None:
    for thread in threading.enumerate():
        if thread is not threading.current_thread() and thread.daemon:
            thread.join(5)


def test_every_published_product_is_shown_newest_first() -> None:
    core = _Core(250)

    reports = web_cache.WebCache(core).get_all_reports(1, "en")

    assert _ids(reports) == list(range(250, 0, -1))
    assert core.pages == [(0, 100), (100, 100), (200, 100)]
    assert core.one_by_one == []


def test_the_rss_feed_has_every_published_product(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUBLIC_WEB_API_KEY", "test-key")
    from lib.web import routes  # noqa: PLC0415 - its cache is made on import, with the key set above

    monkeypatch.setattr(routes, "cache", web_cache.WebCache(_Core(40)))
    app = Flask(__name__)
    app.register_blueprint(routes.reports_bp)
    with app.test_request_context("/rss"):
        g.site = web_site.SiteContext({"id": 1, "hostname": "https://feed.example", "config": {"max_reports_homepage": 10}}, "en")
        feed = routes.rss().get_data(as_text=True)

    assert feed.count("<item>") == 40


def test_an_operator_can_still_cap_them(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUBLIC_WEB_MAX_REPORTS", "150")
    core = _Core(250)

    reports = web_cache.WebCache(core).get_all_reports(1, "en")

    assert _ids(reports) == list(range(250, 100, -1))
    assert core.pages == [(0, 100), (100, 50)]


def test_a_core_that_does_not_page_is_asked_one_product_at_a_time() -> None:
    core = _OldCore(250)

    reports = web_cache.WebCache(core).get_all_reports(1, "en")

    assert _ids(reports) == list(range(250, 50, -1))
    assert core.one_by_one == list(range(250, 50, -1))


def test_reports_are_loaded_once_and_then_read_from_the_cache() -> None:
    core = _Core(3)
    cache = web_cache.WebCache(core)

    assert _ids(cache.get_all_reports(1, "en")) == [3, 2, 1]
    assert _ids(cache.get_all_reports(1, "en")) == [3, 2, 1]
    assert cache.get_report("2", 1, "en").get_title() == "Bulletin 2"
    assert len(core.pages) == 1


def test_out_of_date_reports_are_shown_while_they_load_again(monkeypatch: pytest.MonkeyPatch) -> None:
    core = _Core(3)
    cache = web_cache.WebCache(core)
    cache.get_all_reports(1, "en")
    core.products = [_product(4), *core.products]
    monkeypatch.setattr(config, "cache_ttl", lambda: 0)

    assert _ids(cache.get_all_reports(1, "en")) == [3, 2, 1]
    _join_loads()
    monkeypatch.setattr(config, "cache_ttl", lambda: 3600)
    assert _ids(cache.get_all_reports(1, "en")) == [4, 3, 2, 1]


def test_after_a_reset_nobody_sees_the_reports_from_before_it() -> None:
    core = _Core(3)
    site = web_cache.WebCache(core)
    management = web_cache.WebCache(core)
    site.get_all_reports(1, "en")

    # A product is unpublished, so core resets the node: it loads the reports again right away.
    core.products = core.products[1:]
    management.clear()
    _join_loads()

    assert _ids(site.get_all_reports(1, "en")) == [2, 1]


def test_a_load_that_started_before_a_reset_is_not_kept() -> None:
    core = _Core(3, title="Before")
    cache = web_cache.WebCache(core)
    core.loading = threading.Event()
    load = threading.Thread(target=cache.get_all_reports, args=(1, "en"), daemon=True)
    load.start()

    while not web_cache._lock(f"{web_cache.CACHE_KEY_ALL_REPORTS}:1:en").locked():
        threading.Event().wait(0.01)
    cache.clear()
    core.products = [_product(2, "After"), _product(1, "After")]
    core.loading.set()
    load.join(5)
    _join_loads()

    assert [report.get_title() for report in cache.get_all_reports(1, "en")] == ["After 2", "After 1"]
