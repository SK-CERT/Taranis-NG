"""The RSS and Atom feeds say when each report was published and last changed.

A feed reader sorts by these dates, shows how old an item is and tells new items from those it
has seen. RSS gives an item's publication as ``pubDate`` (RFC 822) and the channel's last change
as ``lastBuildDate``; Atom gives ``published`` and ``updated`` (RFC 3339) for every entry and an
``updated`` for the feed. Core sends the dates with their offset; a core from before it recorded
them sends only when a product was created, in its local time without one.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from flask import Flask, g
from flask import request as flask_request
from lib.report.product import build_product
from lib.web import site as web_site

ATOM = "{http://www.w3.org/2005/Atom}"
PRAGUE = ZoneInfo("Europe/Prague")


def _report(product_id: int, author: str | None = None, **dates: str) -> dict:
    user = {"name": author} if author else None
    return build_product({"id": product_id, "title": f"Bulletin {product_id}", "links": [], "report_items": [], "user": user, **dates})


class _Cache:
    """The reports the feed lists, newest first, a renderer for their text, and the feeds made."""

    def __init__(self, reports: list[dict]) -> None:
        self.reports = reports
        self.feeds: dict[str, dict] = {}

    def get_all_reports(self, _web_id: int, _language: str) -> list[dict]:
        return self.reports

    def renderer(self, _web_id: int) -> SimpleNamespace:
        return SimpleNamespace(
            render_text=lambda report, **_options: f"About {report['title']}",
            render=lambda report, _view, **_options: f'<p>All about <a href="/reports/{report["id"]}">{report["title"]}</a></p>',
        )

    def get_feed(self, key: str) -> dict | None:
        return self.feeds.get(key)

    def set_feed(self, key: str, feed: dict) -> None:
        self.feeds[key] = feed


WEB_CONFIG = {
    "languages": ["en", "cs"],
    "default_language": "en",
    "organization": "Example CERT",
    "organization_url": "https://cert.example",
}


@pytest.fixture
def respond(monkeypatch: pytest.MonkeyPatch):  # noqa: ANN201
    """Answer a request for a feed (``rss`` or ``atom``) of the given reports; returns the response.

    ``query`` is the request's query string, ``headers`` its headers, ``config`` what the web's
    configuration adds or changes, and ``cache`` the node's cache (a fresh one by default).
    """
    monkeypatch.setenv("PUBLIC_WEB_API_KEY", "test-key")
    from lib.web import feeds, routes  # noqa: PLC0415 - routes' cache is made on import, with the key set above

    monkeypatch.setattr(feeds, "TZ", PRAGUE)
    app = Flask(__name__)
    app.register_blueprint(routes.reports_bp)

    def _respond(kind: str, *reports: dict, query: str = "", headers: dict | None = None, config: dict | None = None, cache=None):  # noqa: ANN001, ANN202
        monkeypatch.setattr(routes, "cache", cache or _Cache(list(reports)))
        with app.test_request_context(f"/{kind}" + (f"?{query}" if query else ""), headers=headers or {}):
            web = {"id": 1, "hostname": "https://feed.example", "config": {**WEB_CONFIG, **(config or {})}}
            lang = flask_request.args.get("lang")
            g.site = web_site.SiteContext(web, lang or "cs", chosen=lang is not None)
            return getattr(routes, kind)()

    return _respond


@pytest.fixture
def feed(respond):  # noqa: ANN001, ANN201
    """Render a feed (``rss`` or ``atom``) of the given reports; returns its XML root and content type."""

    def _feed(kind: str, *reports: dict, lang: str | None = None, config: dict | None = None) -> tuple[ET.Element, str]:
        response = respond(kind, *reports, query=f"lang={lang}" if lang else "", config=config)
        return ET.fromstring(response.get_data()), response.headers["Content-Type"]  # noqa: S314 (our own output)

    return _feed


NEWER = {"created": "2026-11-10T08:00:00", "published": "2026-11-12T14:05:00+01:00", "updated": "2026-11-13T09:30:00+01:00"}
OLDER = {"created": "2026-11-01T10:00:00", "published": "2026-11-03T16:45:00+01:00", "updated": "2026-11-03T16:45:00+01:00"}


def test_each_rss_item_says_when_it_was_published(feed) -> None:  # noqa: ANN001
    rss, content_type = feed("rss", _report(2, **NEWER), _report(1, **OLDER))
    channel = rss.find("channel")
    items = channel.findall("item")

    # Plain XML, so that a browser tab shows it; readers know RSS by the content.
    assert content_type == "application/xml; charset=utf-8"
    assert [item.findtext("guid") for item in items] == ["https://feed.example/reports/2", "https://feed.example/reports/1"]
    assert items[0].findtext("pubDate") == "Thu, 12 Nov 2026 14:05:00 +0100"
    assert parsedate_to_datetime(items[1].findtext("pubDate")) == datetime.fromisoformat(OLDER["published"])
    # The channel: published when its newest item was, changed when its last change was.
    assert channel.findtext("pubDate") == "Thu, 12 Nov 2026 14:05:00 +0100"
    assert channel.findtext("lastBuildDate") == "Fri, 13 Nov 2026 09:30:00 +0100"
    assert channel.findtext("language") == "cs"
    assert channel.findtext("link") == "https://feed.example"
    assert channel.findtext("generator") == "Taranis-NG"
    assert channel.find(f"{ATOM}link").attrib == {"href": "https://feed.example/rss", "rel": "self"}


def test_each_atom_entry_says_when_it_was_published_and_last_changed(feed) -> None:  # noqa: ANN001
    atom, content_type = feed("atom", _report(2, **NEWER), _report(1, **OLDER))
    entries = atom.findall(f"{ATOM}entry")

    assert content_type == "application/xml; charset=utf-8"
    assert atom.get("{http://www.w3.org/XML/1998/namespace}lang") == "cs"
    assert atom.findtext(f"{ATOM}id") == "https://feed.example/atom"
    assert datetime.fromisoformat(atom.findtext(f"{ATOM}updated")) == datetime.fromisoformat(NEWER["updated"])
    generator = atom.find(f"{ATOM}generator")
    assert (generator.text, generator.attrib) == ("Taranis-NG", {"uri": "https://github.com/SK-CERT/Taranis-NG"})
    # The whole feed is the organization's.
    author = atom.find(f"{ATOM}author")
    assert (author.findtext(f"{ATOM}name"), author.findtext(f"{ATOM}uri")) == ("Example CERT", "https://cert.example")
    assert {link.get("rel"): link.get("href") for link in atom.findall(f"{ATOM}link")} == {
        "self": "https://feed.example/atom",
        "alternate": "https://feed.example",
    }
    newer = entries[0]
    assert newer.findtext(f"{ATOM}id") == "https://feed.example/reports/2"
    assert datetime.fromisoformat(newer.findtext(f"{ATOM}published")) == datetime.fromisoformat(NEWER["published"])
    assert datetime.fromisoformat(newer.findtext(f"{ATOM}updated")) == datetime.fromisoformat(NEWER["updated"])
    assert newer.findtext(f"{ATOM}summary") == "About Bulletin 2"


def test_a_change_before_publication_does_not_date_an_entry_earlier(feed) -> None:  # noqa: ANN001
    report = _report(1, created="2026-11-01T10:00:00", published="2026-11-03T16:45:00+01:00", updated="2026-11-02T08:00:00+01:00")
    atom, _ = feed("atom", report)

    entry = atom.find(f"{ATOM}entry")
    assert datetime.fromisoformat(entry.findtext(f"{ATOM}updated")) == datetime.fromisoformat("2026-11-03T16:45:00+01:00")


def test_from_an_older_core_the_creation_in_local_time_is_the_publication(feed) -> None:  # noqa: ANN001
    rss, _ = feed("rss", _report(1, created="2026-07-01T10:00:00"))

    # Core's local time, read in the zone the node runs in (TZ, shared with core).
    assert rss.find("channel/item").findtext("pubDate") == "Wed, 01 Jul 2026 10:00:00 +0200"


def test_an_item_without_a_date_has_none(feed) -> None:  # noqa: ANN001
    rss, _ = feed("rss", _report(1))

    assert rss.find("channel/item/pubDate") is None


def test_an_empty_feed_is_still_a_valid_one(feed) -> None:  # noqa: ANN001
    atom, _ = feed("atom")

    assert atom.findall(f"{ATOM}entry") == []
    assert atom.findtext(f"{ATOM}updated")


def test_a_feed_for_one_language_keeps_it_in_its_links(feed) -> None:  # noqa: ANN001
    """Subscribed to /rss?lang=en, a reader gets English, and opens the reports in English."""
    rss, _ = feed("rss", _report(2, **NEWER), lang="en")
    channel = rss.find("channel")

    assert channel.findtext("language") == "en"
    assert channel.find(f"{ATOM}link").get("href") == "https://feed.example/rss?lang=en"
    item = channel.find("item")
    assert item.findtext("link") == "https://feed.example/reports/2?lang=en"
    # Another language's item is another item.
    assert item.findtext("guid") == "https://feed.example/reports/2?lang=en"


@pytest.fixture
def site_request(monkeypatch: pytest.MonkeyPatch):  # noqa: ANN201
    """Run ``check`` in a request to a web with the given languages, shown in ``language``."""
    monkeypatch.setenv("PUBLIC_WEB_API_KEY", "test-key")
    from lib.web import routes  # noqa: PLC0415 - its cache is made on import, with the key set above

    app = Flask(__name__)
    app.register_blueprint(routes.reports_bp)

    def _run(languages: list[str], language: str, check):  # noqa: ANN001, ANN202
        with app.test_request_context("/"):
            config = {"languages": languages, "default_language": languages[0]}
            g.site = web_site.SiteContext({"id": 1, "hostname": "https://feed.example", "config": config}, language)
            return check()

    return _run


def test_every_language_has_its_feeds_the_shown_one_first(site_request) -> None:  # noqa: ANN001
    from lib.web import feed_links  # noqa: PLC0415

    links = site_request(["en", "cs"], "cs", feed_links)

    assert links == [
        {"code": "cs", "name": "Čeština", "current": True, "rss": "/rss?lang=cs", "atom": "/atom?lang=cs"},
        {"code": "en", "name": "English", "current": False, "rss": "/rss?lang=en", "atom": "/atom?lang=en"},
    ]


def test_a_web_of_one_language_keeps_the_plain_addresses(site_request) -> None:  # noqa: ANN001
    from lib.web import feed_links  # noqa: PLC0415

    links = site_request(["sk"], "sk", feed_links)

    assert links == [{"code": "sk", "name": "Slovenčina", "current": True, "rss": "/rss", "atom": "/atom"}]


def test_each_feed_can_be_copied_by_its_full_address(site_client) -> None:  # noqa: ANN001
    """A feed reader wants the address: the menu copies it whole, and stays open to say so."""
    import re  # noqa: PLC0415

    from shared import public_web_script  # noqa: PLC0415

    page = site_client.client.get("/?lang=cs", headers={"Host": "localhost"}).text

    assert re.findall(r'data-copy-link="([^"]+)"', page) == [
        "https://localhost/rss?lang=cs",
        "https://localhost/atom?lang=cs",
        "https://localhost/rss?lang=en",
        "https://localhost/atom?lang=en",
    ]
    assert 'data-label-copied="Odkaz zkopírován"' in page
    assert 'data-bs-auto-close="outside"' in page
    # The page script does the copying.
    assert "[data-copy-link]" in public_web_script.SCRIPT


DC = "{http://purl.org/dc/elements/1.1/}"


def test_each_item_names_the_products_author(feed) -> None:  # noqa: ANN001
    """Atom gives the author per entry; RSS's own author must be an e-mail address, so it is dc:creator."""
    reports = (_report(2, "Jan Novák", **NEWER), _report(1, **OLDER))

    atom, _ = feed("atom", *reports)
    rss, _ = feed("rss", *reports)

    with_author, without = atom.findall(f"{ATOM}entry")
    assert [author.findtext(f"{ATOM}name") for author in with_author.findall(f"{ATOM}author")] == ["Jan Novák"]
    # Without one, an entry is the feed's author's.
    assert without.find(f"{ATOM}author") is None
    with_creator, without_creator = rss.findall("channel/item")
    assert with_creator.findtext(f"{DC}creator") == "Jan Novák"
    assert without_creator.find(f"{DC}creator") is None
    assert rss.find("channel/item/author") is None
    # Dublin Core goes into RSS only.
    assert DC not in ET.tostring(atom, encoding="unicode")


