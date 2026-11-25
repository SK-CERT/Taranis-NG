"""The web collector's browser checks TLS certificates unless the source opts out.

Both drivers used to start with ``--ignore-certificate-errors``: anyone on the network path
could change what a source collected, and read the basic-auth credentials it sends.
"""

from __future__ import annotations

import collections
import types

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
