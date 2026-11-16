"""Pages and images a visitor already has are answered with an empty 304.

A browser asking again sends the ETag it got (``If-None-Match``); while the page is the same,
it gets "not modified" and shows what it has. The ETag digests the page as made, so a changed
report, another language or another cookie makes a new one. The feeds have their own (see
test_feeds.py).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import SimpleNamespace

HOST = {"Host": "localhost"}


def _again(site_client: SimpleNamespace, path: str, etag: str, **headers: str):  # noqa: ANN202
    return site_client.client.get(path, headers={**HOST, "If-None-Match": etag, **headers})


@pytest.mark.parametrize("path", ["/", "/reports/101", "/?lang=cs", "/?search=tomcat"])
def test_a_page_the_browser_has_is_not_sent_again(site_client: SimpleNamespace, path: str) -> None:
    first = site_client.client.get(path, headers=HOST)
    again = _again(site_client, path, first.headers["ETag"])

    assert first.status_code == 200
    # Kept by the browser only, and asked for every time.
    assert first.headers["Cache-Control"] == "private, no-cache"
    assert (again.status_code, again.data) == (304, b"")


def test_another_language_is_another_page(site_client: SimpleNamespace) -> None:
    english = site_client.client.get("/reports/101", headers=HOST)

    czech = _again(site_client, "/reports/101?lang=cs", english.headers["ETag"])

    assert czech.status_code == 200
    assert czech.headers["ETag"] != english.headers["ETag"]


def test_a_changed_report_is_sent_again(site_client: SimpleNamespace) -> None:
    first = site_client.client.get("/reports/101", headers=HOST)
    site_client.fake.products[101]["title"] = "Critical vulnerabilities in Apache products, updated"
    site_client.cache.clear()

    again = _again(site_client, "/reports/101", first.headers["ETag"])

    assert again.status_code == 200
    assert "updated" in again.text


def test_an_uploaded_image_the_browser_has_is_not_sent_again(site_client: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(site_client.fake, "get_web_image", lambda _web_id, _kind: (b"\x89PNG logo", "image/png"))

    first = site_client.client.get("/branding/logo", headers=HOST)
    again = _again(site_client, "/branding/logo", first.headers["ETag"])

    assert (first.status_code, first.data) == (200, b"\x89PNG logo")
    assert "Cache-Control" not in first.headers
    assert (again.status_code, again.data) == (304, b"")


def test_an_error_page_has_no_etag(site_client: SimpleNamespace) -> None:
    missing = site_client.client.get("/reports/999", headers=HOST)

    assert missing.status_code == 404
    assert "ETag" not in missing.headers


def test_the_feeds_keep_their_own(site_client: SimpleNamespace) -> None:
    feed = site_client.client.get("/atom", headers=HOST)

    assert feed.headers["Cache-Control"] == "public, no-cache"
    assert feed.headers["Last-Modified"]
    assert _again(site_client, "/atom", feed.headers["ETag"]).status_code == 304
