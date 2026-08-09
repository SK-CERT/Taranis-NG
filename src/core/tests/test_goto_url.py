"""Same-origin validation of the login redirect target (open-redirect guard)."""

from __future__ import annotations

from http import HTTPStatus
from types import SimpleNamespace

import pytest
from api import auth
from flask import Flask

app = Flask(__name__)


@pytest.mark.parametrize(
    ("goto", "expected"),
    [
        ("/dashboard", True),
        ("/", True),
        ("https://taranis.example/reports", True),
        ("http://taranis.example/reports", True),
        ("//evil.com", False),  # protocol-relative
        ("/\\evil.com", False),  # backslash the browser may normalize to //
        ("https://evil.com/x", False),  # cross-origin absolute
        ("javascript:alert(1)", False),  # non-http scheme
        ("", False),
    ],
)
def test_is_safe_goto_url(goto: str, expected: bool) -> None:
    with app.test_request_context("/", base_url="https://taranis.example"):
        assert auth._is_safe_goto_url(goto) is expected


def test_safe_goto_url_falls_back_to_root_for_hostile_input() -> None:
    with app.test_request_context("/", base_url="https://taranis.example"):
        assert auth._safe_goto_url("https://evil.com/x") == "/"
        assert auth._safe_goto_url(None) == "/"
        assert auth._safe_goto_url("/reports") == "/reports"


@pytest.mark.parametrize(
    ("goto", "expected"),
    [
        ("/v2", "/v2"),
        ("/v2/", "/v2/"),
        ("/v2/dashboard", "/v2/dashboard"),
        ("https://taranis.example/v2/assess?tab=new", "https://taranis.example/v2/assess?tab=new"),
        ("/login", None),
        ("/dashboard", None),
        ("/v2-lookalike", None),
        ("https://evil.example/v2/dashboard", None),
        ("http://taranis.example/v2/dashboard", None),
        (None, None),
    ],
)
def test_redirect_provider_targets_only_vue3_mount(goto: str | None, expected: str | None) -> None:
    with app.test_request_context("/", base_url="https://taranis.example"):
        assert auth._redirect_provider_goto_url(goto) == expected


def test_oauth_start_clearly_rejects_legacy_vue2_target(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth.auth_manager, "get_oauth_authenticator", lambda _slug: SimpleNamespace(provider=SimpleNamespace(id=1)))

    with app.test_request_context(
        "/api/v1/auth/oauth/corporate/login?gotoUrl=/dashboard",
        base_url="https://taranis.example",
    ):
        response = auth.OAuthLoginRedirect.get.__wrapped__(auth.OAuthLoginRedirect(), "corporate")

    assert response == ({"error": "Redirect login requires a same-origin /v2 target"}, HTTPStatus.BAD_REQUEST)


def test_saml_start_clearly_rejects_legacy_vue2_target(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth.auth_manager, "get_saml_authenticator", lambda _slug: SimpleNamespace(provider=SimpleNamespace(id=1)))

    with app.test_request_context(
        "/api/v1/auth/saml/corporate/login?gotoUrl=/dashboard",
        base_url="https://taranis.example",
    ):
        response = auth.SamlLoginRedirect.get.__wrapped__(auth.SamlLoginRedirect(), "corporate")

    assert response == ({"error": "Redirect login requires a same-origin /v2 target"}, HTTPStatus.BAD_REQUEST)


def test_login_cookie_is_secure_over_https() -> None:
    with app.test_request_context("/", base_url="https://taranis.example"):
        assert auth._login_cookie_kwargs() == {
            "secure": True,
            "httponly": True,
            "samesite": "Strict",
            "path": "/api/v1/auth/redeem",
            "max_age": auth.REDIRECT_REDEMPTION_SECONDS,
        }


def test_login_cookie_not_secure_over_http() -> None:
    # plain-HTTP local/E2E runs must still receive the cookie
    with app.test_request_context("/", base_url="http://taranis.local"):
        assert auth._login_cookie_kwargs()["secure"] is False


def test_redemption_requires_same_origin_when_browser_origin_is_present() -> None:
    with app.test_request_context(
        "/api/v1/auth/redeem",
        method="POST",
        base_url="https://taranis.example",
        headers={"Origin": "https://taranis.example", "Sec-Fetch-Site": "same-origin"},
    ):
        assert auth._is_same_origin_request() is True

    with app.test_request_context(
        "/api/v1/auth/redeem",
        method="POST",
        base_url="https://taranis.example",
        headers={"Origin": "https://other.example", "Sec-Fetch-Site": "same-site"},
    ):
        assert auth._is_same_origin_request() is False
