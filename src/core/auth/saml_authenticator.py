"""SAML 2.0 authenticator driven by a database-configured provider.

Provider ``config`` keys:
    idp_sso_url (str): The IdP single-sign-on endpoint (HTTP-Redirect binding).
    idp_entity_id (str): The IdP entityID (issuer of the SAML response).
    idp_certificate (str): Certificate(s) the IdP signs responses with. A PEM
        bundle (several are kept so a key rollover does not break logins) or a
        bare base64 blob as it appears in the IdP metadata.
    sp_entity_id (str): Our entityID / audience (what the IdP is configured
        to issue assertions for).
    acs_url_override (str): Assertion Consumer Service URL when the derived
        one is wrong behind a proxy.
    username_attr (str): Assertion attribute holding the username; empty uses
        the NameID.
    external_id_attr (str): Assertion attribute holding a *stable* subject
        identifier, used to recognize a returning user. Empty uses the NameID,
        which only works when the IdP issues a persistent one - with a
        transient NameID the identity would change on every login.
    name_attr (str): Assertion attribute holding the display name.
    email_attr (str): Assertion attribute holding the e-mail address.
    nameid_format (str): NameID format advertised in our metadata.

Optional human-readable SP metadata (a federation such as eduGAIN, InCommon or
DFN-AAI requires it to register, and an IdP's schema validator rejects the
metadata without the ServiceName that ``sp_display_name`` provides). Each is
emitted only when set:
    sp_display_name (str): Service display name (UIInfo DisplayName, and the
        AttributeConsumingService ServiceName). Falls back to the provider name.
    sp_description (str): UIInfo Description.
    sp_information_url (str): UIInfo InformationURL.
    sp_organization_name (str): md:Organization name/display name.
    sp_organization_url (str): md:Organization URL.
    sp_contact_email (str): Technical contact e-mail (md:ContactPerson).
    sp_contact_name (str): Technical contact name (md:GivenName).

Attributes are looked up by their SAML ``Name`` (an OID when the IdP uses the
URI name-format), never by ``FriendlyName``.

The flow uses the HTTP-Redirect binding for the AuthnRequest and the
HTTP-POST binding for the response. CSRF/replay protection: the RelayState is
a short-lived signed JWT carrying the AuthnRequest ID, which must match the
InResponseTo of the (signature-verified) response.
"""

from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from xml.sax.saxutils import escape, quoteattr

from auth.base_authenticator import BaseAuthenticator, ExternalIdentity
from auth.saml_xml import decrypt_assertion, extract_signed_assertion
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from managers import log_manager
from minisaml.request import get_request_redirect_url
from minisaml.response import TimeDriftLimits, validate_response

if TYPE_CHECKING:
    from cryptography.x509 import Certificate
    from model.auth_provider import AuthProvider

# Tolerated clock skew between Taranis NG and the IdP when checking the
# assertion's NotBefore/NotOnOrAfter conditions.
CLOCK_SKEW = timedelta(minutes=2)

PEM_HEADER = "-----BEGIN CERTIFICATE-----"
PEM_FOOTER = "-----END CERTIFICATE-----"

# Persistent by default: a transient NameID cannot identify a returning user.
DEFAULT_NAMEID_FORMAT = "urn:oasis:names:tc:SAML:2.0:nameid-format:persistent"
# Attribute names are OIDs when the IdP uses the URI name-format, which is what
# federated deployments do; advertise the requested attributes accordingly.
ATTRIBUTE_NAME_FORMAT = "urn:oasis:names:tc:SAML:2.0:attrname-format:uri"

# SAML Identity Provider Discovery protocol (federation mode): the profile URI is
# used both as the DiscoveryResponse binding and to name the endpoint. The return
# ID parameter is the query key the discovery service echoes the chosen IdP
# entityID back to us in.
IDP_DISCOVERY_PROTOCOL = "urn:oasis:names:tc:SAML:profiles:SSO:idp-discovery-protocol"
DISCOVERY_RETURN_ID_PARAM = "idp_entity_id"

