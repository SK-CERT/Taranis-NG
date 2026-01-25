"""Product schema module."""

from marshmallow import EXCLUDE, Schema, fields

from shared.schema.acl_entry import ACLEntryStatusSchema
from shared.schema.presentation import PresentationSchema
from shared.schema.report_item import ReportItemPresentationSchema
from shared.schema.state import StateDefinitionSchema
from shared.schema.user import UserSchemaBase


class ProductSchemaBase(Schema):
    """Base product schema."""

    class Meta:
        """Meta class."""

        unknown = EXCLUDE

    id = fields.Int()
    title = fields.Str()
    description = fields.Str()
    created = fields.DateTime("%d.%m.%Y - %H:%M")
    last_updated = fields.DateTime("%d.%m.%Y - %H:%M")
    product_type_id = fields.Int()
    state_id = fields.Int(allow_none=True)


class ProductSchema(ProductSchemaBase):
    """Product schema."""

    report_items = fields.Nested(ReportItemPresentationSchema, many=True)


class ProductPresentationSchema(ProductSchema, ACLEntryStatusSchema, PresentationSchema):
    """Product presentation schema.

    Attributes:
        state: State associated with the product.
        report_items_count: The count of report items in this product.
        user: User who created the product.
        updated_by: User who last updated the product.
    """

    state = fields.Nested(StateDefinitionSchema, allow_none=True)
    report_items_count = fields.Int()
    user = fields.Nested(UserSchemaBase, allow_none=True)
    updated_by = fields.Nested(UserSchemaBase, allow_none=True)
