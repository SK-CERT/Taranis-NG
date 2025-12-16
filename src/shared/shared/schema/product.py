"""Product schema module."""

from marshmallow import EXCLUDE, Schema, fields

from shared.schema.acl_entry import ACLEntryStatusSchema
from shared.schema.presentation import PresentationSchema
from shared.schema.report_item import ReportItemPresentationSchema
from shared.schema.state import StateDefinitionSchema


class ProductSchemaBase(Schema):
    """Base product schema."""

    class Meta:
        """Meta class."""

        unknown = EXCLUDE

    id = fields.Int()
    title = fields.Str()
    description = fields.Str()
    created = fields.DateTime()
    product_type_id = fields.Int()
    state_id = fields.Int(allow_none=True)


class ProductSchema(ProductSchemaBase):
    """Product schema."""

    report_items = fields.Nested(ReportItemPresentationSchema, many=True)


class ProductPresentationSchema(ProductSchema, ACLEntryStatusSchema, PresentationSchema):
    """Product presentation schema."""

    state = fields.Nested(StateDefinitionSchema, allow_none=True)
