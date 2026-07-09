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


class PublicWebPresentationSchema(PublicWebSchema, PresentationSchema):
    """Schema for presenting a public web in the configuration UI."""

    images = fields.List(fields.Nested(PublicWebImageSchema))
    created = fields.DateTime("%d.%m.%Y - %H:%M:%S")
