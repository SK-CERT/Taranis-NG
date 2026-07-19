"""Same-origin validation of the login redirect target (open-redirect guard)."""

from __future__ import annotations

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


def test_login_cookie_is_secure_over_https() -> None:
    with app.test_request_context("/", base_url="https://taranis.example"):
        assert auth._login_cookie_kwargs() == {"secure": True, "samesite": "Lax"}


def test_login_cookie_not_secure_over_http() -> None:
    # plain-HTTP local/E2E runs must still receive the cookie
    with app.test_request_context("/", base_url="http://taranis.local"):
        assert auth._login_cookie_kwargs()["secure"] is False
