"""Logging out ends the sign-in, not only the token it was called with.

Logout blacklisted the jti it was given, but a refresh mints a new jti and the old token stays
valid: a stolen token refreshed once survived its owner's logout until the session's maximum
length, and so did a second tab holding its own refreshed token. Every token now carries the
session id of its sign-in (``sid``), a refresh and the own-password renewal keep it, and logging
out blacklists it too.
"""

from __future__ import annotations

import ast
from datetime import datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace

import pytest
from api import auth as auth_api
from api import config as config_api
from auth.base_authenticator import BaseAuthenticator
from flask import Flask, jsonify
from flask_jwt_extended import JWTManager, create_access_token, decode_token, verify_jwt_in_request
from managers import auth_manager
from managers.api_manager import SafeErrorApi
from model import token_blacklist
from model.security_settings import SecuritySettings
from model.token_blacklist import TokenBlacklist
from model.user import User

SECRET = "session-logout-test-secret-with-sufficient-length"
CONFIG = Path(__file__).resolve().parents[1] / "config.py"


@pytest.fixture
def alice(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    account = SimpleNamespace(
        id=7,
        username="alice",
        name="Alice Example",
        password="hash-1",
        status="active",
        permissions=[SimpleNamespace(id="PUBLISH_ACCESS")],
        roles=[],
        touch_login=lambda: None,
        get_current_organization_name=lambda: "",
        get_permissions=list,
    )
    monkeypatch.setattr(User, "find", classmethod(lambda _cls, username: account if username == account.username else None))
    monkeypatch.setattr(auth_manager, "_find_active_user", lambda username: account if username == account.username else None)
    monkeypatch.setattr(SecuritySettings, "get_auth_generation", classmethod(lambda _cls: 1))
    monkeypatch.setattr(SecuritySettings, "get_session_max_hours", classmethod(lambda _cls: 24))
    monkeypatch.setattr(auth_manager.Config, "JWT_SECRET_KEY", SECRET)
    monkeypatch.setattr(auth_manager.db, "session", SimpleNamespace(is_active=True))
    monkeypatch.setattr(auth_api, "redis_client", SimpleNamespace(delete=lambda *_keys: 1))
    for name in ("store_auth_error_activity", "store_auth_warning_activity", "store_user_activity", "store_user_auth_error_activity"):
        monkeypatch.setattr(auth_manager.log_manager, name, lambda *_args, **_kwargs: None)
    return account


@pytest.fixture
def blacklist(monkeypatch: pytest.MonkeyPatch) -> set[str]:
    """The stored blacklist entries, kept the way the model keys them (see the storage tests)."""
    stored: set[str] = set()

    def entries(jwt_id: str | None, session_id: str | None) -> set[str]:
        return {entry for entry in (jwt_id, session_id and f"sid:{session_id}") if entry}

    def add(_cls: type, jwt_id: str, session_id: str | None = None) -> None:
        stored.update(entries(jwt_id, session_id))

    def is_blacklisted(_cls: type, jwt_id: str | None, session_id: str | None = None) -> bool:
        return bool(stored & entries(jwt_id, session_id))

    monkeypatch.setattr(TokenBlacklist, "add", classmethod(add))
    monkeypatch.setattr(TokenBlacklist, "is_blacklisted", classmethod(is_blacklisted))
    return stored


@pytest.fixture
def app(alice: SimpleNamespace) -> Flask:  # noqa: ARG001 - the account the tokens are for
    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"] = SECRET
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 14400
    auth_manager._configure_auth_generation_verification(JWTManager(app))

    @app.get("/me")
    @auth_manager.jwt_token_required
    def me():  # noqa: ANN202
        return jsonify(ok=True)

    @app.get("/publish")
    @auth_manager.auth_required("PUBLISH_ACCESS")
    def publish():  # noqa: ANN202
        return jsonify(ok=True)

    api = SafeErrorApi(app)
    api.add_resource(auth_api.Refresh, "/refresh")
    api.add_resource(auth_api.Logout, "/logout")
    return app


def _sign_in(app: Flask, account: SimpleNamespace) -> str:
    with app.app_context():
        body, status = BaseAuthenticator.generate_jwt(account)
    assert status == HTTPStatus.OK
    return body["access_token"]


def _claims(app: Flask, token: str) -> dict:
    with app.app_context():
        return decode_token(token, allow_expired=True)


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _refresh(app: Flask, token: str) -> str:
    response = app.test_client().get("/refresh", headers=_bearer(token))
    assert response.status_code == HTTPStatus.OK, response.get_json()
    return response.get_json()["access_token"]


@pytest.mark.usefixtures("blacklist")
@pytest.mark.parametrize("logged_out_with", ["earlier", "later"])
def test_logging_out_ends_every_token_of_the_sign_in(app: Flask, alice: SimpleNamespace, logged_out_with: str) -> None:
    earlier = _sign_in(app, alice)
    later = _refresh(app, earlier)  # a thief's refresh of the stolen token, or another tab's
    other_sign_in = _sign_in(app, alice)  # the same person signed in on another computer
    client = app.test_client()

    logout = client.post("/logout", headers=_bearer(earlier if logged_out_with == "earlier" else later))

    assert logout.status_code == HTTPStatus.OK
    for token in (earlier, later):
        for path in ("/me", "/publish", "/refresh"):
            response = client.get(path, headers=_bearer(token))
            assert response.status_code == HTTPStatus.UNAUTHORIZED, path
            assert response.get_json()["code"] == "SESSION_INVALID", path
        assert auth_manager.decode_user_from_jwt(token) is None  # SSE, product previews
    # Another sign-in of the same account is not affected.
    assert client.get("/me", headers=_bearer(other_sign_in)).status_code == HTTPStatus.OK
    assert auth_manager.decode_user_from_jwt(other_sign_in) is alice


@pytest.mark.usefixtures("blacklist")
def test_logging_out_with_redis_down_still_ends_the_sign_in(app: Flask, alice: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    # The SSE session lives in Redis; the token and its sign-in are revoked before it is touched.
    def unreachable(*_keys: str) -> int:
        raise ConnectionError

    monkeypatch.setattr(auth_api, "redis_client", SimpleNamespace(delete=unreachable))
    token = _sign_in(app, alice)
    client = app.test_client()

    assert client.post("/logout", headers=_bearer(token)).status_code == HTTPStatus.OK
    assert client.get("/me", headers=_bearer(token)).status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.usefixtures("blacklist")
def test_a_refresh_keeps_the_session_id_and_a_sign_in_mints_a_new_one(app: Flask, alice: SimpleNamespace) -> None:
    first = _sign_in(app, alice)
    refreshed = _refresh(app, first)

    assert _claims(app, refreshed)["sid"] == _claims(app, first)["sid"]
    assert _claims(app, refreshed)["jti"] != _claims(app, first)["jti"]
    assert _claims(app, _sign_in(app, alice))["sid"] != _claims(app, first)["sid"]


def test_the_token_renewed_after_one_s_own_password_change_keeps_the_session(
    app: Flask,
    alice: SimpleNamespace,
    blacklist: set[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = _sign_in(app, alice)
    before = config_api.session_credential(alice)
    monkeypatch.setattr(config_api, "get_user_from_jwt", lambda: alice)

    with app.test_request_context("/users/7", method="PUT", headers=_bearer(token)):
        verify_jwt_in_request()
        alice.password = "hash-2"
        body, status = config_api._own_session_renewed(alice, before)

    assert status == HTTPStatus.OK
    renewed = body["access_token"]
    assert _claims(app, renewed)["sid"] == _claims(app, token)["sid"]
    # Logging out of the sign-in ends the renewed token too.
    assert app.test_client().post("/logout", headers=_bearer(renewed)).status_code == HTTPStatus.OK
    assert f"sid:{_claims(app, token)['sid']}" in blacklist


@pytest.mark.parametrize("session_id", [None, "", 5])
def test_a_token_without_a_session_id_is_refused(
    app: Flask,
    alice: SimpleNamespace,
    session_id: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(TokenBlacklist, "is_blacklisted", classmethod(lambda _cls, *_entries: False))  # nothing logged out
    with app.app_context():
        claims = {auth_manager.AUTH_GENERATION_CLAIM: 1, "cred": config_api.session_credential(alice), "auth_time": 1}
        if session_id is not None:
            claims["sid"] = session_id
        token = create_access_token(identity="alice", additional_claims=claims)

    for path in ("/me", "/publish", "/refresh"):
        response = app.test_client().get(path, headers=_bearer(token))
        assert response.status_code == HTTPStatus.UNAUTHORIZED, path
        assert response.get_json()["code"] == "SESSION_INVALID", path
    assert auth_manager.decode_user_from_jwt(token) is None


@pytest.mark.usefixtures("blacklist")
def test_a_session_is_never_continued_under_a_new_id(app: Flask, alice: SimpleNamespace) -> None:
    """Continuing a sign-in without its id would make a token its logout cannot reach."""
    with app.app_context():
        assert auth_manager.refresh(alice, 1_800_000_000, None)[0]["code"] == "SESSION_INVALID"
        body, status = BaseAuthenticator.generate_jwt(alice, record_login=False, auth_time=1_800_000_000)

    assert (status, body["code"]) == (HTTPStatus.UNAUTHORIZED, "SESSION_EXPIRED")


# --- storage ----------------------------------------------------------------------------------


class _Session:
    def __init__(self) -> None:
        self.added: list[str] = []
        self.queries: list[str] = []
        self.commits = 0

    def add(self, record: TokenBlacklist) -> None:
        self.added.append(record.token)

    def commit(self) -> None:
        self.commits += 1

    def query(self, expression: object) -> SimpleNamespace:
        self.queries.append(str(expression.compile(compile_kwargs={"literal_binds": True})))
        return SimpleNamespace(scalar=lambda: True)


def test_a_logout_stores_the_token_and_its_sign_in(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _Session()
    monkeypatch.setattr(token_blacklist.db, "session", session)

    TokenBlacklist.add("3f0c7a52-0000-4000-8000-000000000001", "a1b2c3")

    assert session.added == ["3f0c7a52-0000-4000-8000-000000000001", "sid:a1b2c3"]
    assert session.commits == 1


def test_one_lookup_covers_the_token_and_its_sign_in(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _Session()
    monkeypatch.setattr(token_blacklist.db, "session", session)

    assert TokenBlacklist.is_blacklisted("jti-1", "a1b2c3") is True
    assert TokenBlacklist.is_blacklisted(None, None) is False  # nothing to look up

    assert len(session.queries) == 1
    assert "IN ('jti-1', 'sid:a1b2c3')" in session.queries[0]


def test_a_logged_out_sign_in_is_kept_longer_than_its_tokens_live(monkeypatch: pytest.MonkeyPatch) -> None:
    """After logout no token of the sign-in can be refreshed; the last one lives one token lifetime."""
    thresholds: list[datetime] = []
    monkeypatch.setattr(TokenBlacklist, "delete_older", classmethod(lambda _cls, check_time: thresholds.append(check_time)))
    config_class = next(node for node in ast.parse(CONFIG.read_text()).body if isinstance(node, ast.ClassDef) and node.name == "Config")
    lifetime = next(
        node.value.value
        for node in config_class.body
        if isinstance(node, ast.Assign) and any(getattr(target, "id", None) == "JWT_ACCESS_TOKEN_EXPIRES" for target in node.targets)
    )
    before = datetime.now(auth_manager.TZ)

    auth_manager.cleanup_token_blacklist(Flask(__name__))

    assert before - thresholds[0] >= timedelta(seconds=lifetime)
