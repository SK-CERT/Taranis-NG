from marshmallow import Schema, fields, EXCLUDE
from taranisng.schema.presentation import PresentationSchema


class ProductTypeSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int()
    title = fields.Str()
    description = fields.Str()
    presenter_id = fields.Str()


class ProductTypePresentationSchema(ProductTypeSchema, PresentationSchema):
    pass
