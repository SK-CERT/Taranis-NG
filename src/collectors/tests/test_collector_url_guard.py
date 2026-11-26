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
from urllib.parse import quote, unquote, urlsplit

import pytest
import requests
from collectors.base_collector import allowed_targets, load_sources
from collectors.csaf_sources import BlockedRedirectError, Fetcher
from collectors.rss_collector import RSSCollector
from collectors.web_collector import WebCollector, without_credentials

from collectors import rss_collector, web_collector
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


@pytest.mark.parametrize(
    ("web_url", "title_page_url"),
    [
        ("https://reader:s3cret-value@news.example.org/a?page=2", "https://reader:s3cret-value@news.example.org/a?page=2"),
        ("reader:s3cret-value@news.example.org/a?page=2", "https://reader:s3cret-value@news.example.org/a?page=2"),
        # typed encoded or not, the browser gets them encoded once
        ("https://reader:p%40ss%3Aword@news.example.org/a?page=2", "https://reader:p%40ss%3Aword@news.example.org/a?page=2"),
        ("https://reader:p@ss:word@news.example.org/a?page=2", "https://reader:p%40ss%3Aword@news.example.org/a?page=2"),
    ],
)
def test_credentials_typed_into_the_web_url_are_the_page_s_credentials(web_url: str, title_page_url: str) -> None:
    accepted, collector = parse_web_collector(WEB_URL=web_url)

    assert accepted is True
    # logged, checked, and stored as every news item's source: no credentials there
    assert collector.source.url == "https://news.example.org/a?page=2"
    assert collector.title_page_url == title_page_url


def test_the_auth_parameters_win_over_credentials_in_the_web_url() -> None:
    accepted, collector = parse_web_collector(
        WEB_URL="https://reader:s3cret-value@news.example.org/a",
        AUTH_USERNAME="analyst",
        AUTH_PASSWORD="other-value",
    )

    assert accepted is True
    assert collector.source.url == "https://news.example.org/a"
    assert collector.title_page_url == "https://analyst:other-value@news.example.org/a"
    assert "s3cret-value" not in repr(collector.source.logger.messages)


def test_a_refused_web_url_is_reported_without_the_credentials_typed_into_it() -> None:
    accepted, source = parse_web_settings(WEB_URL="https://reader:s3cret-value@intranet.example.org/a")

    assert accepted is False
    assert "https://intranet.example.org/a" in source.logger.messages["error"][0]
    assert "s3cret-value" not in repr(source.logger.messages)


def test_an_unreadable_web_url_with_credentials_is_refused_without_quoting_it() -> None:
    accepted, source = parse_web_settings(WEB_URL="https://reader:s3cret-value@[news.example.org/a")

    assert accepted is False
    assert source.logger.messages["error"] == ["Web URL is not a valid URL. Skipping collection."]


def test_web_collector_redacts_credentials_in_browser_errors() -> None:
    _accepted, collector = parse_web_collector(WEB_URL="https://news.example.org/a", AUTH_USERNAME="reader", AUTH_PASSWORD="s3cret-value")

    message = collector._WebCollector__redacted(RuntimeError(f"net::ERR_TIMED_OUT at {collector.title_page_url}"))

    assert "s3cret-value" not in message
    assert "https://news.example.org/a" in message


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://reader:s3cret@news.example.org/article/1?x=1#y", "https://news.example.org/article/1?x=1#y"),
        ("https://reader:p%40ss@news.example.org:8443/a", "https://news.example.org:8443/a"),
        ("https://news.example.org/a?mail=x@example.org", "https://news.example.org/a?mail=x@example.org"),
        ("https://news.example.org/a", "https://news.example.org/a"),
        ("", ""),
        (None, None),
    ],
)
def test_links_are_shown_and_stored_without_credentials(url: str | None, expected: str | None) -> None:
    assert without_credentials(url) == expected


def test_an_article_reached_from_a_credentialed_title_page_is_stored_without_credentials() -> None:
    """A relative link on the title page resolves to a URL that inherits its user name and password."""
    _accepted, collector = parse_web_collector(WEB_URL="https://news.example.org/a", AUTH_USERNAME="reader", AUTH_PASSWORD="s3cret-value")
    collector._WebCollector__find_element_text_by = lambda _scope, selector: "Article title" if selector else ""
    collector._WebCollector__find_element_html_by = lambda _scope, _selector: "<p>Body</p>"
    browser = types.SimpleNamespace(current_url="https://reader:s3cret-value@news.example.org/article/1")

    news_item = collector._WebCollector__process_article_page(browser, browser)

    assert news_item is not None
    assert news_item.link == "https://news.example.org/article/1"
    assert news_item.source == "https://news.example.org/a"


