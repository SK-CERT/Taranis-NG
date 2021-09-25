from managers.db_manager import db
from taranisng.schema import parameter
from marshmallow import post_load


class NewParameterSchema(parameter.ParameterSchema):

    @post_load
    def make_parameter(self, data, **kwargs):
        return Parameter(**data)


class Parameter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.String(1024))
    type = db.Column(db.Enum(parameter.ParameterType))

    def __init__(self, id, key, name, description, type):
        self.key = key
        self.name = name
        self.description = description
        self.type = type
