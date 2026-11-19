"""The collectors' egress guard: which URLs a collector may fetch.

A source's URL is typed in by whoever configures sources, and the pages behind it link and
redirect wherever they like. Without a check, any of them could aim the collector at the cloud
metadata address, at a service next to it (core, Redis, the database) or at a local file, and
read the answer back as a news item.
"""

from __future__ import annotations

import io
import socket
import urllib.error
import urllib.request
from email.message import Message

import pytest
from shared.url_guard import (
    BlockedUrlError,
    allowed_targets_problem,
    assert_collector_url,
    build_guarded_opener,
    collector_url_problem,
)

from shared import url_guard

NAMES = {
    "news.example.org": "93.184.216.34",
    "intranet.example.org": "10.20.30.40",
    "wiki.corp.example.org": "10.20.30.41",
    "core": "172.18.0.5",
    "both.example.org": ["93.184.216.34", "127.0.0.1"],
}


@pytest.fixture(autouse=True)
def _dns(monkeypatch: pytest.MonkeyPatch) -> None:
    """Resolve the made-up names above and nothing else."""

    def getaddrinfo(host: str, port: int, **_kwargs: object) -> list[tuple]:
        if host not in NAMES:
            raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")
        answers = NAMES[host] if isinstance(NAMES[host], list) else [NAMES[host]]
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port)) for address in answers]

    monkeypatch.setattr(url_guard.socket, "getaddrinfo", getaddrinfo)


@pytest.mark.parametrize("url", ["https://news.example.org/feed.xml", "http://news.example.org:8080/", "https://93.184.216.34/"])
def test_a_public_source_is_fetched(url: str) -> None:
    assert_collector_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "FILE:///etc/passwd",
        "view-source:https://news.example.org/",
        "chrome://settings",
        "ftp://news.example.org/file",
        "javascript:alert(1)",
        "about:blank",
        "/etc/passwd",
        "",
    ],
)
def test_only_http_and_https_are_fetched(url: str) -> None:
    with pytest.raises(BlockedUrlError, match="only http and https"):
        assert_collector_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://169.254.169.254/latest/meta-data/",  # cloud instance metadata
        "http://127.0.0.1:5000/",
        "http://127.1/",  # short spelling of 127.0.0.1
        "http://2130706433/",  # 127.0.0.1 as one number
        "http://0x7f000001/",
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",  # IPv4 mapped into IPv6
        "http://10.0.0.5/",
        "http://192.168.1.1/",
        "http://100.64.0.1/",  # shared address space
        "http://0.0.0.0/",
        "http://localhost/",
        "http://app.localhost/",
        "http://core/api/v1/isalive",  # a service on the collector's own network
        "https://intranet.example.org/feed.xml",
        "https://user:secret@intranet.example.org/",
    ],
)
def test_an_internal_address_is_refused(url: str) -> None:
    with pytest.raises(BlockedUrlError):
        assert_collector_url(url)


def test_one_internal_answer_among_public_ones_is_enough_to_refuse() -> None:
    with pytest.raises(BlockedUrlError, match=r"127\.0\.0\.1"):
        assert_collector_url("https://both.example.org/")


def test_a_host_that_does_not_resolve_is_refused() -> None:
    with pytest.raises(BlockedUrlError, match="could not be resolved"):
        assert_collector_url("https://no-such-host.example.org/")


def test_https_without_a_host_is_refused() -> None:
    # What "https://" + a bare file path turns into.
    with pytest.raises(BlockedUrlError, match="no host"):
        assert_collector_url("https:///etc/passwd")


def test_a_malformed_url_is_refused_not_raised_as_something_else() -> None:
    with pytest.raises(BlockedUrlError, match="not a valid URL"):
        assert_collector_url("https://news.example.org:port/")


@pytest.mark.parametrize(
    ("allowed", "url"),
    [
        ("intranet.example.org", "https://intranet.example.org/feed.xml"),
        ("Intranet.Example.org ", "https://intranet.example.org/feed.xml"),
        (".corp.example.org", "https://wiki.corp.example.org/"),
        ("*.corp.example.org", "https://wiki.corp.example.org/"),
        ("10.20.0.0/16", "https://intranet.example.org/feed.xml"),
        ("10.20.30.40", "http://10.20.30.40/"),
        ("news.example.org, 10.20.0.0/16", "https://wiki.corp.example.org/"),
        ("news.example.org\n10.20.0.0/16\n", "https://wiki.corp.example.org/"),  # one per line, as the form stores it
        ("core", "http://core/"),
    ],
)
def test_a_collectors_node_can_allow_internal_sources(allowed: str, url: str) -> None:
    assert_collector_url(url, allowed=allowed)


@pytest.mark.parametrize(
    ("allowed", "url"),
    [
        ("intranet.example.org", "https://wiki.corp.example.org/"),  # another host
        ("example.org", "https://intranet.example.org/"),  # a name allows itself, not its subdomains
        (".corp.example.org", "https://evilcorp.example.org.attacker.example/"),
        ("10.20.0.0/16", "http://169.254.169.254/"),
        ("10.20.0.0/16", "http://core/"),
        ("", "https://intranet.example.org/"),
        (None, "https://intranet.example.org/"),
    ],
)
def test_an_exception_allows_only_what_it_names(allowed: str | None, url: str) -> None:
    with pytest.raises(BlockedUrlError):
        assert_collector_url(url, allowed=allowed)


def test_a_refusal_says_where_the_exception_is_set() -> None:
    with pytest.raises(BlockedUrlError, match="collectors node's allowed internal targets"):
        assert_collector_url("https://intranet.example.org/")


