"""Federation scopes: an IdP may only assert scoped identifiers within its own ``<shibmd:Scope>``."""

from __future__ import annotations

import time
from types import SimpleNamespace

import pytest
import regex
from auth import saml_federation
from auth.base_authenticator import ExternalIdentity
from auth.saml_authenticator import SamlAuthenticator, ScopeMismatchError
from auth.saml_federation import Scope, in_scopes
from lxml.etree import _Element, fromstring

MD = "urn:oasis:names:tc:SAML:2.0:metadata"
DS = "http://www.w3.org/2000/09/xmldsig#"
SHIBMD = "urn:mace:shibboleth:metadata:1.0"
REDIRECT = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
IDP = "https://idp.example.org/idp"


def _metadata(entity_scopes: str = "", idp_scopes: str = "") -> _Element:
    entity_extensions = f"<md:Extensions>{entity_scopes}</md:Extensions>" if entity_scopes else ""
    idp_extensions = f"<md:Extensions>{idp_scopes}</md:Extensions>" if idp_scopes else ""
    return fromstring(
        (
            f'<md:EntitiesDescriptor xmlns:md="{MD}" xmlns:ds="{DS}" xmlns:shibmd="{SHIBMD}">'
            f'<md:EntityDescriptor entityID="{IDP}">{entity_extensions}'
            '<md:IDPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">'
            f"{idp_extensions}"
            '<md:KeyDescriptor use="signing"><ds:KeyInfo><ds:X509Data>'
            "<ds:X509Certificate>MIIB</ds:X509Certificate></ds:X509Data></ds:KeyInfo></md:KeyDescriptor>"
            f'<md:SingleSignOnService Binding="{REDIRECT}" Location="https://idp.example.org/sso"/>'
            "</md:IDPSSODescriptor></md:EntityDescriptor></md:EntitiesDescriptor>"
        ).encode(),
    )


def _scopes(**kwargs: str) -> tuple[Scope, ...]:
    return saml_federation._index_idps(_metadata(**kwargs))[IDP].scopes


def test_scopes_come_from_the_entity_and_its_idp_descriptor() -> None:
    scopes = _scopes(
        entity_scopes='<shibmd:Scope regexp="false">example.org</shibmd:Scope>',
        idp_scopes="<shibmd:Scope> Faculty.Example.NET </shibmd:Scope>",
    )

    assert [scope.value for scope in scopes] == ["example.org", "Faculty.Example.NET"]
    assert all(scope.pattern is None for scope in scopes)


def test_regexp_scopes_are_compiled_and_invalid_ones_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    warnings: list[str] = []
    monkeypatch.setattr(saml_federation.log_manager.logger, "warning", warnings.append)

    scopes = _scopes(
        idp_scopes=(
            r'<shibmd:Scope regexp="true">^([a-z0-9-]+\.)?example\.org$</shibmd:Scope>'
            '<shibmd:Scope regexp="true">([unclosed</shibmd:Scope>'
            '<shibmd:Scope regexp="true">   </shibmd:Scope>'
        ),
    )

    assert len(scopes) == 1
    assert scopes[0].pattern is not None
    assert len(warnings) == 1
    assert "([unclosed" in warnings[0]


def test_an_idp_without_scopes_has_none() -> None:
    assert _scopes() == ()


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("alice@example.org", True),
        ("alice@EXAMPLE.org", True),
        ("alice@mail.example.org", True),
        ("alice@notexample.org", False),
        ("alice@example.org.evil.test", False),
        ("alice@other.test", False),
        ("alice@", False),
        ("alice", False),
        ("a@b@example.org", True),
    ],
)
def test_a_literal_scope_covers_its_domain_and_subdomains(value: str, expected: bool) -> None:
    assert in_scopes(value, (Scope("Example.org"),)) is expected


def test_a_regexp_scope_must_match_the_whole_domain() -> None:
    scopes = (Scope("x", regex.compile(r"(dept\.)?example\.org", regex.IGNORECASE)),)

    assert in_scopes("alice@DEPT.example.org", scopes)
    assert in_scopes("alice@example.org", scopes)
    assert not in_scopes("alice@example.org.evil.test", scopes)
    assert not in_scopes("alice@xdept.example.org", scopes)


