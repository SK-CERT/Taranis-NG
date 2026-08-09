"""Authentication generation invalidates every older JWT centrally."""

from __future__ import annotations

from http import HTTPStatus

import pytest
from flask import Flask, jsonify
from flask_jwt_extended import JWTManager, create_access_token, decode_token, jwt_required
from managers import auth_manager
from model.security_settings import SecuritySettings


@pytest.fixture
def generation_app(monkeypatch: pytest.MonkeyPatch) -> tuple[Flask, dict[str, int], list[str]]:
    generation = {"value": 2}
    issued_on_refresh: list[str] = []
    monkeypatch.setattr(SecuritySettings, "get_auth_generation", lambda: generation["value"])

    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"] = "auth-generation-test-secret-with-sufficient-length"
    jwt_manager = JWTManager(app)
    auth_manager._configure_auth_generation_verification(jwt_manager)

    @app.get("/protected")
    @jwt_required()
    def protected():  # noqa: ANN202
        return jsonify(ok=True)

    @app.get("/refresh")
    @jwt_required()
    def refresh():  # noqa: ANN202
        token = create_access_token(
            identity="alice",
            additional_claims={auth_manager.AUTH_GENERATION_CLAIM: generation["value"]},
        )
        issued_on_refresh.append(token)
        return jsonify(access_token=token)

    return app, generation, issued_on_refresh


def _authorization(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_auth_manager_initialize_registers_generation_callbacks(monkeypatch: pytest.MonkeyPatch) -> None:
    registered: dict[str, object] = {}

    class RecordingJWTManager:
        def __init__(self, app: Flask) -> None:
            registered["app"] = app

        @staticmethod
        def token_verification_loader(callback):  # noqa: ANN001, ANN205
            registered["verify"] = callback

        @staticmethod
        def token_verification_failed_loader(callback):  # noqa: ANN001, ANN205
            registered["rejected"] = callback

    app = Flask(__name__)
    monkeypatch.delenv("TARANIS_NG_AUTHENTICATOR", raising=False)
    monkeypatch.setattr(auth_manager, "JWTManager", RecordingJWTManager)

    previous_authenticator = auth_manager.current_authenticator
    try:
        auth_manager.initialize(app)
    finally:
        auth_manager.current_authenticator = previous_authenticator

    assert registered == {
        "app": app,
        "verify": auth_manager._auth_generation_is_current,
        "rejected": auth_manager._auth_generation_rejected,
    }


@pytest.mark.parametrize("claim", [None, 1, "2", 2.0, True, False, 0, -1])
def test_missing_old_or_malformed_generation_is_rejected(
    generation_app: tuple[Flask, dict[str, int], list[str]],
    claim: object,
) -> None:
    app, _generation, _issued = generation_app
    with app.app_context():
        claims = {} if claim is None else {auth_manager.AUTH_GENERATION_CLAIM: claim}
        token = create_access_token(identity="alice", additional_claims=claims)

    response = app.test_client().get("/protected", headers=_authorization(token))

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.get_json() == {"error": "Authentication token is no longer valid"}


def test_current_generation_is_accepted(generation_app: tuple[Flask, dict[str, int], list[str]]) -> None:
    app, generation, _issued = generation_app
    with app.app_context():
        token = create_access_token(
            identity="alice",
            additional_claims={auth_manager.AUTH_GENERATION_CLAIM: generation["value"]},
        )

    response = app.test_client().get("/protected", headers=_authorization(token))

    assert response.status_code == HTTPStatus.OK
    assert response.get_json() == {"ok": True}


def test_refresh_cannot_resurrect_a_stale_token(
    generation_app: tuple[Flask, dict[str, int], list[str]],
) -> None:
    app, generation, issued = generation_app
    with app.app_context():
        generation_two_token = create_access_token(
            identity="alice",
            additional_claims={auth_manager.AUTH_GENERATION_CLAIM: 2},
        )

    generation["value"] = 3
    stale_response = app.test_client().get("/refresh", headers=_authorization(generation_two_token))

    assert stale_response.status_code == HTTPStatus.UNAUTHORIZED
    assert issued == []

    with app.app_context():
        current_token = create_access_token(
            identity="alice",
            additional_claims={auth_manager.AUTH_GENERATION_CLAIM: 3},
        )
    current_response = app.test_client().get("/refresh", headers=_authorization(current_token))

    assert current_response.status_code == HTTPStatus.OK
    assert len(issued) == 1
    with app.app_context():
        assert decode_token(current_response.get_json()["access_token"])[auth_manager.AUTH_GENERATION_CLAIM] == 3


@pytest.mark.parametrize("payload", [{"sub": "alice"}, {"sub": "alice", "auth_generation": 1}])
def test_manual_session_jwt_consumers_also_reject_missing_or_stale_generation(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict,
) -> None:
    monkeypatch.setattr(auth_manager.jwt, "decode", lambda *_args, **_kwargs: payload)
    monkeypatch.setattr(SecuritySettings, "get_auth_generation", lambda: 2)
    monkeypatch.setattr(auth_manager, "_find_active_user", lambda _username: pytest.fail("stale token reached user lookup"))
    monkeypatch.setattr(auth_manager.log_manager, "store_auth_error_activity", lambda *_args: None)

    assert auth_manager.decode_user_from_jwt("encoded-token") is None
