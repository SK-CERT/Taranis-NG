"""Module for defining attribute classes and schemas.

This module contains classes and schemas related to attributes, including enums, validators, and presentation information.
"""

from marshmallow import Schema, fields, post_load, EXCLUDE
from marshmallow_enum import EnumField
from enum import Enum, auto

from shared.schema.presentation import PresentationSchema


class AttributeType(Enum):
    """Enum class representing the types of attributes."""

    STRING = auto()
    NUMBER = auto()
    BOOLEAN = auto()
    RADIO = auto()
    ENUM = auto()
    TEXT = auto()
    RICH_TEXT = auto()
    DATE = auto()
    TIME = auto()
    DATE_TIME = auto()
    LINK = auto()
    ATTACHMENT = auto()
    TLP = auto()
    CPE = auto()
    CVE = auto()
    CVSS = auto()
    CWE = auto()


class AttributeValidator(Enum):
    """Enum class representing the validators for attributes."""

    NONE = auto()
    EMAIL = auto()
    NUMBER = auto()
    RANGE = auto()
    REGEXP = auto()


class AttributeEnumSchema(Schema):
    """
    Schema class for attribute enums.

    This schema defines the structure for attribute enums.
    It includes fields for id, index, value, and description.
    """

    class Meta:
        """Meta class for defining options in the attribute schema."""

        unknown = EXCLUDE

    id = fields.Integer(load_default=-1)
    index = fields.Integer(load_default=-1)
    value = fields.Str()
    description = fields.Str()

    @post_load
    def make_attribute_enum(self, data, **kwargs):
        """Create an AttributeEnum object from the loaded data."""
        return AttributeEnum(**data)


class AttributeEnum:
    """Class representing an attribute enum."""

    def __init__(self, index, value, description):
        """
        Initialize an Attribute object.

        Args:
            index (int): The index of the attribute.
            value (str): The value of the attribute.
            description (str): The description of the attribute.
        """
        self.index = index
        self.value = value
        self.description = description


class AttributeBaseSchema(Schema):
    """Base schema class for attributes."""

    class Meta:
        """Meta class for defining options for the attribute schema."""

        unknown = EXCLUDE

    id = fields.Int()
    name = fields.Str()
    description = fields.Str(allow_none=True)
    type = EnumField(AttributeType)
    default_value = fields.Str(allow_none=True)
    validator = EnumField(AttributeValidator, allow_none=True)
    validator_parameter = fields.Str(allow_none=True)

    @post_load
    def make_attribute(self, data, **kwargs):
        """Create an Attribute object from the loaded data."""
        return Attribute(**data)


class AttributeSchema(AttributeBaseSchema):
    """Schema class for attributes."""

    attribute_enums = fields.Nested(AttributeEnumSchema, many=True)


class AttributePresentationSchema(AttributeSchema, PresentationSchema):
    """Schema class for attributes with presentation information."""

    attribute_enums_total_count = fields.Int()


class Attribute:
    """Class representing an attribute."""

    def __init__(self, id, name, description, type, default_value, validator, validator_parameter):
        """
        Initialize an Attribute object.

        Args:
            id (int): The ID of the attribute.
            name (str): The name of the attribute.
            description (str): The description of the attribute.
            type (str): The type of the attribute.
            default_value: The default value of the attribute.
            validator: The validator function for the attribute.
            validator_parameter: The parameter for the validator function.

        Returns:
            None
        """
        self.id = id
        self.name = name
        self.description = description
        self.type = type
        self.default_value = default_value
        self.validator = validator
        self.validator_parameter = validator_parameter
