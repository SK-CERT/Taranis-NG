"""Federation metadata trust path: resolve an IdP only from verified metadata.

Signed aggregates are built at test time (no large vendored fixtures): a fresh
keypair signs a small ``EntitiesDescriptor``, and its certificate is the trust
anchor. This exercises the real ``minisignxml`` verification the resolver relies
on, so the security properties - reject a wrong anchor, reject tampering, never
resolve an entity that is not in the verified document - are actually tested.
"""

from __future__ import annotations

import base64
import types
from datetime import UTC, datetime, timedelta

import pytest
from auth import saml_federation
from auth.saml_authenticator import load_idp_certificates
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from lxml import etree
from minisignxml.sign import sign

MD = "urn:oasis:names:tc:SAML:2.0:metadata"
DS = "http://www.w3.org/2000/09/xmldsig#"
REDIRECT = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"


def _keypair() -> tuple[rsa.RSAPrivateKey, x509.Certificate]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test-federation")])
    now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    return key, certificate


def _idp_entity(entity_id: str, cert_b64: str, *, sso: bool = True, cert: bool = True) -> str:
    parts = ""
    if cert:
        parts += (
            '<md:KeyDescriptor use="signing"><ds:KeyInfo><ds:X509Data>'
            f"<ds:X509Certificate>{cert_b64}</ds:X509Certificate>"
            "</ds:X509Data></ds:KeyInfo></md:KeyDescriptor>"
        )
    if sso:
        parts += f'<md:SingleSignOnService Binding="{REDIRECT}" Location="https://sso.example.org/{entity_id.rsplit("/", 1)[-1]}"/>'
    return (
        f'<md:EntityDescriptor entityID="{entity_id}">'
        f'<md:IDPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">'
        f"{parts}</md:IDPSSODescriptor></md:EntityDescriptor>"
    )


def _signed_aggregate(specs: list[tuple[str, bool, bool]], *, valid_until: str | None = None) -> tuple[bytes, str]:
    """Build and sign an EntitiesDescriptor; return (signed XML, trust-anchor PEM).

    Each spec is ``(entity_id, has_sso, has_signing_cert)``.
    """
    key, certificate = _keypair()
    cert_b64 = base64.b64encode(certificate.public_bytes(serialization.Encoding.DER)).decode()
    entities = "".join(_idp_entity(entity_id, cert_b64, sso=sso, cert=cert) for entity_id, sso, cert in specs)
    valid = f' validUntil="{valid_until}"' if valid_until else ""
    xml = f'<md:EntitiesDescriptor xmlns:md="{MD}" xmlns:ds="{DS}" ID="_aggregate"{valid}>{entities}</md:EntitiesDescriptor>'
    signed = sign(element=etree.fromstring(xml.encode()), private_key=key, certificate=certificate)
    anchor_pem = certificate.public_bytes(serialization.Encoding.PEM).decode()
    return signed, anchor_pem


def _provider(anchor_pem: str, *, provider_id: int = 1) -> object:
    return types.SimpleNamespace(
        id=provider_id,
        name="test federation",
        config={
            "discovery_url": "https://ds.example.org/wayf",
            "federation_metadata_url": "https://metadata.example.org/aggregate",
            "federation_metadata_cert": anchor_pem,
        },
    )


def test_resolves_a_known_identity_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    signed, anchor = _signed_aggregate([("https://idp.example.org/a", True, True)])
    monkeypatch.setattr(saml_federation, "_fetch", lambda _url: signed)

    resolved = saml_federation.resolve_idp(_provider(anchor), "https://idp.example.org/a")

    assert resolved is not None
    assert resolved.entity_id == "https://idp.example.org/a"
    assert resolved.sso_url == "https://sso.example.org/a"
    assert len(load_idp_certificates(resolved.certificates)) == 1  # the bundle is usable downstream


def test_unknown_entity_is_trust_gated(monkeypatch: pytest.MonkeyPatch) -> None:
    signed, anchor = _signed_aggregate([("https://idp.example.org/a", True, True)])
    monkeypatch.setattr(saml_federation, "_fetch", lambda _url: signed)

    assert saml_federation.resolve_idp(_provider(anchor), "https://idp.example.org/not-in-federation") is None


