"""Resolve identity providers out of a federation's signed metadata aggregate.

Federation mode connects the service provider to a whole federation
(eduGAIN, InCommon, DFN-AAI, ...) instead of a single identity provider:
the user picks their institution at a discovery service (WAYF), and this module
turns the chosen ``entityID`` into the HTTP-Redirect SSO URL and signing
certificate(s) needed to build the AuthnRequest and, later, verify the response.

The trust anchor is everything. The aggregate is fetched over the network, so
its enveloped XML signature is verified against a certificate the admin pinned
out of band (``federation_metadata_cert``), and an identity provider is only
ever resolved from the *verified* document. Skipping that check would let
anyone able to intercept the metadata fetch inject a rogue IdP and forge
logins.

The verifier is the same ``minisignxml`` the assertion path already relies on;
a real federation aggregate (5+ MB, hundreds of entities) verifies in a fraction
of a second, so the metadata is simply fetched, verified and cached in process
with a short TTL - no background refresh machinery. The TTL never outlives the
document's own ``validUntil``.

Only signatures matching ``minisignxml``'s strict profile are accepted:
exclusive C14N, enveloped-signature + exclusive-C14N transforms, and (by
default) SHA-256 throughout. Federations that sign with a different transform
set, an InclusiveNamespaces prefix list, or SHA-1 are out of scope for now.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import requests
from auth.saml_authenticator import PEM_FOOTER, PEM_HEADER, load_idp_certificates
from auth.url_guard import assert_public_url
from managers import log_manager
from minisignxml.config import VerifyConfig
from minisignxml.verify import extract_verified_element_and_certificate

if TYPE_CHECKING:
    from lxml.etree import _Element
    from model.auth_provider import AuthProvider

MD = "{urn:oasis:names:tc:SAML:2.0:metadata}"
DS = "{http://www.w3.org/2000/09/xmldsig#}"
HTTP_REDIRECT_BINDING = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
PEM_LINE_LENGTH = 64

HTTP_TIMEOUT = 30
# A safety valve against a hostile or runaway response, generous enough for the
# large interfederation aggregates (eduGAIN is tens of MB).
MAX_METADATA_BYTES = 64 * 1024 * 1024
DEFAULT_REFRESH_HOURS = 24
# Re-fetch a little before the document expires rather than exactly at validUntil.
VALID_UNTIL_SKEW = timedelta(minutes=5)

# SHA-256 only, which is what the federations we target actually sign with. This
# is deliberately the strict default; widen it here if a federation needs SHA-1.
VERIFY_CONFIG = VerifyConfig.default()


def is_federation_mode(config: dict | None) -> bool:
    """Tell whether a saml provider is configured to use a discovery service.

    A configured ``discovery_url`` is what puts a provider into federation mode:
    it no longer points at one identity provider but sends the user to a WAYF and
    resolves whichever IdP they pick out of the federation metadata.

    Args:
        config (dict): The provider ``config``.

    Returns:
        bool: True when the provider federates through a discovery service.
    """
    return bool((config or {}).get("discovery_url"))


@dataclass(frozen=True)
class ResolvedIdp:
    """An identity provider resolved out of verified federation metadata.

    Attributes:
        entity_id (str): The IdP entityID (also the issuer we must see in its
            response).
        sso_url (str): The IdP HTTP-Redirect single sign-on endpoint.
        certificates (str): The IdP signing certificate(s) as a PEM bundle,
            ready for :func:`auth.saml_authenticator.load_idp_certificates`.
    """

    entity_id: str
    sso_url: str
    certificates: str


@dataclass
class _Federation:
    """A parsed, verified federation indexed by entityID, with an expiry."""

    entities: dict[str, ResolvedIdp]
    expires_at: datetime


_cache: dict[int, _Federation] = {}
_lock = threading.Lock()


def _to_pem(base64_blob: str) -> str:
    """Wrap the bare base64 of an ``<X509Certificate>`` into a PEM block."""
    body = "".join(base64_blob.split())
    lines = "\n".join(body[index : index + PEM_LINE_LENGTH] for index in range(0, len(body), PEM_LINE_LENGTH))
    return f"{PEM_HEADER}\n{lines}\n{PEM_FOOTER}\n"


def _parse_valid_until(value: str | None) -> datetime | None:
    """Parse a metadata ``validUntil`` timestamp (xsd:dateTime, UTC) or None."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _fetch(url: str) -> bytes:
    """Download the metadata document, guarding against an oversized response.

    Args:
        url (str): The federation metadata URL.

    Returns:
        bytes: The raw document.

    Raises:
        ValueError: When the host is non-public or the response exceeds
            :data:`MAX_METADATA_BYTES`.
    """
    assert_public_url(url)
    with requests.get(url, timeout=HTTP_TIMEOUT, stream=True) as response:
        response.raise_for_status()
        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_content(chunk_size=65536):
            total += len(chunk)
            if total > MAX_METADATA_BYTES:
                msg = f"Federation metadata exceeds the {MAX_METADATA_BYTES} byte limit"
                raise ValueError(msg)
            chunks.append(chunk)
    return b"".join(chunks)


