"""public-web shows reports in the visitor's language, and decides the same in every language.

Core shows a product in the language asked for with ``lang``: ``value`` is what to show, and a
choice constant keeps the value it was written with in ``source_value``. What the app decides
on - the TLP, events, whether to parse versions - must read the written value, or a translated
"CLEAR" would hide a report. Reports are cached per language, and a language picked with
``?lang=`` is carried into the page's links.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from cachelib import SimpleCache
from flask import Flask, g, url_for
from lib.report.report_item import EventsGeneration
from lib.report.vulnerability_report import VulnerabilityReport
from lib.web import cache as web_cache
from lib.web import site as web_site
from lib.web.taranis_client import TaranisClient

if TYPE_CHECKING:
    from types import ModuleType


def _attribute(key: str, value: str, source_value: str | None = None, attribute_type: str = "STRING") -> dict:
    attribute = {"key": key, "type": attribute_type, "value": value, "description": None}
    if source_value is not None:
        attribute["source_value"] = source_value
    return attribute


def _slovak_product() -> dict:
    """A Czech report shown in Slovak, with translated constants and a translated affected system."""
    intro = {
        "title": "Úvod",
        "type": "Vulnerability Report - Intro",
        "attributes": [
            _attribute("description", "Prehľad"),
            _attribute("tlp", "TLP:CLEAR (sk)", "CLEAR", "ENUM"),
            _attribute("generate_events", "generovať", "generate", "RADIO"),
        ],
    }
    item = {
        "title": "Chyba v jadre",
        "type": "Vulnerability Report",
        "attributes": [
            _attribute("description", "Útočník môže spustiť kód."),
            _attribute("tlp", "TLP:CLEAR (sk)", "CLEAR", "ENUM"),
            # Translated by hand into something that no longer parses; the written one does.
            _attribute("affected_systems", "Linux: jadro; verzie pred 6.1", "Linux: kernel; <6.1"),
            _attribute("affected_versions_parsability", "Parsovať", "Parse", "RADIO"),
        ],
    }
    return {
        "id": 7,
        "title": "Bulletin (sk)",
        "description": "",
        "links": [],
        "created": "2026-10-01T10:00:00",
        "user": {"name": "Analyst", "username": "analyst"},
        "report_items": [intro, item],
        "language": "sk",
        "available_languages": ["cs", "sk"],
    }


def test_decisions_read_what_was_written_and_the_page_shows_the_translation() -> None:
    report = VulnerabilityReport.from_dict(_slovak_product())

    assert report.get_tlp() == "CLEAR"
    assert report.should_generate_events() == EventsGeneration.GENERATE
    item = report.get_report_items()[0]
    assert item.should_search()
    assert item.get_product_display(1) == "jadro (linux)"
    assert report.get_language() == "sk"


def test_a_core_without_languages_is_read_as_before() -> None:
    product = _slovak_product()
    for item in product["report_items"]:
        for attribute in item["attributes"]:
            attribute["value"] = attribute.pop("source_value", attribute["value"])
    del product["language"], product["available_languages"]

    report = VulnerabilityReport.from_dict(product)

    assert report.get_tlp() == "CLEAR"
    assert report.get_language() is None


class _Response:
    status_code = 200

    @staticmethod
    def json() -> dict:
        return _slovak_product()


def test_the_client_asks_core_for_the_language() -> None:
    client = TaranisClient("https://core.example", "key")
    calls: list[dict] = []
    client._session.get = lambda url, **kwargs: calls.append({"url": url, **kwargs}) or _Response()

    client.get_product(7, web_id=3, language="sk")
    client.get_product(7)

    assert calls[0]["params"] == {"web_id": 3, "lang": "sk"}
    assert calls[1]["params"] is None


class _Client:
    """Core as the cache sees it: one product, shown in whatever language is asked for."""

    def __init__(self) -> None:
        self.languages: list[str | None] = []

    @staticmethod
    def list_published_product_ids(limit: int, web_id: int | None = None) -> list[int]:  # noqa: ARG004
        return [7]

    def get_product(self, product_id: int, web_id: int | None = None, language: str | None = None) -> dict:  # noqa: ARG002
        self.languages.append(language)
        return {**_slovak_product(), "title": f"Bulletin ({language})", "language": language}


def test_reports_are_cached_per_language(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(web_cache, "FileSystemCache", lambda **_options: SimpleCache())
    client = _Client()
    cache = web_cache.WebCache(client)

    assert cache.get_all_reports(3, "sk")[0].get_title() == "Bulletin (sk)"
    assert cache.get_all_reports(3, "en")[0].get_title() == "Bulletin (en)"
    assert cache.get_report("7", 3, "sk").get_title() == "Bulletin (sk)"
    assert client.languages == ["sk", "en"]


WEB = {"id": 3, "hostname": "feed.example", "config": {"languages": ["cs", "en", "sk"], "default_language": "cs"}}


@pytest.mark.parametrize(
    ("query", "accept", "expected"),
    [
        ("?lang=sk", "en", ("sk", True)),
        ("", "en", ("en", False)),
        ("?lang=de", "", ("cs", False)),
        # Not a language tag: it names a catalog file and would be carried into links.
        ("?lang=../../x", "", ("cs", False)),
    ],
)
def test_the_language_is_picked_from_the_url_then_the_browser(query: str, accept: str, expected: tuple) -> None:
    app = Flask(__name__)
    with app.test_request_context(f"/{query}", headers={"Accept-Language": accept, "Host": "feed.example"}):
        site = web_site.load_site([WEB])

        assert (site.language, site.chosen) == expected


@pytest.fixture
def routes(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """The app's routes, with the reports cache in memory rather than under /tmp."""
    monkeypatch.setattr(web_cache, "FileSystemCache", lambda **_options: SimpleCache())
    # Its client is made on import too, and needs the node's ApiKey.
    monkeypatch.setenv("PUBLIC_WEB_API_KEY", "test-key")
    from lib.web import routes  # noqa: PLC0415 - its cache is made on import

    return routes


def test_a_language_picked_in_the_url_lasts_beyond_one_page(routes: ModuleType) -> None:
    app = Flask(__name__)
    app.register_blueprint(routes.reports_bp)
    with app.test_request_context("/?lang=sk"):
        g.site = web_site.SiteContext(WEB, "sk", chosen=True)

        assert url_for("reports.show", report_id=7) == "/reports/7?lang=sk"
        assert url_for("reports.home", page=2) == "/?page=2&lang=sk"
        assert url_for("reports.branding", kind="logo") == "/branding/logo"

        g.site = web_site.SiteContext(WEB, "sk")
        assert url_for("reports.show", report_id=7) == "/reports/7"
