"""A stored secret is reused only for the destination it was saved for.

"Saved empty keeps the stored secret" lets a dialog be saved without retyping a secret the GUI
never shows. Combined with a change of URL or host in the same request, it sent the stored
secret wherever the request said: node API keys, an AI provider's or data provider's key, a
remote peer's key, an OAuth client secret, an LDAP bind password, the SMTP password.
"""

from __future__ import annotations

import types
from http import HTTPStatus

import pytest
from api import config as config_api
from api import notifications as notifications_api
from flask import Flask
from managers import stored_secrets
from managers.stored_secrets import StoredSecretError
from model import auth_provider
from model.auth_provider import AuthProvider

APP = Flask(__name__)


@pytest.fixture
def stored_node(monkeypatch: pytest.MonkeyPatch) -> types.SimpleNamespace:
    node = types.SimpleNamespace(api_key="stored-key", api_url="https://collectors.example.org/")
    monkeypatch.setattr(stored_secrets.db, "session", types.SimpleNamespace(get=lambda _model, _record_id: node))
    return node


@pytest.mark.usefixtures("stored_node")
def test_a_key_saved_empty_is_kept_for_the_same_url() -> None:
    kept = stored_secrets.keep_stored_api_key({"api_url": " https://collectors.example.org ", "api_key": ""}, object, 7, ("api_url",))

    assert kept["api_key"] == "stored-key"


@pytest.mark.usefixtures("stored_node")
def test_a_key_saved_empty_does_not_follow_a_new_url() -> None:
    with pytest.raises(StoredSecretError, match="api_url changed"):
        stored_secrets.keep_stored_api_key({"api_url": "https://attacker.example", "api_key": ""}, object, 7, ("api_url",))


@pytest.mark.usefixtures("stored_node")
def test_a_new_key_may_go_to_a_new_url() -> None:
    data = {"api_url": "https://elsewhere.example", "api_key": "typed-again"}

    assert stored_secrets.keep_stored_api_key(data, object, 7, ("api_url",)) == data


# --- authentication providers ------------------------------------------------------------


def test_ldap_defaults_are_not_a_change() -> None:
    stored = auth_provider.secret_destination("ldap", {"server_url": "ldaps://ldap.example.org"})
    submitted = auth_provider.secret_destination("ldap", {"server_url": "ldaps://ldap.example.org", "use_tls": True, "ca_cert": ""})

    assert stored_secrets.changed_destination(submitted, stored, auth_provider.SECRET_DESTINATION_KEYS) == []


def test_a_new_ldap_server_or_plain_ldap_is_a_change() -> None:
    stored = auth_provider.secret_destination("ldap", {"server_url": "ldaps://ldap.example.org"})
    moved = auth_provider.secret_destination("ldap", {"server_url": "ldaps://attacker.example"})
    plain = auth_provider.secret_destination("ldap", {"server_url": "ldaps://ldap.example.org", "use_tls": False})

    assert stored_secrets.changed_destination(moved, stored, auth_provider.SECRET_DESTINATION_KEYS) == ["server_url"]
    assert stored_secrets.changed_destination(plain, stored, auth_provider.SECRET_DESTINATION_KEYS) == ["use_tls"]


@pytest.fixture
def stored_provider(monkeypatch: pytest.MonkeyPatch) -> types.SimpleNamespace:
    provider = types.SimpleNamespace(
        kind="oauth2",
        secret="encrypted",
        config={"authorize_url": "https://idp.example/auth", "token_url": "https://idp.example/token", "client_id": "taranis"},
        get_secret_plaintext=lambda: "client-s3cret",
    )
    monkeypatch.setattr(AuthProvider, "find", classmethod(lambda _cls, _provider_id: provider))
    return provider


def _verify(monkeypatch: pytest.MonkeyPatch, config: dict, kind: str = "oauth2") -> tuple[tuple, list]:
    tested: list = []
    monkeypatch.setattr(
        config_api.oauth2_authenticator,
        "verify_configuration",
        lambda *args: tested.append(args) or {"client_status": "accepted"},
    )
    with APP.test_request_context("/", method="POST", json={"id": 3, "kind": kind, "config": config, "secret": ""}):
        result = config_api.OAuthVerifyResource.post.__wrapped__(config_api.OAuthVerifyResource())
    return result, tested


