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
    # Defaulted so a client that predates it - ansible on an older checkout, or the
    # GUI round-tripping a node fetched before an upgrade - still validates.
    #
    # fronted_by_core is deliberately NOT here. It is decided by where the node runs,
    # not by a client: prestart_core.sh sets it for the node beside core and everything
    # else defaults to false. Exposing it with a default would also mean any update
    # omitting it silently cleared it, taking core's own webs down with it.
    cert_resolver = fields.Str(load_default="", allow_none=True)


class PublicWebNodePresentationSchema(PublicWebNodeSchema, PresentationSchema):
    """Schema for presenting a public-web node in the configuration UI."""

    status = fields.Str()
    created = fields.DateTime("%d.%m.%Y - %H:%M:%S")
    last_seen = fields.DateTime("%d.%m.%Y - %H:%M:%S")
