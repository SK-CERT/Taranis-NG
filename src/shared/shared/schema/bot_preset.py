"""Schema for Bot preset, used for serialization and deserialization of bot preset data."""

from marshmallow import Schema, fields, post_load, EXCLUDE

from shared.schema.parameter_value import ParameterValueSchema
from shared.schema.presentation import PresentationSchema


class BotPresetSchemaBase(Schema):
    """Base schema for Bot Preset, used for serialization and deserialization of bot preset data.

    Attributes:
        id (str): Unique identifier for the bot preset.
        name (str): Name of the bot preset.
        parameter_values (list): List of parameter values associated with the bot preset.
    """

    class Meta:
        """Meta class to define schema behavior."""

        unknown = EXCLUDE

    id = fields.Str()
    name = fields.Str()
    parameter_values = fields.List(fields.Nested(ParameterValueSchema))

    @post_load
    def make(self, data, **kwargs):
        """Create a BotPreset instance from the deserialized data.

        Args:
            data (dict): The deserialized data containing bot preset attributes.
            **kwargs: Additional keyword arguments.
        Returns:
            BotPreset: An instance of BotPreset initialized with the provided data.
        """
        return BotPreset(**data)


class BotPresetSchema(BotPresetSchemaBase):
    """Schema for Bot Preset, extending the base schema with additional fields.

    Attributes:
        id (str): Unique identifier for the bot preset.
        name (str): Name of the bot preset.
        description (str): Description of the bot preset.
        bot_id (str): Identifier for the associated bot.
        parameter_values (list): List of parameter values associated with the bot preset.
    """

    id = fields.Str()
    name = fields.Str()
    description = fields.Str()
    bot_id = fields.Str()
    parameter_values = fields.List(fields.Nested(ParameterValueSchema))


class BotPresetPresentationSchema(BotPresetSchema, PresentationSchema):
    """Schema for Bot Preset with presentation details, extending BotPresetSchema and PresentationSchema."""

    item_name = fields.Function(lambda obj: obj.bot.name if obj.bot else None)


class BotPreset:
    """Class representing a Bot Preset, containing its ID, name, and parameter values."""

    def __init__(self, id, name, parameter_values):
        """Initialize a BotPreset instance with ID, name, and parameter values.

        Args:
            id (str): Unique identifier for the bot preset.
            name (str): Name of the bot preset.
            parameter_values (list): List of parameter values associated with the bot preset.
        """
        self.id = id
        self.name = name

        self.param_key_values = dict()
        for pv in parameter_values:
            self.param_key_values.update({pv.parameter.key: pv.value})
