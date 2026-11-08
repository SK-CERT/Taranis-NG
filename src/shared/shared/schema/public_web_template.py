"""Public web report template schemas."""

from marshmallow import EXCLUDE, Schema, fields

from shared.schema.presentation import PresentationSchema


class PublicWebTemplateSchema(Schema):
    """A report template of the public web.

    Exactly one of ``product_preset_id`` (a template for the page, homepage entry and RSS
    text of a product preset's products) and ``report_item_type_id`` (a template for one
    report item block) is set. ``public_web_ids`` lists the webs it applies to; none: every web.
    """

    class Meta:  # ty: ignore[invalid-attribute-override]
        """Meta class."""

        unknown = EXCLUDE

    id = fields.Int(load_default=-1, allow_none=True)
    name = fields.Str(load_default="")
    product_preset_id = fields.Int(load_default=None, allow_none=True)
    report_item_type_id = fields.Int(load_default=None, allow_none=True)
    source = fields.Str(load_default="")
    # Product templates only: whether a product without any TLP may be shown.
    require_tlp_clear = fields.Bool(load_default=True)
    public_web_ids = fields.List(fields.Int(), load_default=list)
    updated_at = fields.DateTime("%d.%m.%Y - %H:%M", dump_only=True)
    updated_by = fields.Str(dump_only=True, allow_none=True)


class PublicWebTemplatePresentationSchema(PublicWebTemplateSchema, PresentationSchema):
    """A report template as the configuration list shows it.

    Attributes:
        target_title: The name of the product preset or report item type it is for.
        web_names: The names of the webs it applies to; none: every web.
    """

    target_title = fields.Str(dump_only=True, allow_none=True)
    web_names = fields.List(fields.Str(), dump_only=True)
