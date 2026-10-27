"""Schema for Product Type, used for serialization and deserialization of product type data."""

from marshmallow import EXCLUDE, Schema, fields

from shared.schema.parameter_value import ParameterValueSchema
from shared.schema.presentation import PresentationSchema


class ProductTypeSchema(Schema):
    """Schema for Product Type, used for serialization and deserialization of product type data.

    Attributes:
        id (int): Unique identifier for the product type.
        title (str): Title of the product type.
        description (str): Description of the product type.
        presenter_id (str): Identifier for the presenter associated with the product type.
        parameter_values (list): List of parameter values associated with the product type.
        language (str): Language its default templates are written in, if stated.
        language_templates (dict): Template paths per language, ``{language: {PARAM_TEMPLATE_PATH: path}}``.
    """

    class Meta:
        """Meta class to define schema behavior."""

        unknown = EXCLUDE

    id = fields.Int()
    title = fields.Str()
    description = fields.Str()
    presenter_id = fields.Str()
    parameter_values = fields.List(fields.Nested(ParameterValueSchema))
    # The language of the default templates, and template paths per language.
    language = fields.Str(allow_none=True, load_default=None)
    language_templates = fields.Dict(load_default=dict)


class ProductTypePresentationSchema(ProductTypeSchema, PresentationSchema):
    """Schema for Product Type with presentation details, extending ProductTypeSchema and PresentationSchema."""

    presenter_name = fields.Function(lambda obj: obj.presenter.name if obj.presenter else None)
