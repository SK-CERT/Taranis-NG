"""Validation of the routing and TLS settings before they reach Traefik.

Traefik rejects a dynamic configuration document as a whole: one unknown curve
name and every router in it disappears, including the ones that were fine. The
value of these checks is that a typo in the form comes back as a message on the
form instead of taking the site's routing down on the next poll.

Only the pure validators are exercised here - ``TraefikSettings.update`` itself
needs a database, and the tests deliberately do not have one (see conftest).
"""

from __future__ import annotations

import datetime

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from model.traefik_settings import (
    _validated_curves,
    _validated_headers,
    _validated_min_version,
    _validated_resolver,
    check_cert_key_pair,
)


def _keypair(common_name: str = "feed.example.org") -> tuple[str, str]:
    """Return a fresh self-signed certificate and its private key, both PEM."""
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = datetime.datetime.now(datetime.UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    return (
        certificate.public_bytes(serialization.Encoding.PEM).decode(),
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode(),
    )


def test_headers_are_trimmed_and_blank_names_dropped() -> None:
    assert _validated_headers({"  X-Frame-Options  ": "  SAMEORIGIN  ", "": "ignored"}) == {"X-Frame-Options": "SAMEORIGIN"}


@pytest.mark.parametrize("name", ["X Frame Options", "X-Frame:Options", "X-Frame\nOptions"])
def test_malformed_header_names_are_rejected(name: str) -> None:
    with pytest.raises(ValueError, match="not a valid HTTP header name"):
        _validated_headers({name: "value"})


@pytest.mark.parametrize("value", ["a\r\nX-Injected: yes", "a\nb"])
def test_a_header_value_cannot_smuggle_another_header(value: str) -> None:
    with pytest.raises(ValueError, match="must not contain a line break"):
        _validated_headers({"X-Robots-Tag": value})


def test_known_tls_version_is_kept_and_unknown_rejected() -> None:
    assert _validated_min_version(" VersionTLS12 ") == "VersionTLS12"
    assert _validated_min_version("") == ""
    with pytest.raises(ValueError, match="not a TLS version"):
        _validated_min_version("TLSv1.2")


@pytest.mark.parametrize("version", ["VersionTLS10", "VersionTLS11"])
def test_deprecated_tls_versions_cannot_be_set(version: str) -> None:
    # RFC 8996: these are not a floor anyone should be able to pick from a form,
    # so they are not merely absent from the GUI list - the backend refuses them.
    with pytest.raises(ValueError, match="not a TLS version"):
        _validated_min_version(version)


def test_curves_are_normalised_and_unknown_ones_rejected() -> None:
    assert _validated_curves(" X25519 , CurveP384 ,, ") == "X25519,CurveP384"
    with pytest.raises(ValueError, match="Unknown TLS curve"):
        _validated_curves("X25519,secp256k1")


@pytest.mark.parametrize("resolver", ["my resolver", "resolver`}", "a" * 65])
def test_resolver_name_must_be_a_bare_identifier(resolver: str) -> None:
    with pytest.raises(ValueError, match="not a valid certificate resolver name"):
        _validated_resolver(resolver)


def test_matching_pair_is_accepted() -> None:
    certificate, key = _keypair()

    check_cert_key_pair(certificate, key)  # does not raise


def test_key_from_a_different_certificate_is_rejected() -> None:
    certificate, _ = _keypair()
    _, other_key = _keypair("other.example.org")

    # Traefik would take this and fail in every handshake instead.
    with pytest.raises(ValueError, match="does not match the certificate"):
        check_cert_key_pair(certificate, other_key)


def test_unreadable_pem_is_reported_per_side() -> None:
    certificate, key = _keypair()

    with pytest.raises(ValueError, match="certificate could not be read as PEM"):
        check_cert_key_pair("not a certificate", key)
    with pytest.raises(ValueError, match="private key could not be read as PEM"):
        check_cert_key_pair(certificate, "not a key")