def _index_idps(verified: _Element) -> dict[str, ResolvedIdp]:
    """Build the entityID -> IdP index from a *verified* metadata element.

    Only identity providers usable by this service survive: an entity must carry
    an ``IDPSSODescriptor`` with an HTTP-Redirect SSO endpoint and at least one
    signing certificate. As with the single-IdP path, a KeyDescriptor counts as
    signing when it is marked ``use="signing"`` or carries no ``use`` at all.

    Args:
        verified (Element): The signature-verified metadata (an aggregate
            ``EntitiesDescriptor`` or a single ``EntityDescriptor``).

    Returns:
        dict: entityID -> ResolvedIdp for every usable identity provider.
    """
    entities: dict[str, ResolvedIdp] = {}
    for entity in verified.iter(f"{MD}EntityDescriptor"):
        entity_id = entity.get("entityID")
        idp = entity.find(f"{MD}IDPSSODescriptor")
        if not entity_id or idp is None:
            continue

        sso_url = None
        for service in idp.findall(f"{MD}SingleSignOnService"):
            if service.get("Binding") == HTTP_REDIRECT_BINDING:
                sso_url = service.get("Location")
                break
        if not sso_url:
            continue

        certificates = []
        for key_descriptor in idp.findall(f"{MD}KeyDescriptor"):
            if key_descriptor.get("use") not in (None, "signing"):
                continue
            certificates.extend(
                _to_pem(certificate.text)
                for certificate in key_descriptor.iter(f"{DS}X509Certificate")
                if certificate.text and certificate.text.strip()
            )
        if not certificates:
            continue

        entities[entity_id] = ResolvedIdp(entity_id=entity_id, sso_url=sso_url, certificates="".join(certificates))
    return entities


def _fetch_verify_index(metadata_url: str | None, cert_pem: str | None) -> tuple[dict[str, ResolvedIdp], datetime | None]:
    """Download, signature-verify and index a federation metadata document.

    The signature is verified against the pinned trust anchor before anything is
    read, and every IdP is taken only from the element the verifier returns.

    Args:
        metadata_url (str): The federation metadata URL.
        cert_pem (str): The trust anchor (a PEM bundle survives a signing-key
            rollover - old and new anchor pasted together).

    Returns:
        tuple: the entityID -> IdP index and the document's ``validUntil``.

    Raises:
        ValueError: When the URL or anchor is missing, or verification fails.
    """
    if not metadata_url or not cert_pem or not cert_pem.strip():
        msg = "Federation mode needs both a metadata URL and its signing certificate"
        raise ValueError(msg)
    trust_anchors = set(load_idp_certificates(cert_pem))
    raw = _fetch(metadata_url)
    verified, _ = extract_verified_element_and_certificate(xml=raw, certificates=trust_anchors, config=VERIFY_CONFIG)
    return _index_idps(verified), _parse_valid_until(verified.get("validUntil"))


