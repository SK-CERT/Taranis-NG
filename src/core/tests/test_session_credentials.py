"""Changing a password ends the account's other sessions.

A token stayed valid for its four hours after the password changed - and the GUI refreshes it
before it runs out, so a stolen session outlived any password reset. Every token now carries an
HMAC of the account's id, username and password hash, and one that no longer matches is refused.
"""

from __future__ import annotations

from http import HTTPStatus
from types import SimpleNamespace

import pytest
from api import config as config_api
from auth import base_authenticator
from auth.base_authenticator import session_credential
from flask import Flask, jsonify
from flask_jwt_extended import JWTManager, create_access_token
from managers import auth_manager
from model.security_settings import SecuritySettings
from model.token_blacklist import TokenBlacklist
from model.user import User

SECRET = "session-credential-test-secret-with-sufficient-length"


@pytest.fixture
def account(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    alice = SimpleNamespace(id=7, username="alice", password="hash-1", status="active", permissions=[], roles=[])
    monkeypatch.setattr(User, "find", classmethod(lambda _cls, username: alice if username == alice.username else None))
    monkeypatch.setattr(SecuritySettings, "get_auth_generation", classmethod(lambda _cls: 1))
    monkeypatch.setattr(TokenBlacklist, "is_blacklisted", classmethod(lambda _cls, _jti: False))
    monkeypatch.setattr(auth_manager, "_find_active_user", lambda username: alice if username == alice.username else None)
    for name in ("store_auth_error_activity", "store_auth_warning_activity", "store_user_activity", "store_user_auth_error_activity"):
        monkeypatch.setattr(auth_manager.log_manager, name, lambda *_args, **_kwargs: None)
    return alice


@pytest.fixture
def app() -> Flask:
    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"] = SECRET
    auth_manager._configure_auth_generation_verification(JWTManager(app))

    @app.get("/me")
    @auth_manager.jwt_token_required
    def me():  # noqa: ANN202
        return jsonify(ok=True)

    @app.get("/publish")
    @auth_manager.auth_required("PUBLISH_ACCESS")
    def publish():  # noqa: ANN202
        return jsonify(ok=True)

    return app


def _token(app: Flask, account: SimpleNamespace, **claims: object) -> str:
    with app.app_context():
        defaults = {auth_manager.AUTH_GENERATION_CLAIM: 1, "cred": session_credential(account)}
        return create_access_token(identity=account.username, additional_claims={**defaults, **claims})


def _get(app: Flask, path: str, token: str) -> object:
    return app.test_client().get(path, headers={"Authorization": f"Bearer {token}"})


def test_the_credential_follows_the_password_and_the_username(account: SimpleNamespace) -> None:
    before = session_credential(account)

    account.password = "hash-2"
    after_password = session_credential(account)
    account.username = "alice2"

    assert len({before, after_password, session_credential(account)}) == 3
    assert "hash" not in before


def test_a_token_is_refused_once_the_password_changed(app: Flask, account: SimpleNamespace) -> None:
    token = _token(app, account)
    assert _get(app, "/me", token).status_code == HTTPStatus.OK

    account.password = "hash-2"
    response = _get(app, "/me", token)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.get_json()["code"] == "SESSION_INVALID"


def test_auth_required_says_the_session_ended(app: Flask, account: SimpleNamespace) -> None:
    token = _token(app, account)
    account.password = None  # the local password was removed

    response = _get(app, "/publish", token)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.get_json() == {"error": "Authentication token is no longer valid", "code": "SESSION_INVALID"}


def test_a_token_without_the_credential_is_refused(app: Flask, account: SimpleNamespace) -> None:
    assert _get(app, "/me", _token(app, account, cred=None)).status_code == HTTPStatus.UNAUTHORIZED


def test_decoding_a_token_for_sse_or_previews_checks_it_too(app: Flask, account: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_manager.Config, "JWT_SECRET_KEY", SECRET)
    token = _token(app, account)
    assert auth_manager.decode_user_from_jwt(token) is account

    account.password = "hash-2"

    assert auth_manager.decode_user_from_jwt(token) is None


def test_changing_one_s_own_password_hands_back_a_new_token(account: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    issued: list = []

    def generate_jwt(user: SimpleNamespace, **kwargs: object) -> tuple[dict, HTTPStatus]:
        issued.append(kwargs)
        return {"access_token": f"new-{user.username}"}, HTTPStatus.OK

    monkeypatch.setattr(base_authenticator.BaseAuthenticator, "generate_jwt", staticmethod(generate_jwt))
    monkeypatch.setattr(config_api, "get_jwt", lambda: {"auth_time": 1700000000})
    before = session_credential(account)

    monkeypatch.setattr(config_api, "get_user_from_jwt", lambda: account)
    assert config_api._own_session_renewed(account, before) is None  # nothing changed
    account.password = "hash-2"
    assert config_api._own_session_renewed(account, before) == ({"access_token": "new-alice"}, HTTPStatus.OK)
    # The same session goes on, with its sign-in time and so its maximum length.
    assert issued == [{"record_login": False, "auth_time": 1700000000}]

    # An administrator changing someone else's password gets nothing: that user's sessions end.
    monkeypatch.setattr(config_api, "get_user_from_jwt", lambda: SimpleNamespace(id=1))
    assert config_api._own_session_renewed(account, before) is None
