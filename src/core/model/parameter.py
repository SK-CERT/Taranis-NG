"""Parameter Model."""

from marshmallow import post_load

from managers.db_manager import db
from shared.schema.parameter import ParameterType, ParameterSchema


class NewParameterSchema(ParameterSchema):
    """New Parameter Schema."""

    @post_load
    def make_parameter(self, data, **kwargs):
        """Make parameter.

        Args:
            data (dict): Data to create parameter.
        Returns:
            Parameter: Created parameter.
        """
        return Parameter(**data)


class Parameter(db.Model):
    """Parameter Model.

    Attributes:
        id (int): Identifier.
        key (str): Key of parameter.
        name (str): Name of parameter.
        description (str): Description of parameter.
        type (ParameterType): Type of parameter.
        default_value (str): Default value.
    """

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(), nullable=False)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    type = db.Column(db.Enum(ParameterType))
    default_value = db.Column(db.String(), nullable=True)

    def __init__(self, key, name, description, type, default_value):
        """Initialize Parameter Model."""
        self.key = key
        self.name = name
        self.description = description
        self.type = type
        self.default_value = default_value
