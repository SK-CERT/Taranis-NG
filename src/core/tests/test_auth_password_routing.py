"""Vue 2 login compatibility and explicit LDAP routing contracts."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from http import HTTPStatus
from types import SimpleNamespace

import pytest
from api import auth
from auth import base_authenticator
from auth.base_authenticator import BaseAuthenticator
from flask import Flask
from managers import auth_manager

app = Flask(__name__)


@pytest.fixture(autouse=True)
def restore_current_authenticator():  # noqa: ANN201
    previous = auth_manager.current_authenticator
    yield
    auth_manager.current_authenticator = previous


def test_vue2_shaped_login_post_keeps_access_token_response(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def authenticate(credentials: dict) -> tuple[dict, HTTPStatus]:
        captured.update(credentials)
        return {"access_token": "local-access-token"}, HTTPStatus.OK

    auth_manager.current_authenticator = None
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
        lambda _provider: pytest.fail("A Vue 2 local password must never be sent to a database LDAP provider"),
    )

    with app.test_request_context("/api/v1/auth/login", method="POST", json={"username": "alice", "password": "secret"}):
        response = auth_manager.authenticate_with_provider(None, {"username": "alice", "password": "secret"})

    assert response == ({"access_token": "local-token"}, HTTPStatus.OK)
    assert provider_queries == [("local",)]


def test_explicit_legacy_environment_ldap_selects_one_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    selected = SimpleNamespace(
        initialize=lambda _app: None,
        get_required_credentials=lambda: ["username", "password"],
        authenticate=lambda _credentials: ({"access_token": "legacy-ldap-token"}, HTTPStatus.OK),
    )
    creations = 0

    def make_adapter() -> object:
        nonlocal creations
        creations += 1
        return selected

    monkeypatch.setenv("TARANIS_NG_AUTHENTICATOR", "ldap")
    monkeypatch.setattr(auth_manager, "JWTManager", lambda _app: None)
    monkeypatch.setattr(auth_manager, "_configure_auth_generation_verification", lambda _manager: None)
    monkeypatch.setattr(auth_manager, "LegacyEnvironmentLDAPAuthenticator", make_adapter)
    monkeypatch.setattr(
        auth_manager.AuthProvider,
        "get_enabled_by_kind",
        lambda _kinds: pytest.fail("Environment LDAP must not query database LDAP providers"),
    )

    auth_manager.initialize(app)
    response = auth_manager.authenticate({"username": "alice", "password": "directory-password"})

    assert creations == 1
    assert auth_manager.current_authenticator is selected
    assert response == ({"access_token": "legacy-ldap-token"}, HTTPStatus.OK)


def test_refresh_keeps_access_token_response_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    user = SimpleNamespace(username="alice")
    auth_manager.current_authenticator = None
    monkeypatch.setattr(auth_manager, "get_user_from_jwt", lambda: user)
    monkeypatch.setattr(
        auth_manager,
        "refresh",
        lambda refreshed_user: ({"access_token": f"refreshed-token-for-{refreshed_user.username}"}, HTTPStatus.OK),
    )

    response = auth.Refresh.get.__wrapped__(auth.Refresh())

    assert response == ({"access_token": "refreshed-token-for-alice"}, HTTPStatus.OK)


def test_issued_access_token_keeps_vue2_user_claims(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_legacy_environment_ldap_translates_old_settings_once(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    ca_path = tmp_path / "ldap-ca.pem"
    ca_path.write_text("test-ca-certificate")
    providers: list[object] = []

    class LDAPBackend:
        def __init__(self, provider: object) -> None:
            providers.append(provider)

        @staticmethod
        def verify(credentials: dict) -> object:
            assert credentials == {"username": "alice", "password": "directory-password"}
            return SimpleNamespace(username="alice")

    monkeypatch.setenv("LDAP_SERVER", "ldap.internal.example")
    monkeypatch.setenv("LDAP_BASE_DN", "ou=people,dc=example,dc=org")
    monkeypatch.setenv("LDAP_CA_CERT_PATH", str(ca_path))
    monkeypatch.setattr(auth_manager, "LDAPAuthenticator", LDAPBackend)
    monkeypatch.setattr(
        auth_manager.BaseAuthenticator,
        "generate_jwt",
        lambda username: ({"access_token": f"token-for-{username}"}, HTTPStatus.OK),
    )

    adapter = auth_manager.LegacyEnvironmentLDAPAuthenticator()
    response = adapter.authenticate({"username": "alice", "password": "directory-password"})

    assert response == ({"access_token": "token-for-alice"}, HTTPStatus.OK)
    assert adapter.get_required_credentials() == ["username", "password"]
    assert len(providers) == 1
    provider = providers[0]
    assert provider.config == {
        "server_url": "ldap.internal.example",
        "use_tls": True,
        "ca_cert": "test-ca-certificate",
        "user_dn_template": "uid={username},ou=people,dc=example,dc=org",
        "username_attr": "uid",
        "name_attr": "cn",
    }
