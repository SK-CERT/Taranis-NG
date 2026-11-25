"""Collectors fetch web sources only: http(s), and nothing on the internal network.

A source's URL is typed in by whoever may configure sources. The Web collector used to take a
``file://`` URL, a bare file path, or any scheme its browser understands, and the RSS collector
handed the URL to feedparser, which opens a local file of that name. Both also fetched internal
addresses - the cloud metadata endpoint, the services next to the collector. Internal sources
are fetched only when the collectors node allows them, which core says with every source it
hands the node. The rules themselves are tested in ``shared/tests/test_url_guard.py``; these
tests pin that each collector asks.
"""

from __future__ import annotations

import collections
import io
import socket
import types
from typing import TYPE_CHECKING, ClassVar

import pytest
import requests
from collectors.base_collector import allowed_targets, load_sources
from collectors.csaf_sources import BlockedRedirectError, Fetcher
from collectors.rss_collector import RSSCollector
from collectors.web_collector import WebCollector

from collectors import rss_collector
from shared import url_guard

if TYPE_CHECKING:
    from collections.abc import Callable

NAMES = {"news.example.org": "93.184.216.34", "intranet.example.org": "10.20.30.40", "core": "172.18.0.5"}

FEED = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>Example news</title>
  <item><title>An advisory</title><link>/advisories/1</link><description>Summary of the advisory.</description></item>