def _load(provider: AuthProvider) -> _Federation:
    """Fetch, verify, index and cache a provider's federation metadata.

    A fresh cache entry is served as is. Otherwise the aggregate is downloaded and
    verified and the fresh index replaces the cached one. When a refresh fails but
    a stale index is still around it is served (with a warning) rather than locking
    every user out over a transient network or signing problem.

    Args:
        provider (AuthProvider): The saml-kind provider in federation mode.

    Returns:
        _Federation: The (possibly just refreshed) federation index.

    Raises:
        ValueError: When there is no usable metadata at all - misconfiguration,
            an unverifiable signature, or a fetch failure with nothing cached.
    """
    now = datetime.now(UTC)
    with _lock:
        cached = _cache.get(provider.id)
        if cached and cached.expires_at > now:
            return cached

    config = provider.config or {}
    try:
        entities, valid_until = _fetch_verify_index(config.get("federation_metadata_url"), config.get("federation_metadata_cert"))
    except Exception as ex:
        stale = _cache.get(provider.id)
        if stale:
            log_manager.logger.warning(
                f"Serving stale federation metadata for provider '{provider.name}' after refresh failed: {ex}",
            )
            return stale
        msg = f"Federation metadata for provider '{provider.name}' could not be loaded: {ex}"
        raise ValueError(msg) from ex

    refresh_hours = config.get("federation_metadata_refresh_hours") or DEFAULT_REFRESH_HOURS
    expires_at = now + timedelta(hours=float(refresh_hours))
    if valid_until:
        expires_at = min(expires_at, valid_until - VALID_UNTIL_SKEW)
        if valid_until <= now:
            log_manager.logger.warning(f"Federation metadata for provider '{provider.name}' is past its validUntil ({valid_until})")

    federation = _Federation(entities=entities, expires_at=expires_at)
    with _lock:
        _cache[provider.id] = federation
    return federation


def verify_metadata(metadata_url: str, cert_pem: str) -> dict:
    """Fetch and signature-verify federation metadata for the admin preview.

    Nothing is cached or stored: it reports how many usable identity providers the
    metadata yields and when it expires, so an admin can confirm the URL and trust
    anchor before saving the provider.

    Args:
        metadata_url (str): The federation metadata URL.
        cert_pem (str): The trust anchor PEM.

    Returns:
        dict: ``entity_count`` and ``valid_until`` (ISO 8601 or None).

    Raises:
        ValueError: When the URL or anchor is missing, or verification fails.
    """
    entities, valid_until = _fetch_verify_index(metadata_url, cert_pem)
    return {"entity_count": len(entities), "valid_until": valid_until.isoformat() if valid_until else None}


def resolve_idp(provider: AuthProvider, entity_id: str) -> ResolvedIdp | None:
    """Resolve one identity provider chosen at the discovery service.

    This is the trust gate: an ``entity_id`` that is not present in the verified
    federation metadata returns None, so an IdP the federation does not vouch for
    can never be used - neither to redirect the user to nor to trust a response
    from.

    Args:
        provider (AuthProvider): The saml-kind provider in federation mode.
        entity_id (str): The IdP entityID the user picked at the WAYF.

    Returns:
        ResolvedIdp: The resolved IdP, or None when it is not in the federation.
    """
    if not entity_id:
        return None
    return _load(provider).entities.get(entity_id)


def entity_count(provider: AuthProvider) -> int:
    """Return how many usable identity providers the federation currently offers.

    For the admin "verify federation" preview: forces a fetch+verify and reports
    the resolvable IdP count.

    Args:
        provider (AuthProvider): The saml-kind provider in federation mode.

    Returns:
        int: The number of identity providers resolvable from the metadata.
    """
    return len(_load(provider).entities)


def invalidate(provider_id: int) -> None:
    """Drop any cached federation for a provider (on config change or delete)."""
    with _lock:
        _cache.pop(provider_id, None)