# -- answering "not modified" ---------------------------------------------------------------


def test_a_reader_with_the_current_feed_gets_an_empty_not_modified(respond) -> None:  # noqa: ANN001
    cache = _Cache([_report(2, **NEWER), _report(1, **OLDER)])

    first = respond("rss", cache=cache)
    etag, modified = first.headers["ETag"], first.headers["Last-Modified"]
    again = respond("rss", cache=cache, headers={"If-None-Match": etag})
    since = respond("rss", cache=cache, headers={"If-Modified-Since": modified})

    assert first.status_code == 200
    assert first.headers["Cache-Control"] == "public, no-cache"
    assert modified == "Fri, 13 Nov 2026 08:30:00 GMT"
    assert again.status_code == 304
    # What goes out for a 304: nothing.
    assert b"".join(again.get_app_iter({"REQUEST_METHOD": "GET"})) == b""
    assert since.status_code == 304
    # The feed is made once for what it shows.
    assert len(cache.feeds) == 1


def test_a_changed_report_makes_a_new_feed(respond) -> None:  # noqa: ANN001
    cache = _Cache([_report(2, **NEWER)])
    etag = respond("atom", cache=cache).headers["ETag"]

    cache.reports = [_report(2, **{**NEWER, "updated": "2026-11-14T10:00:00+01:00"})]
    changed = respond("atom", cache=cache, headers={"If-None-Match": etag})

    assert changed.status_code == 200
    assert changed.headers["ETag"] != etag