</channel></rss>"""


class RecordingLogger:
    """Stand-in for the source logger: remembers what was logged at each level."""

    def __init__(self) -> None:
        """Start with nothing logged."""
        self.messages: dict[str, list[str]] = collections.defaultdict(list)

    def __getattr__(self, level: str) -> Callable[..., None]:
        """Any level is a method that records its message."""

        def record(message: str = "", *_args: object, **_kwargs: object) -> None:
            self.messages[level].append(str(message))

        return record


@pytest.fixture(autouse=True)
def _dns(monkeypatch: pytest.MonkeyPatch) -> None:
    """Resolve the made-up names above and nothing else."""

    def getaddrinfo(host: str, port: int, *_args: object, **_kwargs: object) -> list[tuple]:
        if host not in NAMES:
            raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (NAMES[host], port))]

    monkeypatch.setattr(url_guard.socket, "getaddrinfo", getaddrinfo)


def make_source(allowed: str = "", **parameters: str) -> types.SimpleNamespace:
    """A source whose unset parameters read as empty, with a recording logger.

    ``allowed`` is what its collectors node may fetch from an internal network, as core sends it.
    """
    return types.SimpleNamespace(
        id="source-1",
        name="a source",
        param_key_values=collections.defaultdict(str, parameters),
        logger=RecordingLogger(),
        last_collected=None,
        word_lists=[],
        allowed_private_targets=allowed,
    )


# --- Web collector ---------------------------------------------------------------------------


def parse_web_settings(allowed: str = "", **parameters: str) -> tuple[bool, types.SimpleNamespace]:
    collector = WebCollector()
    collector.source = make_source(allowed, **parameters)
    return collector._WebCollector__parse_settings(), collector.source


@pytest.mark.parametrize(
    ("web_url", "fetched"),
    [
        ("https://news.example.org/advisories", "https://news.example.org/advisories"),
        ("http://news.example.org/", "http://news.example.org/"),
        ("news.example.org/advisories", "https://news.example.org/advisories"),
        ("news.example.org:8443/advisories", "https://news.example.org:8443/advisories"),
        ("  https://news.example.org/  ", "https://news.example.org/"),
    ],
)
def test_web_collector_accepts_a_web_page(web_url: str, fetched: str) -> None:
    accepted, source = parse_web_settings(WEB_URL=web_url)

    assert accepted is True
    assert source.url == fetched
    assert source.logger.messages["error"] == []


@pytest.mark.parametrize(
    "web_url",
    [
        "file:///etc/passwd",
        "FILE:///etc/passwd",
        "file:/etc/passwd",
        "/etc/passwd",
        "/app/storage",
        "view-source:file:///etc/passwd",
        "view-source://etc/passwd",
        "chrome://version",
        "about:blank",
        "ftp://news.example.org/",
        "http://169.254.169.254/latest/meta-data/",
        "http://localhost:5000/",
        "http://core/api/v1/isalive",
        "core",
        "https://intranet.example.org/",
    ],
)
def test_web_collector_refuses_local_files_other_schemes_and_internal_addresses(web_url: str) -> None:
    accepted, source = parse_web_settings(WEB_URL=web_url)

    assert accepted is False
    assert len(source.logger.messages["error"]) == 1
    assert "Skipping collection" in source.logger.messages["error"][0]


def test_web_collector_fetches_an_internal_source_its_node_allows() -> None:
    accepted, source = parse_web_settings("intranet.example.org", WEB_URL="https://intranet.example.org/news")

    assert accepted is True
    assert source.url == "https://intranet.example.org/news"


def test_web_collector_still_refuses_what_its_node_does_not_name() -> None:
    accepted, _source = parse_web_settings("intranet.example.org", WEB_URL="http://core/api/v1/isalive")

    assert accepted is False


def test_web_collector_keeps_page_credentials_out_of_the_log() -> None:
    accepted, source = parse_web_settings(WEB_URL="http://core/", AUTH_USERNAME="reader", AUTH_PASSWORD="s3cret-value")

    assert accepted is False
    assert "s3cret-value" not in " ".join(source.logger.messages["error"])


def parse_web_collector(**parameters: str) -> tuple[bool, WebCollector]:
    collector = WebCollector()
    collector.source = make_source(**parameters)
    return collector._WebCollector__parse_settings(), collector


def test_web_collector_hands_page_credentials_to_the_browser_only() -> None:
    accepted, collector = parse_web_collector(
        WEB_URL="https://news.example.org/a?page=2",
        AUTH_USERNAME="reader",
        AUTH_PASSWORD="s3cret-value",
    )

    assert accepted is True
    # The source's URL is logged and stored as every news item's source: no credentials there.
    assert collector.source.url == "https://news.example.org/a?page=2"
    assert collector.title_page_url == "https://reader:s3cret-value@news.example.org/a?page=2"


def test_web_collector_encodes_credentials_so_they_cannot_change_the_host() -> None:
    accepted, collector = parse_web_collector(
        WEB_URL="https://news.example.org/a",
        AUTH_USERNAME="reader",
        AUTH_PASSWORD="p@ss:word/evil.example",
    )

    assert accepted is True
    assert collector.title_page_url == "https://reader:p%40ss%3Aword%2Fevil.example@news.example.org/a"


def test_web_collector_without_credentials_opens_the_bare_url() -> None:
    accepted, collector = parse_web_collector(WEB_URL="https://news.example.org/a", AUTH_USERNAME="reader")

    assert accepted is True
    assert collector.title_page_url == collector.source.url == "https://news.example.org/a"


def test_web_collector_redacts_credentials_in_browser_errors() -> None:
    _accepted, collector = parse_web_collector(WEB_URL="https://news.example.org/a", AUTH_USERNAME="reader", AUTH_PASSWORD="s3cret-value")

    message = collector._WebCollector__redacted(RuntimeError(f"net::ERR_TIMED_OUT at {collector.title_page_url}"))

    assert "s3cret-value" not in message
    assert "https://news.example.org/a" in message


def test_web_collector_checks_links_and_landing_pages_with_the_source_s_proxy_setting() -> None:
    collector = WebCollector()
    collector.source = make_source(WEB_URL="https://news.example.org/", TOR="true")
    assert collector._WebCollector__parse_settings() is True

    problem = collector._WebCollector__url_problem
    assert problem("http://exampleonionaddress.onion/article") is None  # resolved by Tor, not here
    assert "only http and https" in problem("file:///etc/passwd")
    assert "non-public" in problem("http://core/api/v1/isalive")
    assert "non-public" in problem("http://169.254.169.254/")


# --- RSS collector ---------------------------------------------------------------------------


def initialized_rss_collector(feed_url: str, allowed: str = "") -> RSSCollector:
    collector = RSSCollector()
    source = make_source(allowed, FEED_URL=feed_url)
    collector.source = source
    source.url = feed_url
    source.user_agent = ""
    source.proxy_handler = None
    source.opener = collector._RSSCollector__get_opener()
    return collector


@pytest.mark.parametrize(
    "feed_url",
    ["/etc/passwd", "file:///etc/passwd", "http://169.254.169.254/latest/meta-data/", "http://core/api/v1/isalive", "http://localhost/feed"],
)
def test_rss_collector_refuses_local_files_and_internal_addresses(feed_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    def parse(*_args: object, **_kwargs: object) -> None:
        pytest.fail("feedparser must not be given a URL that was refused")

    monkeypatch.setattr(rss_collector.feedparser, "parse", parse)
    collector = initialized_rss_collector(feed_url)

    assert collector._RSSCollector__fetch_feed() is None
    (error,) = collector.source.logger.messages["error"]
    assert "Refusing to fetch" in error


def test_rss_collector_parses_the_downloaded_body_and_never_hands_feedparser_the_url(monkeypatch: pytest.MonkeyPatch) -> None:
    asked: list[str] = []

    class Answer(io.BytesIO):
        headers: ClassVar[dict[str, str]] = {"Content-Type": "application/rss+xml"}

        def geturl(self) -> str:
            return "https://news.example.org/feed.xml"

    def fake_open(request: object, *_args: object, **_kwargs: object) -> Answer:
        asked.append(request.full_url)
        return Answer(FEED)

    real_parse = rss_collector.feedparser.parse
    parsed_inputs: list[object] = []

    def parse(data: object, **kwargs: object) -> object:
        parsed_inputs.append(data)
        return real_parse(data, **kwargs)

    monkeypatch.setattr(rss_collector, "build_guarded_opener", lambda *_handlers, **_kwargs: fake_open)
    monkeypatch.setattr(rss_collector.feedparser, "parse", parse)
    collector = initialized_rss_collector("https://news.example.org/feed.xml")

    feed = collector._RSSCollector__fetch_feed()

    assert asked == ["https://news.example.org/feed.xml"]
    assert parsed_inputs == [FEED]
    (entry,) = feed["entries"]
    assert entry["title"] == "An advisory"
    assert entry["link"] == "https://news.example.org/advisories/1"  # relative links still resolve


def test_rss_collector_does_not_fetch_an_article_link_to_an_internal_address() -> None:
    collector = initialized_rss_collector("https://news.example.org/feed.xml")

    content = collector._scrape_content("http://169.254.169.254/latest/meta-data/", "An advisory", 1, {"entries": [{}]})

    assert content == ""
    (warning,) = collector.source.logger.messages["warning"]
    assert "Refusing to fetch" in warning


def test_rss_collector_fetches_an_internal_feed_its_node_allows(monkeypatch: pytest.MonkeyPatch) -> None:
    built: list[dict] = []

    class Answer(io.BytesIO):
        headers: ClassVar[dict[str, str]] = {}

        def geturl(self) -> str:
            return "https://intranet.example.org/feed.xml"

    def build(*_handlers: object, **kwargs: object) -> Callable[..., Answer]:
        built.append(kwargs)
        return lambda *_args, **_kwargs: Answer(FEED)

    monkeypatch.setattr(rss_collector, "build_guarded_opener", build)
    collector = initialized_rss_collector("https://intranet.example.org/feed.xml", allowed="intranet.example.org")

    feed = collector._RSSCollector__fetch_feed()

    assert built == [{"allowed": "intranet.example.org"}]  # redirects are judged by the same list
    assert len(feed["entries"]) == 1
    assert collector.source.logger.messages["error"] == []


# --- what core sends ---------------------------------------------------------------------------


def _source_from_core(**extra: object) -> dict:
    source = {"id": "source-1", "name": "a source", "parameter_values": [], "word_lists": [], "description": "", "collector_id": "c1"}
    return {**source, "last_attempted": None, "last_collected": None, **extra}


def test_sources_keep_what_core_says_their_node_may_fetch() -> None:
    (source,) = load_sources([_source_from_core(allowed_private_targets="intranet.example.org\n10.20.0.0/16")])

    assert allowed_targets(source) == "intranet.example.org\n10.20.0.0/16"


@pytest.mark.parametrize("extra", [{}, {"allowed_private_targets": None}, {"allowed_private_targets": ["core"]}])
def test_an_older_core_or_a_strange_answer_allows_nothing_internal(extra: dict) -> None:
    (source,) = load_sources([_source_from_core(**extra)])

    assert allowed_targets(source) == ""


# --- CSAF collector --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    ["http://169.254.169.254/latest/meta-data/", "http://core/api/v1/isalive", "https://intranet.example.org/csaf/"],
)
def test_csaf_fetcher_refuses_an_internal_address_without_a_request(url: str) -> None:
    class NoRequests:
        headers: ClassVar[dict[str, str]] = {}
        proxies: ClassVar[dict[str, str]] = {}
        hooks: ClassVar[dict[str, list]] = {"response": []}

        def get(self, *_args: object, **_kwargs: object) -> None:
            pytest.fail("no request may be sent to a refused URL")

    response = Fetcher(session=NoRequests()).get(url)

    assert response.status == 0
    assert "Refusing to fetch" in response.error


def test_csaf_fetcher_stops_at_a_redirect_to_an_internal_address() -> None:
    fetcher = Fetcher()
    redirect = types.SimpleNamespace(is_redirect=True, url="https://news.example.org/csaf/", headers={"location": "http://169.254.169.254/x"})

    assert fetcher._check_redirect in fetcher.session.hooks["response"]
    with pytest.raises(BlockedRedirectError, match="non-public"):
        fetcher._check_redirect(redirect)


def test_csaf_fetcher_follows_a_redirect_to_a_public_address() -> None:
    fetcher = Fetcher()
    redirect = types.SimpleNamespace(is_redirect=True, url="https://news.example.org/csaf/", headers={"location": "/csaf/v2/"})

    assert fetcher._check_redirect(redirect) is None


def test_csaf_fetcher_fetches_an_internal_provider_its_node_allows() -> None:
    asked: list[str] = []

    class Session:
        headers: ClassVar[dict[str, str]] = {}
        proxies: ClassVar[dict[str, str]] = {}
        hooks: ClassVar[dict[str, list]] = {"response": []}

        def get(self, url: str, **_kwargs: object) -> object:
            asked.append(url)
            raise requests.ConnectionError

    response = Fetcher(session=Session(), allowed="intranet.example.org").get("https://intranet.example.org/csaf/")

    assert asked == ["https://intranet.example.org/csaf/"]  # the guard let it through
    assert "Refusing" not in response.error
