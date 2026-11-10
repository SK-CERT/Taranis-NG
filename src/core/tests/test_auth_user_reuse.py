"""Behind auth_required, the endpoint's own get_user_from_jwt() reuses the user just checked.

Every endpoint asks for its user again after the decorator resolved it: that re-verified the
token and reloaded the user (permissions, hotkeys) once more per request.
"""

from __future__ import annotations

import types

import pytest
from flask import Flask, g
from managers import auth_manager


@pytest.fixture
def app() -> Flask:
    return Flask(__name__)


def test_the_checked_user_is_reused(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    checked = types.SimpleNamespace(id=1, username="alice")
    monkeypatch.setattr(auth_manager, "get_user_from_jwt_token", lambda: pytest.fail("the token must not be verified again"))
    monkeypatch.setattr(auth_manager, "uses_api_key", lambda: False)
    monkeypatch.setattr(auth_manager.db, "session", types.SimpleNamespace(is_active=True))

    with app.test_request_context("/"):
        g.authenticated_user = checked
        assert auth_manager.get_user_from_jwt() is checked


def test_without_auth_required_the_token_is_verified(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    from_token = types.SimpleNamespace(id=2, username="bob")
    monkeypatch.setattr(auth_manager, "get_user_from_jwt_token", lambda: from_token)
    monkeypatch.setattr(auth_manager, "uses_api_key", lambda: False)
    monkeypatch.setattr(auth_manager.db, "session", types.SimpleNamespace(is_active=True))

    with app.test_request_context("/"):
        assert auth_manager.get_user_from_jwt() is from_token


def test_each_request_starts_without_a_user(app: Flask) -> None:
    with app.test_request_context("/"):
        g.authenticated_user = types.SimpleNamespace(id=1)
    with app.test_request_context("/"):
        assert g.get("authenticated_user") is None