def test_wrong_trust_anchor_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    signed, _ = _signed_aggregate([("https://idp.example.org/a", True, True)])
    _, other_anchor = _signed_aggregate([("https://idp.example.org/b", True, True)])  # a different key
    monkeypatch.setattr(saml_federation, "_fetch", lambda _url: signed)

    with pytest.raises(ValueError, match="could not be loaded"):
        saml_federation.resolve_idp(_provider(other_anchor), "https://idp.example.org/a")


def test_tampered_metadata_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    signed, anchor = _signed_aggregate([("https://idp.example.org/a", True, True)])
    tampered = signed.replace(b"https://sso.example.org/a", b"https://sso.evil.example/a")
    monkeypatch.setattr(saml_federation, "_fetch", lambda _url: tampered)

    with pytest.raises(ValueError, match="could not be loaded"):
        saml_federation.resolve_idp(_provider(anchor), "https://idp.example.org/a")


def test_entities_missing_sso_or_certificate_are_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    signed, anchor = _signed_aggregate(
        [
            ("https://idp.example.org/ok", True, True),
            ("https://idp.example.org/no-sso", False, True),
            ("https://idp.example.org/no-cert", True, False),
        ],
    )
    monkeypatch.setattr(saml_federation, "_fetch", lambda _url: signed)
    provider = _provider(anchor)

    assert saml_federation.resolve_idp(provider, "https://idp.example.org/ok") is not None
    assert saml_federation.resolve_idp(provider, "https://idp.example.org/no-sso") is None
    assert saml_federation.resolve_idp(provider, "https://idp.example.org/no-cert") is None


def test_verify_metadata_counts_usable_identity_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    signed, anchor = _signed_aggregate(
        [
            ("https://idp.example.org/a", True, True),
            ("https://idp.example.org/b", True, True),
            ("https://idp.example.org/no-sso", False, True),  # not usable -> not counted
        ],
        valid_until="2099-01-01T00:00:00Z",
    )
    monkeypatch.setattr(saml_federation, "_fetch", lambda _url: signed)

    result = saml_federation.verify_metadata("https://metadata.example.org/aggregate", anchor)

    assert result["entity_count"] == 2
    assert result["valid_until"] == "2099-01-01T00:00:00+00:00"


def test_missing_url_or_anchor_is_rejected() -> None:
    with pytest.raises(ValueError, match="metadata URL and its signing certificate"):
        saml_federation.verify_metadata("", "anchor")


def test_verified_metadata_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    signed, anchor = _signed_aggregate([("https://idp.example.org/a", True, True)])
    calls = {"count": 0}

    def _fetch(_url: str) -> bytes:
        calls["count"] += 1
        return signed

    monkeypatch.setattr(saml_federation, "_fetch", _fetch)
    provider = _provider(anchor)

    saml_federation.resolve_idp(provider, "https://idp.example.org/a")
    saml_federation.resolve_idp(provider, "https://idp.example.org/a")

    assert calls["count"] == 1


def test_invalidate_forces_a_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    signed, anchor = _signed_aggregate([("https://idp.example.org/a", True, True)])
    calls = {"count": 0}

    def _fetch(_url: str) -> bytes:
        calls["count"] += 1
        return signed

    monkeypatch.setattr(saml_federation, "_fetch", _fetch)
    provider = _provider(anchor)

    saml_federation.resolve_idp(provider, "https://idp.example.org/a")
    saml_federation.invalidate(provider.id)
    saml_federation.resolve_idp(provider, "https://idp.example.org/a")

    assert calls["count"] == 2


def test_stale_metadata_is_served_when_a_refresh_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    signed, anchor = _signed_aggregate([("https://idp.example.org/a", True, True)])
    monkeypatch.setattr(saml_federation, "_fetch", lambda _url: signed)
    provider = _provider(anchor)

    saml_federation.resolve_idp(provider, "https://idp.example.org/a")  # populate the cache
    saml_federation._cache[provider.id].expires_at = datetime.now(UTC) - timedelta(seconds=1)  # force it stale

    def _boom(_url: str) -> bytes:
        msg = "network down"
        raise RuntimeError(msg)

    monkeypatch.setattr(saml_federation, "_fetch", _boom)

    resolved = saml_federation.resolve_idp(provider, "https://idp.example.org/a")
    assert resolved is not None  # stale entry served rather than locking users out