# -- pages ------------------------------------------------------------------------------------


def _many(count: int) -> list[dict]:
    return [_report(number, published=f"2026-11-{number:02d}T08:00:00+01:00") for number in range(count, 0, -1)]


def test_a_feed_carries_the_newest_page_and_links_the_older_ones(feed) -> None:  # noqa: ANN001
    atom, _ = feed("atom", *_many(5), config={"feed_page_size": 2})

    links = {link.get("rel"): link.get("href") for link in atom.findall(f"{ATOM}link")}
    assert [entry.findtext(f"{ATOM}id") for entry in atom.findall(f"{ATOM}entry")] == [
        "https://feed.example/reports/5",
        "https://feed.example/reports/4",
    ]
    assert links == {
        "self": "https://feed.example/atom",
        "first": "https://feed.example/atom",
        "last": "https://feed.example/atom?page=3",
        "next": "https://feed.example/atom?page=2",
        "alternate": "https://feed.example",
    }


def test_an_older_page_links_both_ways(respond) -> None:  # noqa: ANN001
    response = respond("rss", *_many(5), query="page=2&lang=en", config={"feed_page_size": 2})
    channel = ET.fromstring(response.get_data()).find("channel")  # noqa: S314 (our own output)

    assert [item.findtext("guid") for item in channel.findall("item")] == [
        "https://feed.example/reports/3?lang=en",
        "https://feed.example/reports/2?lang=en",
    ]
    assert {link.get("rel"): link.get("href") for link in channel.findall(f"{ATOM}link")} == {
        "self": "https://feed.example/rss?page=2&lang=en",
        "first": "https://feed.example/rss?lang=en",
        "last": "https://feed.example/rss?page=3&lang=en",
        "previous": "https://feed.example/rss?lang=en",
        "next": "https://feed.example/rss?page=3&lang=en",
    }


