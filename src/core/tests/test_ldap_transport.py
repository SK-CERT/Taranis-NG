"""LDAP transport: the URL scheme and the "Use TLS" switch must never leave a bind unprotected or unchecked."""

from __future__ import annotations

import ssl
from types import SimpleNamespace
from typing import ClassVar

import pytest
from auth import ldap_authenticator
from auth.ldap_authenticator import LDAPAuthenticator

CA_PEM = "-----BEGIN CERTIFICATE-----\nMIIB\n-----END CERTIFICATE-----\n"


def _authenticator(server_url: str, *, use_tls: bool, **config: str) -> LDAPAuthenticator:
    provider = SimpleNamespace(
        name="Directory",
        config={"server_url": server_url, "use_tls": use_tls, "user_dn_template": "uid={username},dc=example,dc=org", **config},
        get_secret_plaintext=lambda: "service-secret",
    )
    return LDAPAuthenticator(provider)  # ty: ignore[invalid-argument-type]


@pytest.mark.parametrize("use_tls", [True, False])
def test_ldaps_url_is_always_tls_with_a_checked_certificate(use_tls: bool) -> None:
    server = _authenticator("ldaps://ldap.example.org", use_tls=use_tls)._build_server()

    assert server.ssl is True
    assert server.port == 636
    assert server.tls is not None
    assert server.tls.validate == ssl.CERT_REQUIRED


def test_ldaps_url_uses_the_configured_ca() -> None:
    server = _authenticator("LDAPS://ldap.example.org", use_tls=False, ca_cert=CA_PEM)._build_server()

    assert server.tls is not None
    assert server.tls.ca_certs_data == CA_PEM


def test_bare_host_with_tls_uses_ldaps() -> None:
    server = _authenticator("ldap.example.org", use_tls=True)._build_server()

    assert server.ssl is True
    assert server.port == 636
    assert server.tls is not None
    assert server.tls.validate == ssl.CERT_REQUIRED


def test_ldap_url_with_tls_is_upgraded_by_starttls_on_the_plain_port() -> None:
    authenticator = _authenticator("ldap://ldap.example.org", use_tls=True)
    server = authenticator._build_server()

    assert authenticator._transport() == "starttls"
    assert server.ssl is False
    assert server.port == 389
    assert server.tls is not None
    assert server.tls.validate == ssl.CERT_REQUIRED


@pytest.mark.parametrize("server_url", ["ldap://ldap.example.org", "ldap.example.org"])
def test_tls_switched_off_without_ldaps_stays_plain(server_url: str) -> None:
    authenticator = _authenticator(server_url, use_tls=False)

    assert authenticator._transport() == "plain"
    assert authenticator._build_server().ssl is False


class _FakeConnection:
    """Records the order of open / start_tls / bind calls."""

    calls: list[str]
    starttls_result = True

    def __init__(self, _server: object, *, user: str, password: str, read_only: bool) -> None:
        assert read_only is True
        self.user = user
        self.password = password
        self.entries: list = []
        self.result: dict = {}
        self.last_error = None

    def open(self) -> None:
        _FakeConnection.calls.append("open")

    def start_tls(self) -> bool:
        _FakeConnection.calls.append("start_tls")
        return _FakeConnection.starttls_result

    def bind(self) -> bool:
        _FakeConnection.calls.append(f"bind:{self.user}")
        return True

    def search(self, *_args: object, **_kwargs: object) -> bool:
        return False

    def unbind(self) -> None:
        _FakeConnection.calls.append("unbind")


@pytest.fixture
def fake_connection(monkeypatch: pytest.MonkeyPatch) -> type[_FakeConnection]:
    _FakeConnection.calls = []
    _FakeConnection.starttls_result = True
    monkeypatch.setattr(ldap_authenticator, "Connection", _FakeConnection)
    return _FakeConnection


def test_starttls_happens_before_the_bind_sends_the_password(fake_connection: type[_FakeConnection]) -> None:
    identity = _authenticator("ldap://ldap.example.org", use_tls=True).verify({"username": "alice", "password": "pw"})

    assert identity is not None
    assert fake_connection.calls[:3] == ["open", "start_tls", "bind:uid=alice,dc=example,dc=org"]


class _Entry:
    entry_dn = "uid=alice,dc=example,dc=org"
    entry_attributes_as_dict: ClassVar[dict] = {}


class _FakeSearchConnection(_FakeConnection):
    def search(self, *_args: object, **_kwargs: object) -> bool:
        self.entries = [_Entry()]
        return True


def test_search_bind_upgrades_both_the_service_and_the_user_connection(
    fake_connection: type[_FakeConnection],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ldap_authenticator, "Connection", _FakeSearchConnection)
    authenticator = _authenticator(
        "ldap://ldap.example.org",
        use_tls=True,
        bind_dn="cn=svc,dc=example,dc=org",
        search_base="dc=example,dc=org",
    )
    del authenticator.config["user_dn_template"]

    identity = authenticator.verify({"username": "alice", "password": "pw"})

    assert identity is not None
    assert fake_connection.calls == [
        "open",
        "start_tls",
        "bind:cn=svc,dc=example,dc=org",
        "unbind",
        "open",
        "start_tls",
        "bind:uid=alice,dc=example,dc=org",
        "unbind",
    ]


def test_refused_starttls_never_binds(fake_connection: type[_FakeConnection], monkeypatch: pytest.MonkeyPatch) -> None:
    fake_connection.starttls_result = False
    errors: list[str] = []
    monkeypatch.setattr(ldap_authenticator.log_manager, "store_auth_error_activity", lambda message, *_args: errors.append(message))

    identity = _authenticator("ldap://ldap.example.org", use_tls=True).verify({"username": "alice", "password": "pw"})

    assert identity is None
    assert fake_connection.calls == ["open", "start_tls"]
    assert errors == ["LDAP authentication error for provider 'Directory'"]


@pytest.mark.parametrize("server_url", ["ldaps://ldap.example.org", "ldap://ldap.example.org"])
def test_no_starttls_on_ldaps_or_plain(fake_connection: type[_FakeConnection], server_url: str) -> None:
    use_tls = server_url.startswith("ldaps://")
    identity = _authenticator(server_url, use_tls=use_tls).verify({"username": "alice", "password": "pw"})

    assert identity is not None
    assert "start_tls" not in fake_connection.calls
    assert "open" not in fake_connection.calls
