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
from auth.ldap_authenticator import LDAPAuthenticator
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


_ABSENT = object()


def _ldap_config(use_tls: object) -> dict:
    config = {"server_url": "ldap.example.org", "bind_dn": "cn=reader,dc=example,dc=org", "search_base": "dc=example,dc=org"}
    if use_tls is not _ABSENT:
        config["use_tls"] = use_tls
    return config


@pytest.mark.parametrize("use_tls", [_ABSENT, None, True, False, "false", 0])
def test_ldap_use_tls_reads_as_the_login_reads_it(use_tls: object) -> None:
    # The check and the login must agree on whether the bind password goes in clear text.
    config = _ldap_config(use_tls)
    login_uses_tls = LDAPAuthenticator(types.SimpleNamespace(config=config))._build_server().ssl

    assert auth_provider.secret_destination("ldap", config)["use_tls"] is login_uses_tls


@pytest.mark.parametrize(
    ("stored_tls", "submitted_tls", "changed"),
    [
        (True, None, ["use_tls"]),
        (_ABSENT, None, ["use_tls"]),
        (_ABSENT, _ABSENT, []),
        (True, False, ["use_tls"]),
        (False, False, []),
        (_ABSENT, True, []),
    ],
)
def test_ldap_use_tls_changes(stored_tls: object, submitted_tls: object, changed: list) -> None:
    stored = auth_provider.secret_destination("ldap", _ldap_config(stored_tls))
    submitted = auth_provider.secret_destination("ldap", _ldap_config(submitted_tls))

    assert stored_secrets.changed_destination(submitted, stored, auth_provider.SECRET_DESTINATION_KEYS) == changed


def _update_ldap(monkeypatch: pytest.MonkeyPatch, stored_config: dict, submitted_config: dict) -> types.SimpleNamespace:
    old = types.SimpleNamespace(kind="ldap", secret="encrypted", config=dict(stored_config))
    new = types.SimpleNamespace(
        kind="ldap",
        slug="ldap",
        name="LDAP",
        secret=None,
        config=submitted_config,
        enabled=True,
        organization=None,
        default_roles=[],
        provisioning_mode="manual",
        allowed_domains="",
        require_mfa=False,
    )
    monkeypatch.setattr(auth_provider, "NewAuthProviderSchema", lambda: types.SimpleNamespace(load=lambda _data: new))
    monkeypatch.setattr(auth_provider.db, "session", types.SimpleNamespace(get=lambda _model, _provider_id: old, commit=lambda: None))
    # The destination check on its own; _validate refuses a null use_tls before it (tested below).
    monkeypatch.setattr(AuthProvider, "_validate", classmethod(lambda _cls, *_args, **_kwargs: None))
    AuthProvider.update(3, {}, "Admin")
    return old


def test_saving_ldap_with_use_tls_null_and_no_secret_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(StoredSecretError, match="Enter the secret again: use_tls changed"):
        _update_ldap(monkeypatch, _ldap_config(use_tls=True), _ldap_config(None))


@pytest.mark.parametrize(("stored_tls", "submitted_tls"), [(_ABSENT, _ABSENT), (False, False), (True, True)])
def test_saving_ldap_with_the_same_tls_keeps_the_secret(monkeypatch: pytest.MonkeyPatch, stored_tls: object, submitted_tls: object) -> None:
    old = _update_ldap(monkeypatch, _ldap_config(stored_tls), _ldap_config(submitted_tls))

    assert old.secret == "encrypted"


def test_saving_ldap_with_tls_switched_off_and_no_secret_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(StoredSecretError, match="use_tls changed"):
        _update_ldap(monkeypatch, _ldap_config(use_tls=True), _ldap_config(use_tls=False))


@pytest.mark.parametrize("use_tls", [None, "true", "false", 1, 0])
def test_ldap_use_tls_must_be_a_boolean(use_tls: object) -> None:
    with pytest.raises(ValueError, match="use_tls must be true or false"):
        AuthProvider._validate_ldap_config(_ldap_config(use_tls))


@pytest.mark.parametrize("use_tls", [_ABSENT, True, False])
def test_ldap_use_tls_may_be_left_out_or_a_boolean(use_tls: object) -> None:
    AuthProvider._validate_ldap_config(_ldap_config(use_tls))


def test_saving_ldap_with_use_tls_null_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    # A session that builds a query without an application, so that ``query`` can be replaced.
    monkeypatch.setattr(auth_provider.db, "session", types.SimpleNamespace)
    no_rows = types.SimpleNamespace(filter_by=lambda **_kwargs: types.SimpleNamespace(first=lambda: None))
    monkeypatch.setattr(AuthProvider, "query", no_rows)
    provider = types.SimpleNamespace(kind="ldap", slug="ldap", config=_ldap_config(None))

    with pytest.raises(ValueError, match="use_tls must be true or false"):
        AuthProvider._validate(provider, 3)


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


@pytest.mark.usefixtures("smtp_channel")
@pytest.mark.parametrize("flag", ["false", "true", 1])
def test_only_a_real_removal_saves_the_channel_for_another_server_without_the_password(monkeypatch: pytest.MonkeyPatch, flag: object) -> None:
    saved: list = []
    monkeypatch.setattr(notifications_api.NotificationChannel, "save", classmethod(lambda _cls, *args, **_kwargs: saved.append(args)))
    config = {"host": "attacker.example", "port": 587, "security": "starttls", "username": "taranis", "from_address": "taranis@example.org"}
    with APP.test_request_context("/", method="PUT", json={"enabled": True, "clear_secret": flag, "config": config}):
        body, status = notifications_api.NotificationChannelResource.put.__wrapped__(notifications_api.NotificationChannelResource(), "email")

    assert status == HTTPStatus.BAD_REQUEST
    assert "host changed" in body["error"]
    assert saved == []


def test_saving_a_provider_with_a_new_server_and_no_secret_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    old = types.SimpleNamespace(kind="ldap", secret="encrypted", config={"server_url": "ldaps://ldap.example.org"})
    new = types.SimpleNamespace(kind="ldap", slug="ldap", secret=None, config={"server_url": "ldaps://attacker.example"})
    monkeypatch.setattr(auth_provider, "NewAuthProviderSchema", lambda: types.SimpleNamespace(load=lambda _data: new))
    monkeypatch.setattr(auth_provider.db, "session", types.SimpleNamespace(get=lambda _model, _provider_id: old))
    monkeypatch.setattr(AuthProvider, "_validate", classmethod(lambda _cls, *_args, **_kwargs: None))

    with pytest.raises(StoredSecretError, match="server_url changed"):
        AuthProvider.update(3, {}, "Admin")

    assert old.config == {"server_url": "ldaps://ldap.example.org"}