def test_fifty_reports_a_page_unless_the_web_says_otherwise(feed) -> None:  # noqa: ANN001
    atom, _ = feed("atom", *_many(30), *(_report(number) for number in range(100, 30, -1)))

    assert len(atom.findall(f"{ATOM}entry")) == 50


@pytest.mark.parametrize(("query", "status"), [("page=4", 404), ("page=0", 400), ("page=two", 400)])
def test_a_page_that_is_not_there(respond, query: str, status: int) -> None:  # noqa: ANN001
    from werkzeug.exceptions import HTTPException  # noqa: PLC0415

    with pytest.raises(HTTPException) as refused:
        respond("rss", *_many(5), query=query, config={"feed_page_size": 2})

    assert refused.value.code == status


# -- the whole report, logo and rights --------------------------------------------------------


def test_each_item_carries_the_whole_report_with_absolute_links(feed) -> None:  # noqa: ANN001
    atom, _ = feed("atom", _report(2, **NEWER))
    rss, _ = feed("rss", _report(2, **NEWER))

    content = atom.find(f"{ATOM}entry/{ATOM}content")
    assert content.get("type") == "html"
    assert content.text == '<p>All about <a href="https://feed.example/reports/2">Bulletin 2</a></p>'
    encoded = rss.find("channel/item/{http://purl.org/rss/1.0/modules/content/}encoded")
    assert encoded.text == content.text
    # The summary stays plain text.
    assert rss.find("channel/item").findtext("description") == "About Bulletin 2"


def test_the_feed_carries_the_webs_logo_icon_and_rights(feed) -> None:  # noqa: ANN001
    from lib.web import feeds  # noqa: PLC0415

    atom, _ = feed("atom", _report(2, **NEWER))
    rss, _ = feed("rss", _report(2, **NEWER))

    rights = f"© {feeds.this_year()} Example CERT"
    assert atom.findtext(f"{ATOM}rights") == rights
    assert atom.findtext(f"{ATOM}logo") == "https://feed.example/static/logo.svg"
    assert atom.findtext(f"{ATOM}icon") == "https://feed.example/static/favicon.ico"
    channel = rss.find("channel")
    assert channel.findtext("copyright") == rights
    image = channel.find("image")
    assert (image.findtext("url"), image.findtext("link")) == ("https://feed.example/static/logo.svg", "https://feed.example")


