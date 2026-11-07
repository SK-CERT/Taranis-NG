"""Product preset schemas.

A product preset is what a product is published as: a set of deliveries, each a language, a
product format (presenter and template) and a publishing channel, and optionally the public web.
Deliveries combine freely - one format may go to several channels, several formats to one
channel, and several languages of one format to the same channel.
"""

from marshmallow import EXCLUDE, Schema, fields

from shared.schema.acl_entry import ACLEntryStatusSchema
from shared.schema.presentation import PresentationSchema


class ProductPresetDeliverySchema(Schema):
    """One delivery: a language and a format, and the channel it is sent to (none: only previewed).

    A delivery without a language renders the product in the language it is written in.
    """

    class Meta:
        """Meta class."""

        unknown = EXCLUDE

    id = fields.Int(load_default=None, allow_none=True)
    language = fields.Str(load_default=None, allow_none=True)
    product_format_id = fields.Int(required=True)
    publishing_channel_id = fields.Str(load_default=None, allow_none=True)
    product_format_title = fields.Str(dump_only=True)
    publishing_channel_name = fields.Str(dump_only=True, allow_none=True)
    publisher_type = fields.Str(dump_only=True, allow_none=True)


class ProductPresetSchema(Schema):
    """A product preset as it is configured."""

    class Meta:
        """Meta class."""

        unknown = EXCLUDE

    id = fields.Int(load_default=-1, allow_none=True)
    name = fields.Str(load_default="")
    description = fields.Str(load_default="", allow_none=True)
    # The MDI icon it and its products show (none: the default).
    icon = fields.Str(load_default=None, allow_none=True)
    deliveries = fields.Nested(ProductPresetDeliverySchema, many=True, load_default=list)
    # The public-web delivery: published products appear on these webs (none listed: every web).
    public_web_enabled = fields.Bool(load_default=False)
    public_web_ids = fields.List(fields.Int(), load_default=list)
    public_web_names = fields.List(fields.Str(), dump_only=True)
    updated_at = fields.DateTime("%d.%m.%Y - %H:%M", dump_only=True)
    updated_by = fields.Str(dump_only=True, allow_none=True)


class ProductPresetPresentationSchema(ProductPresetSchema, ACLEntryStatusSchema, PresentationSchema):
    """A product preset as lists show it."""

    # The webs a product of it can be shown on (its own, else every web), for the product to pick from.
    web_choices = fields.List(fields.Dict(), dump_only=True)
