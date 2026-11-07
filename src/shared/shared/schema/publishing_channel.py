"""Schema for Publishing Channel, used for serialization and deserialization of publishing channel data."""

from __future__ import annotations

from marshmallow import EXCLUDE, Schema, fields, post_load

from shared.schema.parameter_value import ParameterValueSchema
from shared.schema.presentation import PresentationSchema


class PublishingChannelSchemaBase(Schema):
    """Base schema for Publishing Channel, used for serialization and deserialization.

    Attributes:
        id (str): Unique identifier for the publishing channel.
        name (str): Name of the publishing channel.
        parameter_values (list): List of parameter values associated with the publishing channel.
    """

    class Meta:
        """Meta class to define schema behavior."""

        unknown = EXCLUDE

    id = fields.Str()
    name = fields.Str()
    parameter_values = fields.List(fields.Nested(ParameterValueSchema))

    @post_load
    def make(self, data: dict, **kwargs) -> PublishingChannel:  # noqa: ARG002, ANN003
        """Create a PublishingChannel instance from the deserialized data.

        Args:
            data: The deserialized data.
            **kwargs: Additional arguments.

        Returns:
            PublishingChannel: The channel.
        """
        return PublishingChannel(**data)


class PublishingChannelSchema(PublishingChannelSchemaBase):
    """Schema for Publishing Channel, used for serialization and deserialization.

    Attributes:
        id (str): Unique identifier for the publishing channel.
        name (str): Name of the publishing channel.
        description (str): Description of the publishing channel.
        use_for_notifications (bool): Flag indicating if the channel is used for notifications.
        publisher_id (str): Identifier for the associated publisher.
        parameter_values (list): List of parameter values associated with the publishing channel.
    """

    id = fields.Str()
    name = fields.Str()
    description = fields.Str()
    use_for_notifications = fields.Bool()
    publisher_id = fields.Str()
    parameter_values = fields.List(fields.Nested(ParameterValueSchema))


class PublishingChannelPresentationSchema(PublishingChannelSchema, PresentationSchema):
    """Presentation schema for Publishing Channel, extending the base schema with presentation features."""

    item_name = fields.Function(lambda obj: obj.publisher.name if obj.publisher else None)


class PublishingChannel:
    """Class representing a Publishing Channel with its properties and parameter values."""

    def __init__(self, id: str, name: str, parameter_values: list) -> None:  # noqa: A002
        """Initialize a PublishingChannel instance.

        Args:
            id (str): Unique identifier for the publishing channel.
            name (str): Name of the publishing channel.
            parameter_values (list): List of parameter values associated with the publishing channel.
        """
        self.id = id
        self.name = name

        # Is it even used? Looks like it's never called due to being overridden. If it's used, shouldn't the name be param_key_values instead?
        self.parameter_values = {}
        for parameter_value in parameter_values:
            self.parameter_values.update({parameter_value.parameter.key: parameter_value.value})
