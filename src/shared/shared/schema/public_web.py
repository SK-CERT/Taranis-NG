"""Module for Public Web (a branded feed hosted by a public-web node) schema."""

from marshmallow import EXCLUDE, Schema, fields

from shared.schema.presentation import PresentationSchema


class PublicWebImageSchema(Schema):
    """Metadata about one uploaded image (the binary is served separately)."""

    kind = fields.Str()
    mime_type = fields.Str()
    filename = fields.Str()


class PublicWebSchema(Schema):
    """Schema for a public web (one branded feed under a public-web node).

    The ``config`` field is a free-form object (branding text, feed sizes,
    languages, ...) owned by the GUI; the backend stores it verbatim.
    """

    class Meta:
        """Ignore unknown fields so the GUI can evolve the config shape freely."""

        unknown = EXCLUDE

    id = fields.Int()
    node_id = fields.Int()
    name = fields.Str()
    hostname = fields.Str()
    config = fields.Raw()
    enabled = fields.Bool(load_default=True, dump_default=True)
    # Host-scoped routing settings - HSTS and the certificate a hostname is
    # served with are properties of that hostname, so they live on the web.
    # Empty means "inherit the instance-wide value" (Application Settings ->
    # Routing & TLS); hsts additionally accepts "on" and "off".
    cert_resolver = fields.Str(load_default="", allow_none=True)
    hsts = fields.Str(load_default="", allow_none=True)
    # The certificate this hostname is served with. The key is write-only: it goes
    # in but never comes back, so the form shows has_tls_key and the summary
    # instead, and an empty key on update means "keep the stored one".
    tls_cert = fields.Str(load_default="", allow_none=True)
    tls_key = fields.Str(load_default="", allow_none=True, load_only=True)


class PublicWebPresentationSchema(PublicWebSchema, PresentationSchema):
    """Schema for presenting a public web in the configuration UI."""

    has_tls_key = fields.Bool(dump_only=True)
    tls_cert_subject = fields.Str(dump_only=True)
    tls_cert_not_after = fields.Str(dump_only=True)
    images = fields.List(fields.Nested(PublicWebImageSchema))
    created = fields.DateTime("%d.%m.%Y - %H:%M:%S")
