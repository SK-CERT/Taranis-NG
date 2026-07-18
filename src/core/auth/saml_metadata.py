"""Extract the SAML provider settings from an identity provider's metadata.

An admin registering an IdP has its metadata document (or a URL to it); the
three values our provider needs - entityID, the HTTP-Redirect SSO endpoint and
the signing certificate(s) - all live inside it. Copying them out by hand is
error-prone, so this module does it.
"""

from __future__ import annotations

from auth.saml_authenticator import PEM_FOOTER, PEM_HEADER
from defusedxml import ElementTree

MD = "{urn:oasis:names:tc:SAML:2.0:metadata}"
DS = "{http://www.w3.org/2000/09/xmldsig#}"
HTTP_REDIRECT_BINDING = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
# PEM bodies are conventionally wrapped at 64 characters
PEM_LINE_LENGTH = 64


def _to_pem(base64_blob: str) -> str:
    """Wrap the bare base64 of an <X509Certificate> element into a PEM block."""
    body = "".join(base64_blob.split())
    lines = "\n".join(body[index : index + PEM_LINE_LENGTH] for index in range(0, len(body), PEM_LINE_LENGTH))
    return f"{PEM_HEADER}\n{lines}\n{PEM_FOOTER}\n"


def parse_idp_metadata(xml: str) -> dict:
    """Read the IdP settings out of a SAML metadata document.

    Only the *signing* certificates are taken: a ``KeyDescriptor`` counts when it
    is marked ``use="signing"`` or carries no ``use`` at all (which means it
    serves both purposes). An ``use="encryption"`` key is deliberately ignored -
    it cannot verify a signature, and we never encrypt anything.

    Args:
        xml (str): The metadata document.

    Returns:
        dict: idp_entity_id, idp_sso_url and idp_certificate (a PEM bundle, so
              several signing certificates survive an IdP key rollover).

    Raises:
        ValueError: When the document is not parsable, describes several
            identity providers, describes no IdP, or lacks an SSO endpoint or a
            signing certificate. A single-entity aggregate (a signed
            ``EntitiesDescriptor`` wrapping one IdP, as MDQ services return) is
            accepted and unwrapped.
    """
    try:
        root = ElementTree.fromstring(xml.strip())
    except Exception as ex:
        msg = f"The metadata could not be parsed as XML: {ex}"
        raise ValueError(msg) from ex

    if root.tag == MD + "EntitiesDescriptor":
        # A metadata query service (MDQ endpoints such as those run by eduGAIN,
        # InCommon or DFN-AAI) wraps even a single entity in a signed
        # EntitiesDescriptor. Unwrap it when exactly one identity provider is
        # inside; a genuine multi-IdP aggregate is the federation case and
        # belongs to a federation login method instead.
        idp_entities = [entity for entity in root.findall(MD + "EntityDescriptor") if entity.find(MD + "IDPSSODescriptor") is not None]
        if len(idp_entities) > 1:
            msg = (
                "This metadata describes several identity providers (a federation aggregate). "
                "Provide the metadata of a single identity provider, or configure a federation login method instead."
            )
            raise ValueError(msg)
        if not idp_entities:
            msg = "This metadata aggregate contains no identity provider (no IDPSSODescriptor element)"
            raise ValueError(msg)
        entity = idp_entities[0]
    elif root.tag == MD + "EntityDescriptor":
        entity = root
    else:
        msg = "This does not look like SAML metadata (no EntityDescriptor element)"
        raise ValueError(msg)

    entity_id = entity.get("entityID")
    if not entity_id:
        msg = "The metadata has no entityID"
        raise ValueError(msg)

    idp = entity.find(MD + "IDPSSODescriptor")
    if idp is None:
        msg = "The metadata describes no identity provider (no IDPSSODescriptor element)"
        raise ValueError(msg)

    sso_url = None
    for service in idp.findall(MD + "SingleSignOnService"):
        if service.get("Binding") == HTTP_REDIRECT_BINDING:
            sso_url = service.get("Location")
            break
    if not sso_url:
        msg = "The identity provider publishes no HTTP-Redirect single sign-on endpoint, which is the binding this service uses"
        raise ValueError(msg)

    certificates = []
    for key_descriptor in idp.findall(MD + "KeyDescriptor"):
        # no "use" means the key serves both signing and encryption
        if key_descriptor.get("use") not in (None, "signing"):
            continue
        certificates.extend(
            _to_pem(certificate.text)
            for certificate in key_descriptor.iter(DS + "X509Certificate")
            if certificate.text and certificate.text.strip()
        )
    if not certificates:
        msg = "The metadata contains no signing certificate"
        raise ValueError(msg)

    return {
        "idp_entity_id": entity_id,
        "idp_sso_url": sso_url,
        "idp_certificate": "".join(certificates),
    }
