"""Reports the certificate Traefik actually serves for each hostname.

Traefik decides which certificate a hostname gets - ACME, one uploaded in the GUI,
the instance default, or its own self-signed fallback - and nothing in the database
says which of those won. That gap is easy to trip over: changing the ACME key type,
for instance, has no visible effect until the certificate is next requested, and
the only way to tell was to run ``openssl s_client`` by hand.

So this asks the authority directly. It opens a TLS connection to Traefik on the
compose network, sets SNI to the hostname in question, and reads back whatever
certificate Traefik chose to present. That needs no access to Traefik's ACME store,
no Docker socket and no public DNS - the connection goes to the container, and only
the SNI carries the hostname.

Read-only by nature: there is no way to *ask* for a certificate here. Traefik's API
is read-only (POST returns 405) and its ACME state lives inside the container, so
forcing an issue means editing acme.json and restarting Traefik. This reports; it
does not act.
"""

from __future__ import annotations

import socket
import ssl
from datetime import UTC, datetime, timedelta

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec, ed448, ed25519, rsa
from managers.log_manager import logger

# The Traefik container on the compose network. The hostname being asked about
# travels in the SNI, so this never depends on how public DNS resolves.
_TRAEFIK_HOST = "traefik"
_TRAEFIK_PORT = 443
# Short: this runs while an administrator waits for a page.
_TIMEOUT_SECONDS = 3

# Traefik's built-in self-signed certificate, presented when it has nothing better.
_TRAEFIK_DEFAULT_SUBJECT = "TRAEFIK DEFAULT CERT"

# Traefik renews inside the last 30 days of validity. Worth showing, because it is
# the answer to "when will my change to the ACME settings actually take effect?".
_RENEWAL_WINDOW_DAYS = 30


def _key_description(certificate: x509.Certificate) -> str:
    """Describe the certificate's public key, e.g. "EC-384" or "RSA-4096"."""
    public_key = certificate.public_key()
    if isinstance(public_key, rsa.RSAPublicKey):
        return f"RSA-{public_key.key_size}"
    if isinstance(public_key, ec.EllipticCurvePublicKey):
        return f"EC-{public_key.curve.key_size}"
    if isinstance(public_key, ed25519.Ed25519PublicKey):
        return "Ed25519"
    if isinstance(public_key, ed448.Ed448PublicKey):
        return "Ed448"
    return type(public_key).__name__


def _common_name(name: x509.Name) -> str:
    """Return the CN of a distinguished name, falling back to its full form."""
    attributes = name.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
    return attributes[0].value if attributes else name.rfc4514_string()


def fetch_served_certificate(hostname: str) -> dict:
    """Ask Traefik which certificate it serves for one hostname.

    Args:
        hostname (str): The name to put in the SNI.

    Returns:
        (dict): What was found. ``status`` is "ok" when a certificate came back,
            "default" when it is Traefik's self-signed fallback (i.e. no
            certificate is configured for this hostname), or "error" with a
            ``message`` when the handshake did not complete.
    """
    result: dict[str, object] = {"hostname": hostname}
    # The certificate is the answer, so its validity is beside the point - a
    # self-signed or expired one still has to be reported rather than refused.
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    try:
        with (
            socket.create_connection((_TRAEFIK_HOST, _TRAEFIK_PORT), timeout=_TIMEOUT_SECONDS) as raw,
            context.wrap_socket(raw, server_hostname=hostname) as tls,
        ):
            der = tls.getpeercert(binary_form=True)
    except (OSError, ssl.SSLError) as ex:
        logger.debug(f"Could not read the certificate Traefik serves for '{hostname}': {ex}")
        return {**result, "status": "error", "message": str(ex)}

    if not der:
        return {**result, "status": "error", "message": "Traefik presented no certificate"}

    certificate = x509.load_der_x509_certificate(der)
    subject = _common_name(certificate.subject)
    issuer = _common_name(certificate.issuer)
    not_after = certificate.not_valid_after_utc
    days_left = (not_after - datetime.now(UTC)).days

    return {
        **result,
        "status": "default" if _TRAEFIK_DEFAULT_SUBJECT in subject.upper() else "ok",
        "subject": subject,
        "issuer": issuer,
        "key_type": _key_description(certificate),
        "not_after": not_after.isoformat(),
        "days_left": days_left,
        # When Traefik would renew an ACME certificate. Also the answer to "why has
        # my ACME change not taken effect yet" - it will, at this point.
        "renews_after": (not_after - timedelta(days=_RENEWAL_WINDOW_DAYS)).date().isoformat(),
        "self_signed": subject == issuer,
    }


def collect_certificates(hostnames: list[str]) -> list[dict]:
    """Report the certificate served for each hostname, in the order given.

    Args:
        hostnames (list[str]): Hostnames to ask about; blanks and repeats dropped.

    Returns:
        (list[dict]): One entry per hostname, see :func:`fetch_served_certificate`.
    """
    seen: set[str] = set()
    report: list[dict] = []
    for raw in hostnames:
        hostname = (raw or "").strip().lower()
        if not hostname or hostname in seen:
            continue
        seen.add(hostname)
        report.append(fetch_served_certificate(hostname))
    return report
