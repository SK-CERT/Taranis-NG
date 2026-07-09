"""Routing and TLS settings core hands to Traefik (single row).

Traefik reads two kinds of configuration. The *static* one - entry points,
providers, the ACME resolvers - is read once at process start and lives in
``docker/.env`` and ``docker/docker-compose.yml``; nothing here can change it.
The *dynamic* one is polled at runtime, and that is what this table holds: the
response headers the public webs are served with, the TLS floor, and an optional
default certificate. :mod:`api.traefik` turns it into a Traefik configuration
document, together with the routers derived from the configured webs.

Everything here is therefore editable in the GUI and takes effect on Traefik's
next poll, with no restart and without core needing any access to the Traefik
container.
"""

from __future__ import annotations

import re
from datetime import datetime

from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, load_pem_private_key
from managers import crypto_manager
from managers.db_manager import db
from shared.common import TZ
from shared.schema.traefik_settings import TraefikSettingsSchema

# The floor every deployment starts from, and what the GUI shows on first open.
# Kept in step with docker/traefik/dynamic/fallback.yml, which is the copy the
# catch-all router falls back on while core is unreachable - that one cannot be
# served from here, because it exists for the case where "here" is unavailable.
DEFAULT_SECURITY_HEADERS: dict[str, str] = {
    # No Strict-Transport-Security here: it is its own middleware, built from the
    # hsts_* columns and applied to the whole instance (see hsts_header_value).
    # Two middlewares setting the same header would fight, and HSTS is scoped to
    # the host anyway, so one policy per instance is the only coherent choice.
    "X-Frame-Options": "SAMEORIGIN",
    "X-Robots-Tag": "noindex, nofollow, noarchive, nosnippet, noimageindex, notranslate",
    "X-Content-Type-Options": "nosniff",
    "Permissions-Policy": (
        "accelerometer=(), ambient-light-sensor=(), autoplay=(), battery=(), camera=(), cross-origin-isolated=(), "
        "display-capture=(), document-domain=(), encrypted-media=(), execution-while-not-rendered=(), "
        "execution-while-out-of-viewport=(), fullscreen=(), geolocation=(), gyroscope=(), keyboard-map=(), "
        "magnetometer=(), microphone=(), midi=(), navigation-override=(), payment=(), picture-in-picture=(), "
        "publickey-credentials-get=(), screen-wake-lock=(), sync-xhr=(), usb=(), web-share=(), "
        "xr-spatial-tracking=(), clipboard-read=(), clipboard-write=(), gamepad=(), speaker-selection=(), "
        "conversion-measurement=(), focus-without-user-activation=(), hid=(), idle-detection=(), "
        "interest-cohort=(), serial=(), sync-script=(), trust-token-redemption=(), window-placement=(), "
        "vertical-scroll=()"
    ),
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Cross-Origin-Embedder-Policy": "require-corp",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Content-Security-Policy": (
        "default-src 'self'; font-src https://cdn.jsdelivr.net:443 'self'; "
        "script-src https://cdn.jsdelivr.net:443 'self' 'unsafe-inline'; "
        "script-src-elem https://cdn.jsdelivr.net:443 'self' 'unsafe-inline'; "
        "style-src-attr 'self' 'unsafe-inline'; "
        "style-src-elem https://cdn.jsdelivr.net:443 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; frame-ancestors 'self'; frame-src 'self'"
    ),
}

DEFAULT_TLS_MIN_VERSION = "VersionTLS13"
DEFAULT_TLS_CURVE_PREFERENCES = "X25519MLKEM768,X25519,CurveP521,CurveP384,CurveP256"

# HSTS ships off. It is the one setting here that a browser remembers and refuses
# to let the user override: while it is in force a certificate error cannot be
# clicked through, so switching it on before certificates are actually being
# issued locks everyone out of the GUI for the whole max-age.
DEFAULT_HSTS_MAX_AGE = 31536000  # one year, the usual production value
# Two years. Traefik would serve anything, but a typo of a few extra digits is
# unrecoverable for real visitors, so the form refuses it.
HSTS_MAX_AGE_LIMIT = 63072000
# What the preload list itself demands of a submitted site.
HSTS_PRELOAD_MIN_MAX_AGE = 31536000

