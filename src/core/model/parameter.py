"""Parameter Model."""

from marshmallow import post_load

from managers.db_manager import db
from shared.schema.parameter import ParameterType, ParameterSchema


class NewParameterSchema(ParameterSchema):
    """XXX_2069."""

    @post_load
    def make_parameter(self, data, **kwargs):
        """XXX_2069."""
        return Parameter(**data)


class Parameter(db.Model):
    """XXX_2069."""

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(), nullable=False)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    type = db.Column(db.Enum(ParameterType))

    def __init__(self, key, name, description, type):
        """XXX_2069."""
        self.key = key
        self.name = name
        self.description = description
        self.type = type
