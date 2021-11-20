from marshmallow import Schema, fields

from schema.parameter import ParameterSchema


class CollectorSchema(Schema):
    id = fields.Str()
    type = fields.Str()
    name = fields.Str()
    description = fields.Str()
    parameters = fields.List(fields.Nested(ParameterSchema))