@pytest.mark.parametrize(
    "value",
    [
        "alice@example.org.",
        "alice@exa mple.org",
        "alice@example.org/x",
        "alice@-example.org",
        "alice@" + "a" * 250 + ".example.org",
        "alice@exa\u200bmple.org",
    ],
)
def test_a_domain_that_is_not_a_host_name_is_in_no_scope(value: str) -> None:
    scopes = (Scope("example.org"), Scope("x", regex.compile(r".*", regex.IGNORECASE)))

    assert not in_scopes(value, scopes)


def test_a_regexp_scope_that_backtracks_gives_up_instead_of_pinning_a_worker() -> None:
    scopes = (Scope("x", regex.compile(r"^(([a-z0-9-]+)+\.)+example\.org$", regex.IGNORECASE)),)

    start = time.perf_counter()
    assert not in_scopes("alice@" + "a" * 60, scopes)
    assert time.perf_counter() - start < 2
    assert in_scopes("alice@dept.example.org", scopes)


def test_metadata_regexp_scopes_get_the_time_budget() -> None:
    (scope,) = _scopes(idp_scopes='<shibmd:Scope regexp="true">^(([a-z0-9-]+)+\\.)+example\\.org$</shibmd:Scope>')

    start = time.perf_counter()
    assert not scope.matches("a" * 60)
    assert time.perf_counter() - start < 2


def test_nothing_is_in_scope_of_an_idp_without_scopes() -> None:
    assert not in_scopes("alice@example.org", ())


def _authenticator() -> SamlAuthenticator:
    provider = SimpleNamespace(id=3, name="eduID", config={"discovery_url": "https://ds.example.org"})
    return SamlAuthenticator(provider)  # ty: ignore[invalid-argument-type]


@pytest.fixture
def auth_errors(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    errors: list[str] = []
    monkeypatch.setattr("auth.saml_authenticator.log_manager.store_auth_error_activity", lambda message, *_args: errors.append(message))
    return errors


def test_a_scoped_username_within_the_scopes_is_marked_scoped(auth_errors: list[str]) -> None:
    identity = ExternalIdentity("alice@example.org", "abc@example.org", "Alice", "alice@mail.example.org", IDP)

    checked = _authenticator()._within_scopes(identity, (Scope("example.org"),))

    assert checked.scoped is True
    assert checked.email == "alice@mail.example.org"
    assert checked.issuer == IDP
    assert auth_errors == []


@pytest.mark.parametrize(
    ("username", "external_id", "label"),
    [
        ("alice@victim.test", "opaque-id", "username"),
        ("alice@example.org", "abc@victim.test", "external id"),
    ],
)
def test_a_scoped_value_outside_the_scopes_is_refused(username: str, external_id: str, label: str, auth_errors: list[str]) -> None:
    identity = ExternalIdentity(username, external_id, None, None, IDP)

    with pytest.raises(ScopeMismatchError):
        _authenticator()._within_scopes(identity, (Scope("example.org"),))

    assert len(auth_errors) == 1
    assert f"asserted the {label}" in auth_errors[0]
    assert IDP in auth_errors[0]
    assert "['example.org']" in auth_errors[0]


def test_an_idp_without_scopes_cannot_assert_a_scoped_username(auth_errors: list[str]) -> None:
    with pytest.raises(ScopeMismatchError):
        _authenticator()._within_scopes(ExternalIdentity("alice@example.org", None, None, None, IDP), ())

    assert len(auth_errors) == 1


def test_an_unscoped_username_passes_but_is_not_marked_scoped(auth_errors: list[str]) -> None:
    identity = ExternalIdentity("alice", "opaque-persistent-id", None, None, IDP)

    checked = _authenticator()._within_scopes(identity, (Scope("example.org"),))

    assert checked.scoped is False
    assert auth_errors == []


def test_a_mail_outside_the_scopes_is_dropped_not_refused(auth_errors: list[str]) -> None:
    """Otherwise any IdP could pass the provider's e-mail domain filter with a borrowed domain."""
    identity = ExternalIdentity("alice@example.org", None, "Alice", "boss@victim.test", IDP)

    checked = _authenticator()._within_scopes(identity, (Scope("example.org"),))

    assert checked.email is None
    assert checked.scoped is True
    assert auth_errors == []
