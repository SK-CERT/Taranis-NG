"""Schema for Publisher Preset, used for serialization and deserialization of publisher preset data."""

from marshmallow import EXCLUDE, Schema, fields, post_load

from shared.schema.parameter_value import ParameterValueSchema
from shared.schema.presentation import PresentationSchema


class PublisherPresetSchemaBase(Schema):
    """Base schema for Publisher Preset, used for serialization and deserialization.

    Attributes:
        id (str): Unique identifier for the publisher preset.
        name (str): Name of the publisher preset.
        parameter_values (list): List of parameter values associated with the publisher preset.
    """

    class Meta:
        """Meta class to define schema behavior."""

        unknown = EXCLUDE

    id = fields.Str()
    name = fields.Str()
    parameter_values = fields.List(fields.Nested(ParameterValueSchema))

    @post_load
    def make(self, data, **kwargs):
        """Create a PublisherPreset instance from the deserialized data."""
        return PublisherPreset(**data)


class PublisherPresetSchema(PublisherPresetSchemaBase):
    """Schema for Publisher Preset, used for serialization and deserialization.

    Attributes:
        id (str): Unique identifier for the publisher preset.
        name (str): Name of the publisher preset.
        description (str): Description of the publisher preset.
        use_for_notifications (bool): Flag indicating if the preset is used for notifications.
        publisher_id (str): Identifier for the associated publisher.
        parameter_values (list): List of parameter values associated with the publisher preset.
    """

    id = fields.Str()
    name = fields.Str()
    description = fields.Str()
    use_for_notifications = fields.Bool()
    publisher_id = fields.Str()
    parameter_values = fields.List(fields.Nested(ParameterValueSchema))


class PublisherPresetPresentationSchema(PublisherPresetSchema, PresentationSchema):
    """Presentation schema for Publisher Preset, extending the base schema with presentation features."""

    item_name = fields.Function(lambda obj: obj.publisher.name if obj.publisher else None)


class PublisherPreset:
    """Class representing a Publisher Preset with its properties and parameter values."""

    def __init__(self, id, name, parameter_values):
        """Initialize a PublisherPreset instance.

        Args:
            id (str): Unique identifier for the publisher preset.
            name (str): Name of the publisher preset.
            parameter_values (list): List of parameter values associated with the publisher preset.
        """
        self.id = id
        self.name = name

        # Is it even used? Looks like it's never called due to being overridden. If it's used, shouldn't the name be param_key_values instead?
        self.parameter_values = dict()
        for parameter_value in parameter_values:
            self.parameter_values.update({parameter_value.parameter.key: parameter_value.value})
