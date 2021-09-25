from marshmallow import Schema, fields
from taranisng.schema import parameter


class BotSchema(Schema):
    id = fields.Str()
    type = fields.Str()
    name = fields.Str()
    description = fields.Str()
    parameters = fields.List(fields.Nested(parameter.ParameterSchema))
