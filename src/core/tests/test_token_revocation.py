"""A logged-out token is refused everywhere, not only where a decorator remembered to look.

Logout blacklists the token's jti, but only ``auth_required`` and ``jwt_token_required`` checked
the blacklist, by hand. Sixteen endpoints with a bare ``@jwt_required()`` - TOTP and passkey
enrollment, hotkeys, word lists, the dashboard, settings - accepted a stolen token after its
owner logged out, for up to four hours; the dashboard did not even ask whether the account was
still active.
"""

from __future__ import annotations

import ast
from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace

import pytest
from flask import Flask, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
from managers import auth_manager
from managers.api_manager import SafeErrorApi
from model.security_settings import SecuritySettings
from model.token_blacklist import TokenBlacklist

API = Path(__file__).resolve().parents[1] / "api"
SECRET = "token-revocation-test-secret-with-sufficient-length"


@pytest.fixture
def revoked(monkeypatch: pytest.MonkeyPatch) -> set[str]:
    """The jtis that were logged out."""
    jtis: set[str] = set()
    monkeypatch.setattr(SecuritySettings, "get_auth_generation", classmethod(lambda _cls: 1))
    monkeypatch.setattr(TokenBlacklist, "is_blacklisted", classmethod(lambda _cls, jti: jti in jtis))
    for name in ("store_auth_error_activity", "store_auth_warning_activity", "store_user_activity"):
        monkeypatch.setattr(auth_manager.log_manager, name, lambda *_args, **_kwargs: None)
    return jtis


def _app() -> Flask:
    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"] = SECRET
    auth_manager._configure_auth_generation_verification(JWTManager(app))

    @app.get("/bare")
    @jwt_required()
    def bare():  # noqa: ANN202
        return jsonify(ok=True)

    return app


def _token(app: Flask, jti_holder: dict) -> str:
    with app.app_context():
        token = create_access_token(identity="alice", additional_claims={auth_manager.AUTH_GENERATION_CLAIM: 1})
        from flask_jwt_extended import decode_token  # noqa: PLC0415 - needs the app context

        jti_holder["jti"] = decode_token(token)["jti"]
    return token


def test_every_jwt_check_refuses_a_logged_out_token(revoked: set[str]) -> None:
    app = _app()
    held: dict = {}
    token = _token(app, held)
    client = app.test_client()

    assert client.get("/bare", headers={"Authorization": f"Bearer {token}"}).status_code == HTTPStatus.OK
    revoked.add(held["jti"])
    assert client.get("/bare", headers={"Authorization": f"Bearer {token}"}).status_code == HTTPStatus.UNAUTHORIZED


def test_a_revocation_that_cannot_be_checked_refuses(monkeypatch: pytest.MonkeyPatch, revoked: set[str]) -> None:  # noqa: ARG001
    def broken(_cls: type, _jti: str) -> bool:
        message = "database down"
        raise RuntimeError(message)

    monkeypatch.setattr(TokenBlacklist, "is_blacklisted", classmethod(broken))

    assert auth_manager._token_revoked({}, {"jti": "x"}) is True


def test_a_resource_answers_401_not_500_for_a_logged_out_token(monkeypatch: pytest.MonkeyPatch, revoked: set[str]) -> None:
    app = _app()
    from api import user as user_api  # noqa: PLC0415

    SafeErrorApi(app).add_resource(user_api.UserHotkeys, "/hotkeys")
    monkeypatch.setattr(auth_manager, "_find_active_user", lambda _sub: SimpleNamespace(id=1, username="alice"))
    monkeypatch.setattr(user_api.Hotkey, "get_json", classmethod(lambda _cls, _user: {"items": []}))
    held: dict = {}
    token = _token(app, held)
    revoked.add(held["jti"])

    response = app.test_client().get("/hotkeys", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_decoding_a_session_token_refuses_a_logged_out_one(revoked: set[str]) -> None:
    app = _app()
    held: dict = {}
    token = _token(app, held)
    revoked.add(held["jti"])

    original = auth_manager.Config.JWT_SECRET_KEY
    try:
        auth_manager.Config.JWT_SECRET_KEY = SECRET
        assert auth_manager.decode_user_from_jwt(token) is None
    finally:
        auth_manager.Config.JWT_SECRET_KEY = original


@pytest.mark.parametrize("module", ["user.py", "dashboard.py", "config.py"])
def test_no_endpoint_uses_a_bare_jwt_required(module: str) -> None:
    tree = ast.parse((API / module).read_text())
    decorators = [ast.unparse(decorator) for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) for decorator in node.decorator_list]

    assert not [decorator for decorator in decorators if decorator.startswith("jwt_required")]
