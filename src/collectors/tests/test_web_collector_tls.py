"""The web collector's browser checks TLS certificates unless the source opts out.

Both drivers used to start with ``--ignore-certificate-errors``: anyone on the network path
could change what a source collected, and read the basic-auth credentials it sends.
"""

from __future__ import annotations

import collections
import datetime as dt
import ssl
import types
import urllib.error

import pytest
from collectors.web_collector import WebCollector

from collectors import web_collector


class RecordingLogger:
    """Swallows log calls."""

    def __getattr__(self, _level: str) -> object:
        """Any level is a no-op."""
        return lambda *_args, **_kwargs: None


@pytest.fixture
def started(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Record the options each driver is started with, without starting a browser."""
    seen: dict = {}

    def driver(name: str) -> object:
        def start(*, service: object, options: object) -> object:  # noqa: ARG001
            seen[name] = options
            return types.SimpleNamespace(implicitly_wait=lambda _seconds: None)

        return start

    monkeypatch.setattr(web_collector.webdriver, "Chrome", driver("chrome"))
    monkeypatch.setattr(web_collector.webdriver, "Firefox", driver("firefox"))
    monkeypatch.setattr(web_collector, "ChromeService", lambda **_kwargs: None)
    monkeypatch.setattr(web_collector, "FirefoxService", lambda **_kwargs: None)
    return seen


def browser_options(started: dict, webdriver: str, **parameters: str) -> object:
    collector = WebCollector()
    collector.source = types.SimpleNamespace(
        id="source-1",
        param_key_values=collections.defaultdict(str, {"WEB_URL": "https://93.184.216.34/", "WEBDRIVER": webdriver, **parameters}),
        logger=RecordingLogger(),
        allowed_private_targets="",
    )
    assert collector._WebCollector__parse_settings() is True
    assert collector._WebCollector__get_headless_driver() is not None
    return started[webdriver]


@pytest.mark.parametrize("webdriver", ["chrome", "firefox"])
def test_certificates_are_checked_by_default(started: dict, webdriver: str) -> None:
    options = browser_options(started, webdriver)

    assert options.accept_insecure_certs is False
    assert "--ignore-certificate-errors" not in options.arguments


@pytest.mark.parametrize("webdriver", ["chrome", "firefox"])
def test_a_source_can_opt_out(started: dict, webdriver: str) -> None:
    options = browser_options(started, webdriver, IGNORE_TLS_ERRORS="true")

    assert options.accept_insecure_certs is True


class _Browser:
    """Answers the error-page probe as Chrome does."""

    def __init__(self, protocol: str, code: str = "") -> None:
        self.answer = [protocol, code]

    def execute_script(self, _script: str) -> list[str]:
        return self.answer


@pytest.mark.parametrize(
    "code",
    ["net::ERR_CERT_AUTHORITY_INVALID", "net::ERR_CERT_DATE_INVALID", "net::ERR_CERT_COMMON_NAME_INVALID", "net::ERR_SSL_PROTOCOL_ERROR"],
)
def test_chrome_s_certificate_warning_page_is_reported_as_such(code: str) -> None:
    """Chrome does not fail get() for an untrusted certificate: it shows its warning page under the site's URL."""
    reason = web_collector.browser_error_page(_Browser("chrome-error:", code))

    assert reason is not None
    assert code in reason
    assert "Ignore TLS certificate errors" in reason


def test_another_chrome_error_page_says_what_it_is() -> None:
    assert web_collector.browser_error_page(_Browser("chrome-error:", "net::ERR_CONNECTION_RESET")) == (
        "The browser could not load the page (net::ERR_CONNECTION_RESET)"
    )


@pytest.mark.parametrize("protocol", ["https:", "http:"])
def test_a_loaded_site_is_no_error_page(protocol: str) -> None:
    assert web_collector.browser_error_page(_Browser(protocol, "net::ERR_CERT_AUTHORITY_INVALID")) is None


def test_a_browser_that_cannot_answer_is_no_error_page() -> None:
    class Gone:
        def execute_script(self, _script: str) -> list[str]:
            msg = "no such window"
            raise RuntimeError(msg)

    assert web_collector.browser_error_page(Gone()) is None


def test_the_if_modified_check_leaves_a_certificate_error_to_the_collection() -> None:
    """A source that ignores TLS errors must not get an error from the pre-check on every run."""
    from collectors import base_collector  # noqa: PLC0415 - the module under test, imported where used

    logged: dict[str, list[str]] = collections.defaultdict(list)

    def opener(_request: object, timeout: int) -> None:  # noqa: ARG001
        reason = ssl.SSLCertVerificationError(1, "[SSL: CERTIFICATE_VERIFY_FAILED] self-signed certificate")
        raise urllib.error.URLError(reason)

    source = types.SimpleNamespace(
        url="https://self-signed.example.org/",
        user_agent=None,
        last_collected=dt.datetime(2026, 11, 25, tzinfo=dt.UTC),
        opener=opener,
        logger=types.SimpleNamespace(
            debug=logged["debug"].append,
            exception=logged["exception"].append,
        ),
    )

    assert base_collector.not_modified(source) is False
    assert logged["exception"] == []
    assert "TLS error" in logged["debug"][0]