# Traefik rejects a dynamic configuration naming a version or curve it does not
# know, and rejecting the document means dropping every router in it - including
# the ones that were fine. So the values are checked before they are stored.
# TLS 1.0 and 1.1 are deliberately absent: RFC 8996 deprecates both, every current
# browser refuses them, and they are not something an administrator should be able
# to re-enable from a web form. VersionTLS12 is also Traefik's own default, so an
# empty value is safe.
TLS_VERSIONS = ("VersionTLS12", "VersionTLS13")
# Key-exchange groups (TLS 1.3 supported_groups / ECDHE), not certificate curves -
# the two are unrelated. An RSA certificate is served fine with this list: the group
# does the exchange and the RSA key only signs. X25519MLKEM768 is the post-quantum
# hybrid and is offered first.
TLS_CURVES = ("X25519MLKEM768", "X25519", "CurveP521", "CurveP384", "CurveP256")

# RFC 7230 header field name.
_HEADER_NAME_PATTERN = re.compile(r"^[A-Za-z0-9!#$%&'*+\-.^_`|~]+$")
# Interpolated into a router's tls.certResolver, and a resolver name is a bare
# identifier in Traefik.
_RESOLVER_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class TraefikSettings(db.Model):
    """The GUI-managed part of the Traefik configuration.

    Attributes:
        id (int): Always 1 - this table holds a single row.
        security_headers (dict): Response headers added to every public web,
            as the ``public-web-security-headers`` middleware.
        hsts_enabled (bool): Whether to send Strict-Transport-Security. Off sends
            ``max-age=0``, which tells browsers to forget any pin they hold.
        hsts_max_age (int): Lifetime of the pin, in seconds.
        hsts_include_subdomains (bool): Whether the pin covers every subdomain.
        hsts_preload (bool): Whether to advertise for the browser preload list.
        tls_min_version (str): Lowest TLS version accepted, one of TLS_VERSIONS;
            everything from it upwards is allowed. Empty means Traefik's default.
        tls_curve_preferences (str): Comma-separated key-exchange groups, most
            preferred first, each one of TLS_CURVES. Unrelated to the certificate's
            key algorithm.
        cert_resolver (str): ACME resolver the generated routers should use.
            Overrides the TRAEFIK_CERT_RESOLVER environment variable; empty
            falls back to it.
        default_cert (str): PEM certificate chain served for hostnames no router
            matches. Empty means Traefik's own self-signed default.
        default_key (str): The matching private key, encrypted at rest.
        updated_by (str): User who last updated the settings.
        updated_at (datetime): Timestamp of the last update.
    """

    __tablename__ = "traefik_settings"

    id = db.Column(db.Integer, primary_key=True)
    security_headers = db.Column(db.JSON, nullable=False, default=dict)
    hsts_enabled = db.Column(db.Boolean, nullable=False, default=False, server_default="false")
    hsts_max_age = db.Column(db.Integer, nullable=False, default=DEFAULT_HSTS_MAX_AGE, server_default=str(DEFAULT_HSTS_MAX_AGE))
    hsts_include_subdomains = db.Column(db.Boolean, nullable=False, default=False, server_default="false")
    hsts_preload = db.Column(db.Boolean, nullable=False, default=False, server_default="false")
    tls_min_version = db.Column(db.String(), nullable=True)
    tls_curve_preferences = db.Column(db.String(), nullable=True)
    cert_resolver = db.Column(db.String(), nullable=True)
    default_cert = db.Column(db.Text(), nullable=True)
    default_key = db.Column(db.Text(), nullable=True)
    updated_by = db.Column(db.String())
    updated_at = db.Column(db.DateTime)

    @classmethod
    def get(cls) -> TraefikSettings:
        """Return the settings row, creating it with the shipped defaults when absent.

        Returns:
            TraefikSettings: The single settings row.
        """
        record = db.session.get(cls, 1)
        if not record:
            record = cls()
            record.id = 1
            record.security_headers = dict(DEFAULT_SECURITY_HEADERS)
            record.tls_min_version = DEFAULT_TLS_MIN_VERSION
            record.tls_curve_preferences = DEFAULT_TLS_CURVE_PREFERENCES
            db.session.add(record)
            db.session.commit()
        return record

    @classmethod
    def get_json(cls) -> dict:
        """Return the settings in JSON format."""
        return TraefikSettingsSchema().dump(cls.get())

    @classmethod
    def update(cls, data: dict, user_name: str) -> TraefikSettings:
        """Update the routing and TLS settings.

        Args:
            data (dict): The new settings.
            user_name (str): User performing the update.

        Returns:
            TraefikSettings: The updated settings row.

        Raises:
            ValueError: When a value would produce a configuration Traefik
                rejects, or when the certificate and key do not belong together.
        """
        new = TraefikSettingsSchema().load(data)
        record = cls.get()

        record.security_headers = _validated_headers(new.get("security_headers") or {})
        record.hsts_enabled = bool(new.get("hsts_enabled"))
        record.hsts_max_age = _validated_hsts_max_age(new.get("hsts_max_age"))
        record.hsts_include_subdomains = bool(new.get("hsts_include_subdomains"))
        record.hsts_preload = bool(new.get("hsts_preload"))
        _check_hsts(record)
        record.tls_min_version = _validated_min_version(new.get("tls_min_version"))
        record.tls_curve_preferences = _validated_curves(new.get("tls_curve_preferences"))
        record.cert_resolver = _validated_resolver(new.get("cert_resolver"))

        certificate = (new.get("default_cert") or "").strip()
        # Empty means "keep the stored key" (the form never receives it back, so
        # it cannot send it either) - the same rule as auth_provider secrets.
        key = (new.get("default_key") or "").strip()
        if not certificate:
            # Clearing the certificate clears the key with it: a key alone is
            # unusable, and leaving it behind would keep a secret nobody can see.
            record.default_cert = ""
            record.default_key = ""
        else:
            plaintext_key = key or record.get_default_key_plaintext()
            if not plaintext_key:
                msg = "A default certificate needs its private key"
                raise ValueError(msg)
            check_cert_key_pair(certificate, plaintext_key)
            # Normalised to exactly one trailing newline: PEM is whitespace-
            # sensitive, and this is the last point that can guarantee it.
            record.default_cert = certificate + "\n"
            if key:
                record.default_key = crypto_manager.encrypt(key + "\n")

        record.updated_by = user_name
        record.updated_at = datetime.now(TZ)
        db.session.commit()
        return record

    @property
    def has_default_key(self) -> bool:
        """Whether a private key is stored (the key itself is never exposed)."""
        return bool(self.default_key)

    @property
    def cert_subject(self) -> str:
        """Subject of the default certificate, for display. Empty when there is none."""
        return cert_subject(self.default_cert)

    @property
    def cert_not_after(self) -> str:
        """Expiry of the default certificate, for display. Empty when there is none."""
        return cert_not_after(self.default_cert)

    def get_default_key_plaintext(self) -> str:
        """Return the decrypted private key, or an empty string when there is none."""
        if not self.default_key:
            return ""
        return crypto_manager.decrypt(self.default_key) or ""

    def get_curve_preferences(self) -> list[str]:
        """Return the curve preferences as a normalized list."""
        return [curve.strip() for curve in (self.tls_curve_preferences or "").split(",") if curve.strip()]

    def hsts_header_value(self, *, forced: bool | None = None) -> str:
        """Build the Strict-Transport-Security value, including when HSTS is off.

        Off is ``max-age=0`` rather than no header at all, for two reasons. The
        middleware is named by routers declared on container labels, and Traefik
        disables a router naming a middleware that does not exist - so it has to
        be served unconditionally. And ``max-age=0`` is the only way to release
        browsers that are already pinned: turning the setting off then actively
        undoes it, instead of leaving people locked out until the pin expires.

        Args:
            forced (bool | None): Override the instance switch - a web with a
                per-web "on"/"off" uses the same parameters but its own switch.
                None follows ``hsts_enabled``.

        Returns:
            (str): The header value, e.g. "max-age=31536000; includeSubDomains".
        """
        enabled = self.hsts_enabled if forced is None else forced
        if not enabled:
            return "max-age=0"
        value = f"max-age={int(self.hsts_max_age or 0)}"
        if self.hsts_include_subdomains:
            value += "; includeSubDomains"
        if self.hsts_preload:
            value += "; preload"
        return value