# Human-readable SP metadata (UIInfo, Organization, ServiceName). Federations
# such as eduGAIN, InCommon or DFN-AAI require these and want every language they
# list an entity in; the same admin-supplied text is emitted for each language here.
MDUI_NAMESPACE = "urn:oasis:names:tc:SAML:metadata:ui"
METADATA_LANGS = ("en", "cs")

SP_KEY_SIZE = 2048
SP_CERTIFICATE_DAYS = 3650
# What we tell an IdP it may encrypt with. RSA-1_5 is deliberately absent.
SUPPORTED_ENCRYPTION_METHODS = (
    "http://www.w3.org/2009/xmlenc11#aes256-gcm",
    "http://www.w3.org/2009/xmlenc11#aes128-gcm",
    "http://www.w3.org/2001/04/xmlenc#aes256-cbc",
    "http://www.w3.org/2001/04/xmlenc#aes128-cbc",
    "http://www.w3.org/2001/04/xmlenc#rsa-oaep-mgf1p",
    "http://www.w3.org/2009/xmlenc11#rsa-oaep",
)


def generate_sp_keypair(entity_id: str) -> dict:
    """Generate the service provider keypair an identity provider encrypts to.

    The certificate is self-signed: an IdP only uses it to encrypt the assertion
    to our public key, so no chain of trust is involved - the federation pins the
    certificate we register with it.

    Args:
        entity_id (str): Our entityID, used as the certificate's common name.

    Returns:
        dict: private_key and certificate, both PEM.
    """
    key = rsa.generate_private_key(public_exponent=65537, key_size=SP_KEY_SIZE)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, entity_id or "taranis-ng")])
    now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=SP_CERTIFICATE_DAYS))
        .sign(key, hashes.SHA256())
    )
    return {
        "private_key": key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode(),
        "certificate": certificate.public_bytes(serialization.Encoding.PEM).decode(),
    }


def validate_sp_keypair(private_key_pem: str, certificate_pem: str) -> None:
    """Check that an SP keypair parses and that the two halves belong together.

    Args:
        private_key_pem (str): The private key.
        certificate_pem (str): The certificate.

    Raises:
        ValueError: When either half is unparsable or they do not match.
    """
    try:
        key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
    except Exception as ex:
        msg = f"The service provider private key could not be parsed: {ex}"
        raise ValueError(msg) from ex
    try:
        certificate = x509.load_pem_x509_certificate(certificate_pem.encode())
    except Exception as ex:
        msg = f"The service provider certificate could not be parsed: {ex}"
        raise ValueError(msg) from ex

    if certificate.public_key().public_numbers() != key.public_key().public_numbers():
        msg = "The service provider certificate does not match the private key"
        raise ValueError(msg)


def load_idp_certificates(value: str) -> list[Certificate]:
    """Load the IdP signing certificate(s) from whatever form they were pasted in.

    Accepts a PEM bundle (one or more certificates - an IdP publishes two during
    a key rollover) as well as the bare base64 blob that appears inside
    ``<ds:X509Certificate>`` in the metadata, which is what an admin copying from
    the IdP actually has in hand.

    Args:
        value (str): The configured certificate material.

    Returns:
        list[Certificate]: Every certificate found, in the order given.

    Raises:
        ValueError: When no certificate can be parsed.
    """
    text = (value or "").strip()
    if not text:
        msg = "No IdP signing certificate configured"
        raise ValueError(msg)

    if PEM_HEADER not in text:
        # bare base64 (possibly wrapped across lines): add the armor ourselves
        body = "".join(text.split())
        text = f"{PEM_HEADER}\n{body}\n{PEM_FOOTER}\n"

    certificates = []
    for block in text.split(PEM_HEADER)[1:]:
        pem = f"{PEM_HEADER}{block.split(PEM_FOOTER)[0]}{PEM_FOOTER}\n"
        try:
            certificates.append(x509.load_pem_x509_certificate(pem.encode()))
        except Exception as ex:
            msg = f"The IdP signing certificate could not be parsed: {ex}"
            raise ValueError(msg) from ex

    if not certificates:
        msg = "The IdP signing certificate could not be parsed"
        raise ValueError(msg)
    return certificates


