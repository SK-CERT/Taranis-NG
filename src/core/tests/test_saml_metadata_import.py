"""parse_idp_metadata extracts single-IdP settings, incl. from a wrapped aggregate.

A metadata query service (MDQ endpoints such as those run by eduGAIN, InCommon
or DFN-AAI) returns even one entity inside a signed ``EntitiesDescriptor``; the
importer must unwrap that but still refuse a genuine multi-IdP aggregate.
"""

from __future__ import annotations

import pytest
from auth.saml_metadata import parse_idp_metadata

MD = "urn:oasis:names:tc:SAML:2.0:metadata"
DS = "http://www.w3.org/2000/09/xmldsig#"
REDIRECT = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
POST = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
NS = f'xmlns:md="{MD}" xmlns:ds="{DS}"'
CERT_B64 = "MIIBdummyCertificateBase64Data=="


def _idp(entity_id: str, *, sso_binding: str = REDIRECT, sso: str | None = "https://idp.example.org/sso", cert: str | None = CERT_B64) -> str:
    parts = ""
    if cert is not None:
        parts += (
            '<md:KeyDescriptor use="signing"><ds:KeyInfo><ds:X509Data>'
            f"<ds:X509Certificate>{cert}</ds:X509Certificate>"
            "</ds:X509Data></ds:KeyInfo></md:KeyDescriptor>"
        )
    if sso is not None:
        parts += f'<md:SingleSignOnService Binding="{sso_binding}" Location="{sso}"/>'
    return (
        f'<md:EntityDescriptor entityID="{entity_id}">'
        f'<md:IDPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">'
        f"{parts}</md:IDPSSODescriptor></md:EntityDescriptor>"
    )


def _sp(entity_id: str) -> str:
    return (
        f'<md:EntityDescriptor entityID="{entity_id}">'
        f'<md:SPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">'
        f'<md:AssertionConsumerService Binding="{POST}" Location="https://sp.example.org/acs" index="0"/>'
        f"</md:SPSSODescriptor></md:EntityDescriptor>"
    )


def _single(entity_xml: str) -> str:
    return entity_xml.replace("<md:EntityDescriptor ", f"<md:EntityDescriptor {NS} ", 1)


def _aggregate(*entities: str) -> str:
    return f'<md:EntitiesDescriptor {NS} Name="urn:test:aggregate">{"".join(entities)}</md:EntitiesDescriptor>'


def test_single_entity_descriptor_is_parsed() -> None:
    result = parse_idp_metadata(_single(_idp("https://idp.example.org/idp")))
    assert result["idp_entity_id"] == "https://idp.example.org/idp"
    assert result["idp_sso_url"] == "https://idp.example.org/sso"
    assert "BEGIN CERTIFICATE" in result["idp_certificate"]
    assert CERT_B64 in result["idp_certificate"]


def test_single_entity_aggregate_is_unwrapped() -> None:
    # A metadata query service (MDQ endpoint) returns a signed
    # EntitiesDescriptor wrapping a single entity.
    result = parse_idp_metadata(_aggregate(_idp("https://idp.example.org/idp")))
    assert result["idp_entity_id"] == "https://idp.example.org/idp"


def test_aggregate_with_one_idp_and_an_sp_unwraps_to_the_idp() -> None:
    result = parse_idp_metadata(_aggregate(_sp("https://sp.example.org/sp"), _idp("https://idp.example.org/idp")))
    assert result["idp_entity_id"] == "https://idp.example.org/idp"


def test_multiple_identity_providers_are_rejected() -> None:
    xml = _aggregate(_idp("https://idp.example.org/a"), _idp("https://idp.example.org/b"))
    with pytest.raises(ValueError, match="several identity providers"):
        parse_idp_metadata(xml)


def test_aggregate_without_any_identity_provider_is_rejected() -> None:
    with pytest.raises(ValueError, match="no identity provider"):
        parse_idp_metadata(_aggregate(_sp("https://sp.example.org/sp")))


def test_identity_provider_without_redirect_sso_is_rejected() -> None:
    with pytest.raises(ValueError, match="HTTP-Redirect"):
        parse_idp_metadata(_single(_idp("https://idp.example.org/idp", sso_binding=POST)))


def test_identity_provider_without_signing_certificate_is_rejected() -> None:
    with pytest.raises(ValueError, match="signing certificate"):
        parse_idp_metadata(_single(_idp("https://idp.example.org/idp", cert=None)))


def test_non_metadata_document_is_rejected() -> None:
    with pytest.raises(ValueError, match="EntityDescriptor"):
        parse_idp_metadata('<foo xmlns="urn:x"/>')


def test_unparsable_input_is_rejected() -> None:
    with pytest.raises(ValueError, match="could not be parsed"):
        parse_idp_metadata("this is not < xml")
