"""Product schema module."""

from marshmallow import EXCLUDE, Schema, fields

from shared.schema.acl_entry import ACLEntryStatusSchema
from shared.schema.presentation import PresentationSchema
from shared.schema.report_item import ReportItemPresentationSchema


class ProductSchemaBase(Schema):
    """Base product schema."""

    class Meta:
        """Meta class."""

        unknown = EXCLUDE

    id = fields.Int()
    title = fields.Str()
    description = fields.Str()
    product_type_id = fields.Int()


class ProductSchema(ProductSchemaBase):
    """Product schema."""

    report_items = fields.Nested(ReportItemPresentationSchema, many=True)


class ProductPresentationSchema(ProductSchema, ACLEntryStatusSchema, PresentationSchema):
    """Product presentation schema."""

    states = fields.List(fields.Dict(), dump_only=True)
