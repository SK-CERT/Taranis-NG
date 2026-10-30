"""This module defines classes and schemas for handling parameters and their serialization/deserialization."""

from enum import Enum, auto

from marshmallow import Schema, fields, post_load


class ParameterType(Enum):
    """Enum class representing different types of parameters.

    Attributes:
        STRING (auto): Represents a string parameter type.
        NUMBER (auto): Represents a numeric parameter type.
        BOOLEAN (auto): Represents a boolean parameter type.
        LIST (auto): Represents a list parameter type.
    """

    STRING = auto()
    NUMBER = auto()
    BOOLEAN = auto()
    LIST = auto()


class Parameter:
    """A class used to represent a Parameter."""

    def __init__(
        self,
        id: int,  # noqa: A002
        key: str,
        name: str,
        description: str,
        type: ParameterType,  # noqa: A002
        default_value: str,
        translate: bool = False,
    ) -> None:
        """Initialize a new Parameter instance.

        Args:
            id (int): The unique identifier for the parameter.
            key (str): The key associated with the parameter.
            name (str): The name of the parameter.
            description (str): A brief description of the parameter.
            type (ParameterType): The type of the parameter.
            default_value (str): The default value for the parameter.
            translate (bool): Whether the parameter is translatable.
        """
        self.id = id
        self.key = key
        self.name = name
        self.description = description
        self.type = type
        self.default_value = default_value
        self.translate = translate


class ParameterSchema(Schema):
    """ParameterSchema is a Marshmallow schema for serializing and deserializing Parameter objects.

    Attributes:
        id (fields.Int): The unique identifier of the parameter.
        key (fields.Str): The key associated with the parameter.
        name (fields.Str): The name of the parameter.
        description (fields.Str): A brief description of the parameter.
        type (fields.Enum): The type of the parameter, which is an enumeration of ParameterType.
        default_value (fields.Str): Default value.
        translate (fields.Bool): Whether the parameter is translatable.

    Methods:
        make_parameter(data, **kwargs):
            Creates a Parameter instance from the deserialized data.
    """

    id = fields.Int()
    key = fields.Str()
    name = fields.Str()
    description = fields.Str()
    type = fields.Enum(ParameterType)
    default_value = fields.Str(allow_none=True)
    translate = fields.Bool(load_default=False)

    @post_load
    def make_parameter(self, data: dict, **kwargs) -> Parameter:  # noqa: ANN003, ARG002
        """Create a Parameter instance from the provided data.

        Args:
            data (dict): A dictionary containing the data to initialize the Parameter instance.
            **kwargs: Additional keyword arguments.

        Returns:
            Parameter: An instance of the Parameter class initialized with the provided data.
        """
        return Parameter(**data)


class ParameterExport:
    """A class used to represent a Parameter Export.

    Args:
        key (str): The key associated with the parameter export.

    Methods:
        __init__(self, key): Initializes the ParameterExport with the given key.
    """

    def __init__(self, key: str) -> None:
        """Initialize a Parameter instance with a given key.

        Args:
            key (str): The key associated with the parameter.
        """
        self.key = key


class ParameterExportSchema(Schema):
    """Schema for exporting parameters.

    Attributes:
        key (str): The key of the parameter.

    Methods:
        make(data, **kwargs):
            Creates a ParameterExport instance from the loaded data.
    """

    key = fields.Str()

    @post_load
    def make(self, data: dict, **kwargs) -> ParameterExport:  # noqa: ANN003, ARG002
        """Create a ParameterExport instance from the provided data.

        Args:
            data (dict): A dictionary containing the data to initialize the ParameterExport instance.
            **kwargs: Additional keyword arguments.

        Returns:
            ParameterExport: An instance of ParameterExport initialized with the provided data.
        """
        return ParameterExport(**data)