def test_html_with_the_webs_own_paths_is_made_absolute() -> None:
    from lib.web import feeds  # noqa: PLC0415

    html = '<a href="/reports/7">7</a> <img src="/branding/logo"> <a href="//cdn.example/x">x</a> <a href="https://a.example/">a</a>'

    assert feeds.absolute("https://feed.example", html) == (
        '<a href="https://feed.example/reports/7">7</a> <img src="https://feed.example/branding/logo"> '
        '<a href="//cdn.example/x">x</a> <a href="https://a.example/">a</a>'
    )


# -- WebSub -----------------------------------------------------------------------------------

HUB = "https://hub.example/"


def test_with_a_hub_the_feeds_name_it(respond) -> None:  # noqa: ANN001
    atom = respond("atom", _report(2, **NEWER), config={"websub_hub": HUB})
    rss = respond("rss", _report(2, **NEWER), query="lang=cs", config={"websub_hub": HUB})

    atom_links = {link.get("rel"): link.get("href") for link in ET.fromstring(atom.get_data()).findall(f"{ATOM}link")}  # noqa: S314
    rss_links = {
        link.get("rel"): link.get("href")
        for link in ET.fromstring(rss.get_data()).find("channel").findall(f"{ATOM}link")  # noqa: S314
    }
    assert (atom_links["hub"], atom_links["self"]) == (HUB, "https://feed.example/atom")
    assert (rss_links["hub"], rss_links["self"]) == (HUB, "https://feed.example/rss?lang=cs")
    assert rss.headers.getlist("Link") == [f'<{HUB}>; rel="hub"', '<https://feed.example/rss?lang=cs>; rel="self"']


def test_without_a_hub_none_is_named(respond) -> None:  # noqa: ANN001
    response = respond("atom", _report(2, **NEWER), config={"websub_hub": "ftp://hub.example/"})

    assert "hub" not in {link.get("rel") for link in ET.fromstring(response.get_data()).findall(f"{ATOM}link")}  # noqa: S314
    assert "Link" not in response.headers


def _web(hostname: str, **config: object) -> dict:
    return {"id": 1, "hostname": hostname, "enabled": True, "config": {"languages": ["en", "cs"], **config}}


def test_the_hub_learns_of_every_feed_a_reader_may_follow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUBLIC_WEB_API_KEY", "test-key")
    from lib.web import websub  # noqa: PLC0415

    told: list[tuple[str, dict]] = []

    def post(url: str, data: dict, timeout: int) -> SimpleNamespace:
        assert timeout > 0
        told.append((url, data))
        return SimpleNamespace(status_code=204)

    monkeypatch.setattr(websub.requests, "post", post)

    webs = [
        _web("feed.example", websub_hub=HUB),
        _web("quiet.example"),
        {**_web("off.example", websub_hub=HUB), "enabled": False},
    ]
    websub.notify(webs)

    assert [url for url, _data in told] == [HUB] * 7
    assert [data["hub.url"] for _url, data in told] == [
        "https://feed.example/rss",
        "https://feed.example/feed",
        "https://feed.example/atom",
        "https://feed.example/rss?lang=en",
        "https://feed.example/atom?lang=en",
        "https://feed.example/rss?lang=cs",
        "https://feed.example/atom?lang=cs",
    ]
    assert {data["hub.mode"] for _url, data in told} == {"publish"}


def test_a_hub_that_is_down_is_only_logged(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUBLIC_WEB_API_KEY", "test-key")
    from lib.web import websub  # noqa: PLC0415

    def down(*_args: object, **_kwargs: object) -> None:
        message = "hub down"
        raise websub.requests.ConnectionError(message)

    monkeypatch.setattr(websub.requests, "post", down)

    websub.notify([_web("feed.example", websub_hub=HUB)])


def test_a_cache_reset_tells_the_hubs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUBLIC_WEB_API_KEY", "test-key")
    from lib.web import management, websub  # noqa: PLC0415

    asked: list = []
    monkeypatch.setattr(management.cache, "clear", lambda: asked.append("clear"))
    monkeypatch.setattr(websub, "notify_in_background", asked.append)

    with Flask(__name__).test_request_context("/management/reset-cache", method="POST"):
        _body, status = management.reset_cache.__wrapped__()

    assert status == 200
    assert asked == ["clear", management.cache.get_webs]