class SamlAuthenticator(BaseAuthenticator):
    """SP-side SAML 2.0 web browser SSO against a configured identity provider."""

    def __init__(self, provider: AuthProvider) -> None:
        """Initialize the authenticator from a provider row.

        Args:
            provider (AuthProvider): The saml-kind provider configuration.
        """
        self.provider = provider
        self.config = provider.config or {}

    def sp_entity_id(self) -> str:
        """Return our entityID (the audience the IdP issues assertions for)."""
        return self.config.get("sp_entity_id") or "taranis-ng"

    def nameid_format(self) -> str:
        """Return the NameID format we advertise in our metadata."""
        return self.config.get("nameid_format") or DEFAULT_NAMEID_FORMAT

    def is_federation(self) -> bool:
        """Tell whether this provider federates through a discovery service.

        A configured ``discovery_url`` switches the provider from targeting one
        identity provider to sending the user to a WAYF and resolving whichever
        IdP they pick out of the federation metadata.
        """
        return bool(self.config.get("discovery_url"))

    def sp_certificate(self) -> str:
        """Return our (public) certificate, the one the IdP encrypts assertions to."""
        return (self.config.get("sp_certificate") or "").strip()

    def load_sp_private_key(self) -> object | None:
        """Load our private key, or None when no keypair is configured.

        The key lives in the provider's Fernet-encrypted ``secret`` column, which
        no other SAML setting uses.
        """
        pem = self.provider.get_secret_plaintext()
        if not pem:
            return None
        return serialization.load_pem_private_key(pem.encode(), password=None)

    @staticmethod
    def _localized(prefix: str, tag: str, value: str, indent: str) -> str:
        """Emit an XML element once per advertised language, or '' when unset.

        A federation lists an entity in several languages (typically both the
        local language and English); the same admin-supplied text is repeated
        for each.
        """
        if not value:
            return ""
        text = escape(value)
        return "".join(f'\n{indent}<{prefix}:{tag} xml:lang="{lang}">{text}</{prefix}:{tag}>' for lang in METADATA_LANGS)

    def _metadata_organization(self, service_name: str) -> str:
        """Build the ``<md:Organization>`` block, or '' when none is configured.

        A federation typically requires it. All three child elements are
        mandatory, so a missing display name or URL falls back to the service name
        and the SP entityID.
        """
        name = (self.config.get("sp_organization_name") or "").strip()
        url = (self.config.get("sp_organization_url") or "").strip()
        if not name and not url:
            return ""
        name = name or service_name
        url = url or (self.config.get("sp_information_url") or "").strip() or self.sp_entity_id()
        return (
            "\n  <md:Organization>"
            f"{self._localized('md', 'OrganizationName', name, '    ')}"
            f"{self._localized('md', 'OrganizationDisplayName', name, '    ')}"
            f"{self._localized('md', 'OrganizationURL', url, '    ')}"
            "\n  </md:Organization>"
        )

    def _metadata_contact(self) -> str:
        """Build the technical ``<md:ContactPerson>`` block, or '' with no e-mail configured.

        A federation typically requires a ``SurName`` on the technical contact.
        It is taken from ``sp_contact_surname`` when set; otherwise it is derived
        from the last token of ``sp_contact_name`` ("Jane Doe" -> "Doe"), so the
        warning clears even when only the name field is filled. The whole block
        is omitted when no e-mail is configured, matching the schema's optionality
        (SurName and GivenName are both optional in SAML itself).
        """
        email = (self.config.get("sp_contact_email") or "").strip()
        if not email:
            return ""
        name = (self.config.get("sp_contact_name") or "").strip()
        given = f"\n    <md:GivenName>{escape(name)}</md:GivenName>" if name else ""
        surname = (self.config.get("sp_contact_surname") or "").strip()
        if not surname and name:
            # A federation typically requires a SurName; fall back to the last
            # token of the name.
            surname = name.rsplit(maxsplit=1)[-1]
        surname_el = f"\n    <md:SurName>{escape(surname)}</md:SurName>" if surname else ""
        address = email if email.startswith("mailto:") else f"mailto:{email}"
        return (
            '\n  <md:ContactPerson contactType="technical">'
            f"{given}"
            f"{surname_el}"
            f"\n    <md:EmailAddress>{escape(address)}</md:EmailAddress>"
            "\n  </md:ContactPerson>"
        )

    def get_metadata_xml(self, acs_url: str, disco_url: str | None = None) -> str:
        """Build the SP metadata XML to register at the identity provider.

        The descriptor declares what this SP can actually do: it never signs
        AuthnRequests (minisaml cannot) and it requires signed assertions - the
        signature is what we verify, so an assertion without one is unusable even
        when it decrypts.

        When a keypair is configured, the certificate is published as an
        encryption KeyDescriptor: that is what an identity provider encrypts the
        assertion to, and what a federation's registration form asks for. Without
        a keypair no key is advertised, and a well-behaved IdP then sends the
        assertion in clear.

        Args:
            acs_url (str): Our Assertion Consumer Service URL.
            disco_url (str): Our DiscoveryResponse URL. In federation mode it is
                advertised as an ``<idpdisc:DiscoveryResponse>`` so the discovery
                service accepts it as the ``return`` target; ignored otherwise.

        Returns:
            str: The SP metadata document.
        """
        requested = ""
        for key in ("external_id_attr", "username_attr", "name_attr", "email_attr"):
            name = (self.config.get(key) or "").strip()
            if name:
                requested += (
                    f"\n      <md:RequestedAttribute Name={quoteattr(name)} "
                    f'NameFormat="{ATTRIBUTE_NAME_FORMAT}" isRequired="{"true" if key == "external_id_attr" else "false"}"/>'
                )

        # A human-readable name for this service, used as the AttributeConsumingService
        # ServiceName and as the UIInfo/Organization display fallback.
        service_name = (self.config.get("sp_display_name") or "").strip() or self.provider.name or "Taranis NG"

        attribute_service = ""
        if requested:
            # The schema requires ServiceName before RequestedAttribute; omitting it
            # makes an IdP's schema validator reject the metadata.
            names = self._localized("md", "ServiceName", service_name, "      ")
            attribute_service = f'\n    <md:AttributeConsumingService index="0">{names}{requested}\n    </md:AttributeConsumingService>'

        key_descriptor = ""
        certificate = self.sp_certificate()
        if certificate:
            body = "".join(line for line in certificate.splitlines() if "CERTIFICATE" not in line).strip()
            methods = "".join(f'\n        <md:EncryptionMethod Algorithm="{method}"/>' for method in SUPPORTED_ENCRYPTION_METHODS)
            key_descriptor = (
                '\n    <md:KeyDescriptor use="encryption">'
                '\n      <ds:KeyInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">'
                f"\n        <ds:X509Data><ds:X509Certificate>{body}</ds:X509Certificate></ds:X509Data>"
                "\n      </ds:KeyInfo>"
                f"{methods}"
                "\n    </md:KeyDescriptor>"
            )

        # SPSSODescriptor/Extensions carries the UIInfo a federation asks for and,
        # in federation mode, the DiscoveryResponse endpoint. The schema allows a
        # single Extensions element (before KeyDescriptor), so they share one.
        ui_parts = (
            self._localized("mdui", "DisplayName", (self.config.get("sp_display_name") or "").strip(), "        ")
            + self._localized("mdui", "Description", (self.config.get("sp_description") or "").strip(), "        ")
            + self._localized("mdui", "InformationURL", (self.config.get("sp_information_url") or "").strip(), "        ")
        )
        ui_info = f'\n      <mdui:UIInfo xmlns:mdui="{MDUI_NAMESPACE}">{ui_parts}\n      </mdui:UIInfo>' if ui_parts else ""

        discovery_response = ""
        if self.is_federation() and disco_url:
            discovery_response = (
                f'\n      <idpdisc:DiscoveryResponse xmlns:idpdisc="{IDP_DISCOVERY_PROTOCOL}" '
                f'Binding="{IDP_DISCOVERY_PROTOCOL}" Location={quoteattr(disco_url)} index="0" isDefault="true"/>'
            )

        extensions = f"\n    <md:Extensions>{ui_info}{discovery_response}\n    </md:Extensions>" if (ui_info or discovery_response) else ""

        # Organization and ContactPerson sit at the EntityDescriptor level, after
        # the role descriptor; federations (eduGAIN, InCommon, DFN-AAI, ...) require
        # both.
        organization = self._metadata_organization(service_name)
        contact = self._metadata_contact()

        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata" '
            f"entityID={quoteattr(self.sp_entity_id())}>\n"
            '  <md:SPSSODescriptor AuthnRequestsSigned="false" WantAssertionsSigned="true" '
            'protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">'
            f"{extensions}{key_descriptor}\n"
            f"    <md:NameIDFormat>{self.nameid_format()}</md:NameIDFormat>\n"
            '    <md:AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" '
            f'Location={quoteattr(acs_url)} index="0" isDefault="true"/>'
            f"{attribute_service}\n"
            "  </md:SPSSODescriptor>"
            f"{organization}{contact}\n"
            "</md:EntityDescriptor>\n"
        )

    def get_authn_request_url(self, sso_url: str, acs_url: str, relay_state: str, request_id: str) -> str:
        """Build the SSO URL carrying the AuthnRequest (HTTP-Redirect binding).

        Args:
            sso_url (str): The identity provider single sign-on endpoint. In
                federation mode this is the endpoint resolved for the IdP the user
                chose at the discovery service.
            acs_url (str): Our Assertion Consumer Service URL.
            relay_state (str): Signed state token round-tripped by the IdP.
            request_id (str): The AuthnRequest ID (verified against InResponseTo).

        Returns:
            str: The URL to redirect the browser to.
        """
        return get_request_redirect_url(
            saml_endpoint=sso_url,
            expected_audience=self.sp_entity_id(),
            acs_url=acs_url,
            request_id=request_id,
            relay_state=relay_state,
        )

    def get_login_redirect_url(self, acs_url: str, relay_state: str, request_id: str) -> str:
        """Build the AuthnRequest redirect to the single configured identity provider."""
        return self.get_authn_request_url(self.config.get("idp_sso_url"), acs_url, relay_state, request_id)

    def get_discovery_redirect_url(self, return_url: str) -> str:
        """Build the discovery-service (WAYF) URL that lets the user pick their IdP.

        Follows the SAML Identity Provider Discovery Service protocol: it carries
        our entityID, a ``return`` URL the service sends the browser back to, and
        the name of the query parameter it must report the chosen IdP entityID in.
        Any federation-specific extras the admin configured - for federations that
        support it, a ``filter`` parameter that restricts which IdPs are listed -
        are appended verbatim as an already-URL-ready query fragment, so nothing
        here is specific to one federation.

        Args:
            return_url (str): Absolute URL of our DiscoveryResponse endpoint,
                already carrying our signed state token.

        Returns:
            str: The discovery-service URL to redirect the browser to.
        """
        parsed = urlparse(self.config["discovery_url"])
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query["entityID"] = self.sp_entity_id()
        query["return"] = return_url
        query["returnIDParam"] = DISCOVERY_RETURN_ID_PARAM
        encoded = urlencode(query)
        extra = (self.config.get("discovery_params") or "").strip().lstrip("?&")
        if extra:
            encoded = f"{encoded}&{extra}"
        return urlunparse(parsed._replace(query=encoded))

    def _idp_trust_material(self, chosen_entity_id: str | None) -> tuple[str, str]:
        """Return the (certificate, expected issuer) the IdP response must verify against.

        In single-IdP mode these are the pinned config values. In federation mode
        both come from the verified federation metadata for the IdP the user chose
        at the discovery service, so a chosen entity that is not in the federation
        raises rather than being trusted.

        Args:
            chosen_entity_id (str): The IdP entityID from the signed RelayState
                (federation mode only).

        Returns:
            tuple[str, str]: The IdP signing certificate(s) (PEM) and the issuer.

        Raises:
            ValueError: When the chosen IdP is not in the federation metadata.
        """
        if not self.is_federation():
            return self.config.get("idp_certificate", ""), self.config.get("idp_entity_id")

        from auth import saml_federation  # noqa: PLC0415 - avoid an import cycle at module load

        resolved = saml_federation.resolve_idp(self.provider, chosen_entity_id or "")
        if resolved is None:
            msg = f"the response is from '{chosen_entity_id}', not an identity provider in the federation"
            raise ValueError(msg)
        return resolved.certificates, resolved.entity_id

    def handle_response(
        self,
        saml_response: str,
        request_id: str | None,
        chosen_entity_id: str | None = None,
    ) -> ExternalIdentity | None:
        """Validate a posted SAMLResponse and resolve the external identity.

        The response signature is verified against the IdP's certificate; issuer,
        audience, validity window and InResponseTo are checked before any
        attribute is trusted. In federation mode the certificate and expected
        issuer are not fixed config - they are resolved from the verified
        federation metadata for the IdP the user chose at the discovery service,
        which is why an assertion from an entity not in the federation is refused
        here rather than trusted.

        Args:
            saml_response (str): The base64 SAMLResponse form field.
            request_id (str): The AuthnRequest ID from the signed RelayState.
            chosen_entity_id (str): In federation mode, the IdP entityID carried
                in the signed RelayState (set at the DiscoveryResponse step).

        Returns:
            ExternalIdentity: The authenticated identity, or None on failure.
        """
        try:
            idp_certificate, idp_issuer = self._idp_trust_material(chosen_entity_id)

            # every certificate is tried, so an IdP key rollover (metadata
            # carries the old and the new one) keeps working
            certificates = load_idp_certificates(idp_certificate)

            # minisaml accepts a document whose signed root is the Assertion, and both
            # of the awkward real-world shapes reduce to exactly that: an assertion
            # encrypted to our public key (a federation requirement), and a response
            # signed alongside its assertion (which minisignxml refuses - it verifies a
            # single signature). Everything else is passed through as it arrived.
            raw_response = base64.b64decode(saml_response)
            assertion = decrypt_assertion(raw_response, self.load_sp_private_key()) or extract_signed_assertion(raw_response)

            # validate_response base64-decodes its input; raw XML would be mangled
            data = base64.b64encode(assertion) if assertion is not None else saml_response

            response = validate_response(
                data=data,
                certificate=certificates,
                expected_audience=self.sp_entity_id(),
                idp_issuer=idp_issuer,
                allowed_time_drift=TimeDriftLimits(not_before_max_drift=CLOCK_SKEW, not_on_or_after_max_drift=CLOCK_SKEW),
            )
        except Exception as ex:
            log_manager.store_auth_error_activity(f"SAML response validation failed for provider '{self.provider.name}'", ex)
            return None

        if request_id and response.in_response_to and response.in_response_to != request_id:
            log_manager.store_auth_error_activity(f"SAML InResponseTo mismatch for provider '{self.provider.name}'")
            return None

        attributes = response.attrs
        username_attr = self.config.get("username_attr")
        username = attributes.get(username_attr) if username_attr else response.name_id
        if not username:
            source = username_attr or "NameID"
            log_manager.store_auth_error_activity(
                f"SAML provider '{self.provider.name}' returned no '{source}' value; attributes: {sorted(attributes.keys())}",
            )
            return None

        # The stable identifier recognizes a returning user. Falling back to the
        # NameID is only safe when the IdP issues a persistent one, so a
        # configured attribute that the assertion does not carry is an error
        # rather than a silent downgrade - the fallback would strand the user
        # with a new identity on every login.
        external_id_attr = self.config.get("external_id_attr")
        external_id = attributes.get(external_id_attr) if external_id_attr else response.name_id
        if external_id_attr and not external_id:
            log_manager.store_auth_error_activity(
                f"SAML provider '{self.provider.name}' returned no '{external_id_attr}' value to identify the user by; "
                f"attributes: {sorted(attributes.keys())}",
            )
            return None

        return ExternalIdentity(
            username=str(username),
            external_id=str(external_id) if external_id else None,
            name=attributes.get(self.config.get("name_attr") or "displayName"),
            email=attributes.get(self.config.get("email_attr") or "mail"),
        )
