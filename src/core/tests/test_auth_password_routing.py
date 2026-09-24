"""Provider-less password login compatibility and local-only routing contracts."""

from __future__ import annotations

from http import HTTPStatus
from types import SimpleNamespace

import pytest
from api import auth
from auth import base_authenticator
from auth.base_authenticator import BaseAuthenticator
from flask import Flask
from managers import auth_manager

app = Flask(__name__)


def test_login_post_without_provider_keeps_access_token_response(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def authenticate(credentials: dict) -> tuple[dict, HTTPStatus]:
        captured.update(credentials)
        return {"access_token": "local-access-token"}, HTTPStatus.OK

    monkeypatch.setattr(auth_manager, "authenticate", authenticate)

    with app.test_request_context(
        "/api/v1/auth/login",
        method="POST",
        json={"username": "alice", "password": "correct horse"},
    ):
        response = auth.Login().post()

    assert response == ({"access_token": "local-access-token"}, HTTPStatus.OK)
    assert captured == {"username": "alice", "password": "correct horse", "provider_id": None}


def test_no_provider_id_tries_local_only_and_never_database_ldap(monkeypatch: pytest.MonkeyPatch) -> None:
    local_provider = SimpleNamespace(kind="local")
    provider_queries: list[tuple[str, ...]] = []

    def get_enabled_by_kind(kinds: tuple[str, ...]) -> list:
        provider_queries.append(kinds)
        return [local_provider] if kinds == ("local",) else []

    monkeypatch.setattr(auth_manager.AuthProvider, "get_enabled_by_kind", get_enabled_by_kind)
    monkeypatch.setattr(auth_manager.PasswordAuthenticator, "verify", lambda _credentials: SimpleNamespace(username="alice"))
    monkeypatch.setattr(auth_manager, "_finalize_login", lambda _provider, _user: ({"access_token": "local-token"}, HTTPStatus.OK))
    monkeypatch.setattr(
        auth_manager,
        "LDAPAuthenticator",
        lambda _provider: pytest.fail("A password sent without provider_id must never reach a database LDAP provider"),
    )

    with app.test_request_context("/api/v1/auth/login", method="POST", json={"username": "alice", "password": "secret"}):
        response = auth_manager.authenticate_with_provider(None, {"username": "alice", "password": "secret"})

    assert response == ({"access_token": "local-token"}, HTTPStatus.OK)
    assert provider_queries == [("local",)]


def test_refresh_keeps_access_token_response_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    user = SimpleNamespace(username="alice")
    monkeypatch.setattr(auth_manager, "get_user_from_jwt", lambda: user)
    monkeypatch.setattr(
        auth_manager,
        "refresh",
        lambda refreshed_user: ({"access_token": f"refreshed-token-for-{refreshed_user.username}"}, HTTPStatus.OK),
    )

    response = auth.Refresh.get.__wrapped__(auth.Refresh())

    assert response == ({"access_token": "refreshed-token-for-alice"}, HTTPStatus.OK)


def test_issued_access_token_keeps_user_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    user = SimpleNamespace(
        username="alice",
        id=7,
        name="Alice Example",
        status="active",
        get_current_organization_name=lambda: "Example Org",
        get_permissions=lambda: ["ANALYZE_ACCESS"],
        touch_login=lambda: None,
    )
    captured: dict = {}

    def create_access_token(*, identity: str, additional_claims: dict) -> str:
        captured.update(identity=identity, additional_claims=additional_claims)
        return "encoded-jwt"

    monkeypatch.setattr(base_authenticator, "create_access_token", create_access_token)
    monkeypatch.setattr(base_authenticator.log_manager, "store_user_activity", lambda *_args: None)
    monkeypatch.setattr(base_authenticator.SecuritySettings, "get_auth_generation", lambda: 3)

    response = BaseAuthenticator.generate_jwt(user)

    assert response == ({"access_token": "encoded-jwt"}, HTTPStatus.OK)
    assert captured == {
        "identity": "alice",
        "additional_claims": {
            "auth_generation": 3,
            "user_claims": {
                "id": 7,
                "name": "Alice Example",
                "organization_name": "Example Org",
                "permissions": ["ANALYZE_ACCESS"],
            },
        },
    }