def test_web_collector_redacts_credentials_of_any_url_in_errors() -> None:
    _accepted, collector = parse_web_collector(WEB_URL="https://news.example.org/a", AUTH_USERNAME="reader", AUTH_PASSWORD="s3cret-value")

    message = collector._WebCollector__redacted(RuntimeError("net::ERR_ABORTED at https://reader:s3cret-value@news.example.org/article/7"))

    assert message == "net::ERR_ABORTED at https://news.example.org/article/7"


@pytest.mark.parametrize(
    "quoted",
    [
        lambda url: url,
        quote,  # Firefox: about:neterror?e=...&u=https%3A//user%3Apass%40host/...
        lambda url: quote(url, safe=""),
        lambda url: quote(quote(url)),
        lambda url: quote(quote(url, safe=""), safe=""),
        lambda url: url.replace("/", "\\/"),  # JSON-escaped
    ],
    ids=["raw", "encoded", "encoded-slashes", "encoded-twice", "encoded-slashes-twice", "json"],
)
def test_web_collector_redacts_the_page_credentials_however_an_error_quotes_them(quoted: Callable[[str], str]) -> None:
    _accepted, collector = parse_web_collector(WEB_URL="https://news.example.org/a", AUTH_USERNAME="re@der", AUTH_PASSWORD="p@ss w/rd")
    article = urlsplit(collector.title_page_url)._replace(path="/article/7").geturl()

    message = collector._WebCollector__redacted(RuntimeError(f"Reached error page: about:neterror?e=netTimeout&u={quoted(article)}&c=UTF-8"))

    readable = message.replace("\\/", "/")
    for _encoding in range(3):  # the URL's own, and up to two more
        readable = unquote(readable)
    assert "news.example.org/article/7" in readable
    assert "p@ss w/rd" not in readable
    assert "re@der" not in readable


def test_web_collector_redacts_the_page_credentials_outside_a_url() -> None:
    _accepted, collector = parse_web_collector(WEB_URL="https://news.example.org/a", AUTH_USERNAME="reader", AUTH_PASSWORD="s3cret-value")

    message = collector._WebCollector__redacted(
        RuntimeError("bad credentials reader:s3cret-value, then s3cret-value alone, for news.example.org"),
    )

    assert message == "bad credentials ***, then *** alone, for news.example.org"


def test_credentials_typed_into_the_web_url_are_redacted_too() -> None:
    _accepted, collector = parse_web_collector(WEB_URL="https://reader:s3cret-value@news.example.org/a")

    message = collector._WebCollector__redacted(RuntimeError(f"u={quote(collector.title_page_url)}"))

    assert message == "u=https%3A//***%40news.example.org/a"


def test_a_short_user_name_or_password_is_redacted_only_where_it_ends_the_credentials_of_a_url() -> None:
    """Replaced everywhere, "ab" would mangle every message it happens to occur in."""
    _accepted, collector = parse_web_collector(WEB_URL="https://news.example.org/tab", AUTH_USERNAME="ab", AUTH_PASSWORD="cd")

    message = collector._WebCollector__redacted(RuntimeError(f"u={quote(collector.title_page_url)} (abcd, cd@x)"))

    assert message == "u=https%3A//***%40news.example.org/tab (abcd, ***@x)"


@pytest.mark.parametrize("parameters", [{}, {"AUTH_USERNAME": ""}, {"AUTH_USERNAME": "", "AUTH_PASSWORD": ""}])
def test_without_credentials_an_error_is_logged_as_it_is(parameters: dict[str, str]) -> None:
    _accepted, collector = parse_web_collector(WEB_URL="https://news.example.org/a", **parameters)
    text = "Message: timeout: Timed out receiving message from renderer: 10.000 (https://news.example.org/a)"

    assert collector._WebCollector__redacted(RuntimeError(text)) == text