def _validated_headers(headers: dict) -> dict[str, str]:
    """Return the headers, rejecting names or values Traefik could not serve.

    Args:
        headers (dict): Header name to value.

    Returns:
        (dict[str, str]): The headers, trimmed.

    Raises:
        ValueError: On a malformed name, or a value containing a line break -
            which would let one header inject another.
    """
    validated: dict[str, str] = {}
    for raw_name, raw_value in headers.items():
        name = (raw_name or "").strip()
        value = (raw_value or "").strip()
        if not name:
            continue
        if not _HEADER_NAME_PATTERN.match(name):
            msg = f"'{name}' is not a valid HTTP header name"
            raise ValueError(msg)
        if "\r" in value or "\n" in value:
            msg = f"The value of '{name}' must not contain a line break"
            raise ValueError(msg)
        validated[name] = value
    return validated


def _validated_hsts_max_age(max_age: int | str | None) -> int:
    """Return the HSTS lifetime in seconds, or raise when it is not usable.

    Args:
        max_age (int | str | None): The submitted value.

    Returns:
        (int): The lifetime, within 0..HSTS_MAX_AGE_LIMIT.

    Raises:
        ValueError: When it is not a whole number, negative, or beyond the limit.
    """
    try:
        value = DEFAULT_HSTS_MAX_AGE if max_age is None or max_age == "" else int(max_age)
    except (TypeError, ValueError) as ex:
        msg = "The HSTS max-age must be a whole number of seconds"
        raise ValueError(msg) from ex
    if value < 0:
        msg = "The HSTS max-age cannot be negative"
        raise ValueError(msg)
    if value > HSTS_MAX_AGE_LIMIT:
        msg = f"The HSTS max-age cannot exceed {HSTS_MAX_AGE_LIMIT} seconds (two years)"
        raise ValueError(msg)
    return value


