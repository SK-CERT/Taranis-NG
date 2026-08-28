"""Redirect-flow exits must not become open redirects.

`_login_error_redirect` and `_finish_redirect_login` are the two chokepoints
every OIDC/OAuth2/SAML login passes through on its way back to the GUI. Most of
their fifteen call sites hand them a goto_url read straight out of the stored
auth transaction rather than one already passed through `_safe_goto_url`, so the
check has to live in the helpers themselves.
"""

from __future__ import annotations

import pytest
from api import auth
from flask import Flask

EVIL = "https://evil.example/phish"


@pytest.fixture
def app() -> Flask:
    return Flask(__name__)


def _location(response: object) -> str:
    return response.headers["Location"]


def test_error_redirect_refuses_a_foreign_host(app: Flask) -> None:
    with app.test_request_context("/", base_url="https://taranis.example"):
        assert _location(auth._login_error_redirect(EVIL, "auth_failed")).startswith("/?login_error=")


def test_error_redirect_keeps_a_same_origin_target(app: Flask) -> None:
    with app.test_request_context("/", base_url="https://taranis.example"):
        assert _location(auth._login_error_redirect("/v2/login", "auth_failed")) == "/v2/login?login_error=auth_failed"
        absolute = _location(auth._login_error_redirect("https://taranis.example/v2/", "auth_failed"))
        assert absolute.startswith("https://taranis.example/v2/?login_error=")


@pytest.mark.parametrize("candidate", ["//evil.example/x", "/\\evil.example/x", "https://evil.example"])
def test_protocol_relative_and_backslash_forms_are_refused(app: Flask, candidate: str) -> None:
    # browsers normalize these to another origin, so a plain startswith("/") is not enough
    with app.test_request_context("/", base_url="https://taranis.example"):
        assert _location(auth._login_error_redirect(candidate, "auth_failed")).startswith("/?login_error=")


def test_successful_redirect_login_refuses_a_foreign_host(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth.auth_transaction_manager, "create", lambda *_a, **_kw: "handle-1")
    with app.test_request_context("/", base_url="https://taranis.example"):
        response = auth._finish_redirect_login(EVIL, {"access_token": "t", "code": "OK"})
    assert _location(response) == "/"
    # the redemption cookie must not have been planted on the attacker's origin either
    assert "evil.example" not in response.headers.get("Set-Cookie", "")