class CrawledBrowser:
    """Just enough of a WebDriver to crawl a title page; its errors quote the URLs it holds, as browsers do."""

    def __init__(self, current_url: str) -> None:
        """A browser on ``current_url``, in a single tab."""
        self.current_url = current_url
        self.current_window_handle = "title"
        self.window_handles = ["title"]
        self.switch_to = types.SimpleNamespace(new_window=lambda _kind: None, window=self.window)
        self.opened: list[str] = []

    def get(self, url: str) -> None:
        """Open a URL; one ending in /broken fails as Firefox does."""
        if url.endswith("/broken"):
            msg = f"Message: Reached error page: about:neterror?e=netTimeout&u={quote(url)}"
            raise RuntimeError(msg)
        self.opened.append(url)

    def execute_script(self, _script: str) -> list[str]:
        """The page shown is the site's, not the browser's error page."""
        return ["https:", ""]

    def find_element(self, *_locator: object) -> None:
        """Fail like a page that changed under the driver."""
        msg = f"stale element reference on {self.current_url}"
        raise RuntimeError(msg)

    def window(self, _handle: str) -> None:
        """Fail like a tab that went away."""
        msg = f"no such window while on {self.current_url}"
        raise RuntimeError(msg)

    def quit(self) -> None:
        """Nothing to stop."""


def test_browser_errors_on_the_title_page_are_logged_without_credentials_or_traceback() -> None:
    _accepted, collector = parse_web_collector(
        WEB_URL="https://news.example.org/a",
        AUTH_USERNAME="reader",
        AUTH_PASSWORD="s3cret-value",
        POPUP_CLOSE_SELECTOR="css: .close",
    )
    browser = CrawledBrowser(collector.title_page_url)
    collector._WebCollector__get_headless_driver = lambda: browser

    def crawl(*_args: object) -> int:
        msg = f"Message: Reached error page: about:neterror?e=netReset&u={quote(collector.title_page_url, safe='')}"
        raise RuntimeError(msg)

    collector._WebCollector__process_title_page_articles = crawl

    assert collector._WebCollector__browse_title_page(collector.title_page_url) == 0
    assert collector._WebCollector__close_other_tabs(browser, "title", collector.title_page_url) is True

    messages = collector.source.logger.messages
    # a traceback ends with the exception's own text, which nothing redacts
    assert messages["exception"] == []
    assert [message.split(":")[0] for message in messages["error"]] == [
        "Popup find failed",
        "Page crawl failed",
        "Browser tab restoration failed, reloading the title page",
    ]
    assert "s3cret-value" not in repr(dict(messages))


def test_browser_errors_on_article_pages_are_logged_without_credentials_and_a_bad_link_skips_only_itself(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _accepted, collector = parse_web_collector(WEB_URL="https://news.example.org/a", AUTH_USERNAME="reader", AUTH_PASSWORD="s3cret-value")
    monkeypatch.setattr(web_collector.time, "sleep", lambda _seconds: None)
    article = "https://reader:s3cret-value@news.example.org/article"
    links = ["https://reader:s3cret-value@[news.example.org/1", f"{article}/broken", f"{article}/stale", f"{article}/fine"]
    items = [types.SimpleNamespace(get_attribute=lambda _name, link=link: link) for link in links]
    collector._WebCollector__wait_for_article_items = lambda _browser: None
    collector._WebCollector__safe_find_elements_by = lambda _browser, _selector: items

    def process_article_page(browser: CrawledBrowser, _scope: object) -> object:
        if browser.opened[-1].endswith("/stale"):
            msg = f"stale element reference at {browser.opened[-1].replace('/', '\\/')}"
            raise RuntimeError(msg)
        return types.SimpleNamespace(print_news_item=lambda _logger: None)

    collector._WebCollector__process_article_page = process_article_page
    collector.sanitize_news_item = lambda *_args: None
    collector.news_items = []
    browser = CrawledBrowser(collector.title_page_url)

    failed = collector._WebCollector__process_title_page_articles(browser, "title", collector.title_page_url)

    assert failed == 3
    assert browser.opened == [f"{article}/stale", f"{article}/fine"]
    assert len(collector.news_items) == 1
    messages = collector.source.logger.messages
    assert messages["exception"] == []
    assert messages["warning"] == [
        "Refusing to open 'https://[news.example.org/1': not a valid URL (Invalid IPv6 URL). Skipping article 1/4.",
    ]
    assert [message.split(":")[0] for message in messages["error"]] == ["Failed to get link for article 2/4", "Parsing an article failed"]
    assert "s3cret-value" not in repr(dict(messages))


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