@pytest.mark.parametrize(
    "allowed",
    [
        "",
        None,
        "intranet.example.org",
        ".corp.example.org",
        "*.corp.example.org",
        "core",
        "wazuh_manager",
        "10.20.30.40",
        "10.20.0.0/16",
        "fd00:1234::/32",
        "[fd00::1]",
        "intranet.example.org\n10.20.0.0/16\n\n.corp.example.org",
        "intranet.example.org, 10.20.0.0/16",
    ],
)
def test_a_list_of_hosts_domains_addresses_and_networks_can_be_saved(allowed: str | None) -> None:
    assert allowed_targets_problem(allowed) is None


@pytest.mark.parametrize(
    ("allowed", "named"),
    [
        ("0.0.0.0/0", "0.0.0.0/0"),
        ("::/0", "::/0"),
        ("intranet.example.org\n0.0.0.0/0", "0.0.0.0/0"),
        ("*", "*"),
        ("https://intranet.example.org/feed", "https://intranet.example.org/feed"),
        ("intranet.example.org:8443", "intranet.example.org:8443"),
        ("10.20.0.0/40", "10.20.0.0/40"),
        ("two words", "two words"),
        ("-bad-.example.org", "-bad-.example.org"),
    ],
)
def test_a_list_that_allows_everything_or_makes_no_sense_is_refused_naming_the_entry(allowed: str, named: str) -> None:
    assert f"'{named}'" in allowed_targets_problem(allowed)


def test_through_a_proxy_a_name_unknown_here_is_let_through() -> None:
    # The proxy (Tor above all) resolves it; this node cannot.
    assert_collector_url("http://exampleonionaddress.onion/", via_proxy=True)


@pytest.mark.parametrize("url", ["http://127.0.0.1/", "http://localhost/", "http://169.254.169.254/", "http://core/", "file:///etc/passwd"])
def test_a_proxy_does_not_open_the_internal_network(url: str) -> None:
    with pytest.raises(BlockedUrlError):
        assert_collector_url(url, via_proxy=True)


def test_the_problem_is_returned_as_text_for_logging() -> None:
    assert collector_url_problem("https://news.example.org/") is None
    assert "non-public address 172.18.0.5" in collector_url_problem("http://core/")


class _Answers(urllib.request.HTTPHandler, urllib.request.HTTPSHandler):
    """Answer every http(s) request from a table instead of the network.

    A subclass of both standard handlers, so the opener is built without them.
    """

    def __init__(self, answers: dict[str, tuple[int, dict[str, str], bytes]]) -> None:
        super().__init__()
        self.answers = answers
        self.asked: list[str] = []

    def http_open(self, request: urllib.request.Request) -> urllib.response.addinfourl:
        self.asked.append(request.full_url)
        status, headers, body = self.answers[request.full_url]
        message = Message()
        for name, value in headers.items():
            message[name] = value
        response = urllib.response.addinfourl(io.BytesIO(body), message, request.full_url, status)
        response.msg = "status"
        return response

    https_open = http_open


def test_the_opener_refuses_before_connecting() -> None:
    answers = _Answers({})
    opener = build_guarded_opener(answers)

    with pytest.raises(BlockedUrlError):
        opener("http://169.254.169.254/latest/meta-data/")
    with pytest.raises(BlockedUrlError):
        opener(urllib.request.Request("file:///etc/passwd"))  # noqa: S310 - the scheme under test
    assert answers.asked == []


def test_the_opener_follows_a_redirect_to_a_public_address() -> None:
    answers = _Answers(
        {
            "https://news.example.org/old": (302, {"Location": "/new"}, b""),
            "https://news.example.org/new": (200, {}, b"the feed"),
        },
    )

    with build_guarded_opener(answers)("https://news.example.org/old", timeout=5) as response:
        assert response.read() == b"the feed"


@pytest.mark.parametrize("target", ["http://169.254.169.254/latest/meta-data/", "http://core/api/v1/isalive"])
def test_the_opener_refuses_a_redirect_to_an_internal_address(target: str) -> None:
    answers = _Answers({"https://news.example.org/feed": (302, {"Location": target}, b"")})

    with pytest.raises(BlockedUrlError):
        build_guarded_opener(answers)("https://news.example.org/feed")
    assert answers.asked == ["https://news.example.org/feed"]


def test_the_opener_refuses_a_redirect_to_a_local_file() -> None:
    # urllib itself refuses to be redirected off http(s), before the guard is asked.
    answers = _Answers({"https://news.example.org/feed": (302, {"Location": "file:///etc/passwd"}, b"")})

    with pytest.raises((BlockedUrlError, urllib.error.HTTPError)):
        build_guarded_opener(answers)("https://news.example.org/feed")
    assert answers.asked == ["https://news.example.org/feed"]


def test_the_opener_fetches_and_follows_redirects_within_what_the_node_allows() -> None:
    answers = _Answers(
        {
            "https://intranet.example.org/old": (302, {"Location": "https://wiki.corp.example.org/new"}, b""),
            "https://wiki.corp.example.org/new": (200, {}, b"the feed"),
        },
    )

    with build_guarded_opener(answers, allowed="intranet.example.org\n.corp.example.org")("https://intranet.example.org/old") as response:
        assert response.read() == b"the feed"


def test_the_opener_refuses_a_redirect_from_an_allowed_host_to_one_that_is_not() -> None:
    answers = _Answers({"https://intranet.example.org/feed": (302, {"Location": "http://core/api/v1/isalive"}, b"")})

    with pytest.raises(BlockedUrlError):
        build_guarded_opener(answers, allowed="intranet.example.org")("https://intranet.example.org/feed")
    assert answers.asked == ["https://intranet.example.org/feed"]
