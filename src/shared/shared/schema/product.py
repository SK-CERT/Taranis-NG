"""Product schema module."""

from marshmallow import EXCLUDE, Schema, fields

from shared.schema.acl_entry import ACLEntryStatusSchema
from shared.schema.link import LinkRefSchema
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
    created = fields.DateTime("%d.%m.%Y - %H:%M")
    updated_at = fields.DateTime("%d.%m.%Y - %H:%M")
    product_type_id = fields.Int()
    state_id = fields.Int(allow_none=True)
    # The language the product is written in (ISO 639-1); None while not set.
    language = fields.Str(allow_none=True, load_default=None)
    public_web_ids = fields.List(fields.Int(), allow_none=True)
    # The product's own sources, in citation order; the description cites them by key.
    links = fields.Nested(LinkRefSchema, many=True, load_default=list)


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
        translations: The title per language, with origin and whether it is outdated.
        title_translations: The title per language, ``{language: {"title": ...}}``.
        tags: The ids of the tags people put on it.
        translation_status: Its title's translation status per language as built-in tag keys,
            or ``{"": "language_not_set"}``.
    """

    state = fields.Nested(StateDefinitionSchema, allow_none=True)
    report_items_count = fields.Int()
    updated_by = fields.Str()
    # Translated titles: with their state for the edit form, and plain for lists.
    translations = fields.Dict(dump_only=True)
    title_translations = fields.Dict(dump_only=True)
    tags = fields.List(fields.Int(), attribute="tag_ids", dump_only=True)
    translation_status = fields.Dict(keys=fields.Str(), values=fields.Str(), dump_only=True)
