"""The SP metadata we publish must conform to the SAML 2.0 metadata schema.

An identity provider's registration form validates the metadata against the XSD
and refuses it otherwise (a missing AttributeConsumingService/ServiceName is
exactly what regressed once). These tests validate the generated document against
the official OASIS/W3C schema chain, vendored under ``resources/saml_schemas``.
"""

from __future__ import annotations

import types
from pathlib import Path

import pytest
from auth.saml_authenticator import SamlAuthenticator, generate_sp_keypair
from lxml import etree

SCHEMA_DIR = Path(__file__).parent / "resources" / "saml_schemas"

MD = "urn:oasis:names:tc:SAML:2.0:metadata"
MDUI = "urn:oasis:names:tc:SAML:metadata:ui"

ACS_URL = "https://taranis.example.org/api/v1/auth/saml/1/acs"
DISCO_URL = "https://taranis.example.org/api/v1/auth/saml/1/disco"

BASE = {"sp_entity_id": "https://taranis.example.org/api/v1/auth/saml/1/metadata"}
ATTRS = {
    "external_id_attr": "urn:oid:1.3.6.1.4.1.5923.1.1.1.10",
    "username_attr": "urn:oid:0.9.2342.19200300.100.1.1",
    "name_attr": "urn:oid:2.16.840.1.113730.3.1.241",
    "email_attr": "urn:oid:0.9.2342.19200300.100.1.3",
}
ENRICH = {
    "sp_display_name": "Taranis NG Threat Intelligence",
    "sp_description": "OSINT and threat intelligence platform.",
    "sp_information_url": "https://taranis.example.org/",
    "sp_organization_name": "Example CERT",
    "sp_organization_url": "https://example.org/",
    "sp_contact_email": "cert@example.org",
    "sp_contact_name": "Example CERT Team",
}
FEDERATION = {
    "discovery_url": "https://ds.example.org/wayf",
    "federation_metadata_url": "https://metadata.example.org/entities/federation",
    "federation_metadata_cert": "unused-when-only-building-metadata",
}


@pytest.fixture(scope="module")
def metadata_schema() -> etree.XMLSchema:
    """The compiled SAML 2.0 metadata schema (with its imported schema chain)."""
    return etree.XMLSchema(etree.parse(str(SCHEMA_DIR / "saml-schema-metadata-2.0.xsd")))


def _metadata(config: dict, disco_url: str | None = None) -> str:
    """Build SP metadata for a provider with the given config."""
    provider = types.SimpleNamespace(id=1, name="Taranis NG", config=config)
    provider.get_secret_plaintext = lambda: None
    return SamlAuthenticator(provider).get_metadata_xml(ACS_URL, disco_url)


# name -> (config, disco_url); each must validate against the schema
CASES = {
    "minimal_single_idp": (BASE, None),
    "single_idp_with_attributes": ({**BASE, **ATTRS}, None),
    "single_idp_enriched": ({**BASE, **ATTRS, **ENRICH}, None),
    "single_idp_with_keypair": ({**BASE, **ATTRS, "sp_certificate": generate_sp_keypair("sp")["certificate"]}, None),
    "federation_minimal": ({**BASE, **FEDERATION}, DISCO_URL),
    "federation_enriched": ({**BASE, **FEDERATION, **ATTRS, **ENRICH}, DISCO_URL),
}


@pytest.mark.parametrize("case", CASES.keys())
def test_generated_metadata_conforms_to_saml_schema(metadata_schema: etree.XMLSchema, case: str) -> None:
    """Every metadata shape we can emit validates against the SAML metadata XSD."""
    config, disco_url = CASES[case]
    document = etree.fromstring(_metadata(config, disco_url).encode())
    is_valid = metadata_schema.validate(document)
    errors = "\n".join(f"  line {e.line}: {e.message}" for e in metadata_schema.error_log)
    assert is_valid, f"metadata for '{case}' is not schema-valid:\n{errors}"


def test_attribute_consuming_service_has_service_name_before_requested_attributes() -> None:
    """Regression: RequestedAttribute must be preceded by ServiceName (the schema requires it)."""
    document = etree.fromstring(_metadata({**BASE, **ATTRS, **ENRICH}).encode())
    acs = document.find(f".//{{{MD}}}AttributeConsumingService")
    assert acs is not None, "no AttributeConsumingService emitted for a provider with attributes"
    children = [etree.QName(child).localname for child in acs]
    assert children[0] == "ServiceName", children
    assert children.index("ServiceName") < children.index("RequestedAttribute"), children


def test_enriched_metadata_carries_uiinfo_organization_and_contact() -> None:
    """The fields a federation registration requires are present when configured."""
    document = etree.fromstring(_metadata({**BASE, **ATTRS, **ENRICH}, DISCO_URL).encode())
    ui_info = document.find(f".//{{{MDUI}}}UIInfo")
    assert ui_info is not None
    for tag in ("DisplayName", "Description", "InformationURL"):
        langs = sorted(e.get("{http://www.w3.org/XML/1998/namespace}lang") for e in ui_info.findall(f"{{{MDUI}}}{tag}"))
        assert langs == ["cs", "en"], f"{tag} languages: {langs}"
    assert document.find(f"{{{MD}}}Organization") is not None
    contact = document.find(f"{{{MD}}}ContactPerson")
    assert contact is not None
    assert contact.get("contactType") == "technical"
    # Federations (eduGAIN, InCommon, DFN-AAI, ...) require a SurName on the
    # technical contact. It is derived from sp_contact_name's last token when
    # sp_contact_surname is unset.
    assert contact.find(f"{{{MD}}}SurName") is not None, "technical contact has no SurName"
    assert contact.find(f"{{{MD}}}SurName").text == "Team"  # last token of "Example CERT Team"


def test_minimal_metadata_omits_optional_blocks() -> None:
    """Nothing optional leaks in when unconfigured (backward compatible metadata)."""
    document = etree.fromstring(_metadata(BASE).encode())
    assert document.find(f".//{{{MDUI}}}UIInfo") is None
    assert document.find(f"{{{MD}}}Organization") is None
    assert document.find(f"{{{MD}}}ContactPerson") is None
    assert document.find(f".//{{{MD}}}AttributeConsumingService") is None
