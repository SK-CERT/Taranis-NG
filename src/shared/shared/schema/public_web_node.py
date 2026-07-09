"""Module for Public Web node schema."""

from marshmallow import EXCLUDE, Schema, fields

from shared.schema.presentation import PresentationSchema


class PublicWebNodeSchema(Schema):
    """Schema for a public-web node (a read-only report-feed consumer)."""

    class Meta:
        """Ignore presentation-only fields (title/status/last_seen/...) the GUI round-trips on update."""

        unknown = EXCLUDE

    id = fields.Int()
    name = fields.Str()
    description = fields.Str()
    api_url = fields.Str()
    api_key = fields.Str()


class PublicWebNodePresentationSchema(PublicWebNodeSchema, PresentationSchema):
    """Schema for presenting a public-web node in the configuration UI."""

    status = fields.Str()
    created = fields.DateTime("%d.%m.%Y - %H:%M:%S")
    last_seen = fields.DateTime("%d.%m.%Y - %H:%M:%S")