def _check_hsts(record: TraefikSettings) -> None:
    """Reject HSTS combinations a browser would refuse or an administrator would regret.

    Args:
        record (TraefikSettings): The row, with the HSTS fields already assigned.

    Raises:
        ValueError: When HSTS is on with no lifetime, or preload is requested
            without the two things the preload list requires of a site.
    """
    if not record.hsts_enabled:
        return
    if record.hsts_max_age == 0:
        msg = "HSTS with max-age=0 does nothing; either raise the max-age or turn HSTS off"
        raise ValueError(msg)
    if record.hsts_preload and not record.hsts_include_subdomains:
        msg = "The browser preload list only accepts sites that include subdomains"
        raise ValueError(msg)
    if record.hsts_preload and record.hsts_max_age < HSTS_PRELOAD_MIN_MAX_AGE:
        msg = f"The browser preload list requires a max-age of at least {HSTS_PRELOAD_MIN_MAX_AGE} seconds (one year)"
        raise ValueError(msg)


def _validated_min_version(version: str | None) -> str:
    """Return the TLS version, or raise when Traefik would not recognise it."""
    value = (version or "").strip()
    if not value:
        return ""
    if value not in TLS_VERSIONS:
        msg = f"'{value}' is not a TLS version Traefik knows; expected one of {', '.join(TLS_VERSIONS)}"
        raise ValueError(msg)
    return value


def _validated_curves(curves: str | None) -> str:
    """Return the comma-separated curve list, or raise on an unknown curve."""
    names = [curve.strip() for curve in (curves or "").split(",") if curve.strip()]
    unknown = [name for name in names if name not in TLS_CURVES]
    if unknown:
        msg = f"Unknown TLS curve(s): {', '.join(unknown)}; expected any of {', '.join(TLS_CURVES)}"
        raise ValueError(msg)
    return ",".join(names)


def _validated_resolver(resolver: str | None) -> str:
    """Return the resolver name, or raise when it is not a bare identifier."""
    value = (resolver or "").strip()
    if value and not _RESOLVER_PATTERN.match(value):
        msg = f"'{value}' is not a valid certificate resolver name"
        raise ValueError(msg)
    return value


def check_cert_key_pair(certificate: str, key: str) -> None:
    """Verify the private key belongs to the certificate.

    Traefik would accept a mismatched pair into its configuration and only fail
    later, in the TLS handshake, on every request. Catching it here turns that
    into a message on the form.

    Args:
        certificate (str): PEM certificate chain; the leaf is checked.
        key (str): PEM private key.

    Raises:
        ValueError: When either side is unreadable or they do not match.
    """
    try:
        parsed_cert = x509.load_pem_x509_certificate(certificate.encode())
    except ValueError as ex:
        msg = f"The certificate could not be read as PEM: {ex}"
        raise ValueError(msg) from ex

    try:
        parsed_key = load_pem_private_key(key.encode(), password=None)
    except (ValueError, TypeError) as ex:
        msg = f"The private key could not be read as PEM: {ex}. Encrypted keys must be decrypted first."
        raise ValueError(msg) from ex

    def public_bytes(public_key: object) -> bytes:
        return public_key.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)

    if public_bytes(parsed_key.public_key()) != public_bytes(parsed_cert.public_key()):
        msg = "The private key does not match the certificate"
        raise ValueError(msg)


def parse_cert(certificate: str | None) -> x509.Certificate | None:
    """Parse a PEM certificate, or return None when absent or unreadable."""
    if not certificate:
        return None
    try:
        return x509.load_pem_x509_certificate(certificate.encode())
    except ValueError:
        return None


def cert_subject(certificate: str | None) -> str:
    """Subject of a PEM certificate, for display. Empty when there is none."""
    parsed = parse_cert(certificate)
    return parsed.subject.rfc4514_string() if parsed else ""


def cert_not_after(certificate: str | None) -> str:
    """Expiry of a PEM certificate, for display. Empty when there is none."""
    parsed = parse_cert(certificate)
    return parsed.not_valid_after_utc.isoformat() if parsed else ""
