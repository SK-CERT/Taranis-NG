"""This module defines the schema for the GUI-managed Traefik dynamic configuration."""

from marshmallow import EXCLUDE, Schema, fields


class TraefikSettingsSchema(Schema):
    """Marshmallow schema for the routing and TLS settings core serves to Traefik.

    Only the parts Traefik accepts at runtime are here. Its static configuration
    (entry points, providers, the ACME resolvers themselves) is read once at
    startup and lives in ``docker/.env`` and ``docker/docker-compose.yml``.

    The private key is write-only: it goes in, but never comes back out. The
    form shows ``has_default_key`` and the certificate summary instead, and an
    empty ``default_key`` on update means "keep the stored one".
    """

    class Meta:
        """Meta class to define schema behavior."""

        unknown = EXCLUDE

    security_headers = fields.Dict(keys=fields.Str(), values=fields.Str(), load_default=dict)
    hsts_enabled = fields.Bool(load_default=False, dump_default=False)
    hsts_max_age = fields.Int(load_default=31536000, allow_none=True)
    hsts_include_subdomains = fields.Bool(load_default=False, dump_default=False)
    hsts_preload = fields.Bool(load_default=False, dump_default=False)
    tls_min_version = fields.Str(load_default="", allow_none=True)
    tls_curve_preferences = fields.Str(load_default="", allow_none=True)
    cert_resolver = fields.Str(load_default="", allow_none=True)
    default_cert = fields.Str(load_default="", allow_none=True)
    default_key = fields.Str(load_default="", allow_none=True, load_only=True)

    has_default_key = fields.Bool(dump_only=True)
    # Human-readable summary of default_cert, so the form can say which
    # certificate is in use without parsing PEM in the browser.
    cert_subject = fields.Str(dump_only=True)
    cert_not_after = fields.Str(dump_only=True)
    updated_by = fields.Str(dump_only=True)
    updated_at = fields.Str(dump_only=True)