def test_the_oauth_test_uses_the_stored_secret_for_its_own_endpoints(
    monkeypatch: pytest.MonkeyPatch,
    stored_provider: types.SimpleNamespace,
) -> None:
    (_body, status), tested = _verify(monkeypatch, dict(stored_provider.config))

    assert status == HTTPStatus.OK
    assert tested[0][2] == "client-s3cret"


@pytest.mark.usefixtures("stored_provider")
@pytest.mark.parametrize(
    ("kind", "config"),
    [
        ("oauth2", {"authorize_url": "https://idp.example/auth", "token_url": "https://attacker.example/t", "client_id": "taranis"}),
        ("oidc", {"issuer_url": "https://attacker.example", "client_id": "taranis"}),
    ],
)
def test_the_oauth_test_does_not_send_the_stored_secret_elsewhere(monkeypatch: pytest.MonkeyPatch, kind: str, config: dict) -> None:
    (body, status), tested = _verify(monkeypatch, config, kind)

    assert status == HTTPStatus.BAD_REQUEST
    assert "Enter the client secret again" in body["error"]
    assert tested == []


# --- notification e-mail channel ------------------------------------------------------------


@pytest.fixture
def smtp_channel(monkeypatch: pytest.MonkeyPatch) -> list:
    stored = types.SimpleNamespace(
        secret="encrypted",
        config={"host": "smtp.example.org", "port": 587, "security": "starttls", "verify_tls": True, "username": "taranis"},
        get_secret_plaintext=lambda: "smtp-pa55",
    )
    monkeypatch.setattr(notifications_api.NotificationChannel, "find", classmethod(lambda _cls, _kind: stored))
    monkeypatch.setattr(notifications_api, "get_user_from_jwt", lambda: types.SimpleNamespace(id=1, name="Admin"))
    monkeypatch.setattr(notifications_api.log_manager, "store_user_activity", lambda *_args: None)
    sent: list = []
    monkeypatch.setattr(notifications_api.notification_manager, "send_test", lambda *args: sent.append(args))
    return sent


def _test_mail(host: str) -> tuple:
    body = {
        "recipient": "admin@example.org",
        "secret": "",
        "config": {"host": host, "port": 587, "security": "starttls", "username": "taranis", "from_address": "taranis@example.org"},
    }
    with APP.test_request_context("/", method="POST", json=body):
        return notifications_api.NotificationChannelTestResource.post.__wrapped__(
            notifications_api.NotificationChannelTestResource(),
            "email",
        )


def test_a_test_mail_uses_the_stored_password_for_its_own_server(smtp_channel: list) -> None:
    assert _test_mail("smtp.example.org")[1] == HTTPStatus.OK
    assert smtp_channel[0][2] == "smtp-pa55"


def test_a_test_mail_does_not_log_in_to_another_server_with_the_stored_password(smtp_channel: list) -> None:
    body, status = _test_mail("attacker.example")

    assert status == HTTPStatus.BAD_REQUEST
    assert "host changed" in body["error"]
    assert smtp_channel == []


def test_saving_a_provider_with_a_new_server_and_no_secret_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    old = types.SimpleNamespace(kind="ldap", secret="encrypted", config={"server_url": "ldaps://ldap.example.org"})
    new = types.SimpleNamespace(kind="ldap", slug="ldap", secret=None, config={"server_url": "ldaps://attacker.example"})
    monkeypatch.setattr(auth_provider, "NewAuthProviderSchema", lambda: types.SimpleNamespace(load=lambda _data: new))
    monkeypatch.setattr(auth_provider.db, "session", types.SimpleNamespace(get=lambda _model, _provider_id: old))
    monkeypatch.setattr(AuthProvider, "_validate", classmethod(lambda _cls, *_args: None))

    with pytest.raises(StoredSecretError, match="server_url changed"):
        AuthProvider.update(3, {}, "Admin")

    assert old.config == {"server_url": "ldaps://ldap.example.org"}
