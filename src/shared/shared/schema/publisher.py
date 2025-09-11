"""Schema for Publisher and Publisher Input."""

from marshmallow import Schema, fields, post_load

from shared.schema.parameter import ParameterSchema
from shared.schema.parameter_value import ParameterValueSchema


class PublisherSchema(Schema):
    """Schema for Publisher."""

    id = fields.Str()
    type = fields.Str()
    name = fields.Str()
    description = fields.Str()
    parameters = fields.List(fields.Nested(ParameterSchema))


class PublisherInput:
    """Publisher Input class."""

    def __init__(
        self,
        name: str,
        type: str,  # noqa: A002
        parameter_values: list,
        mime_type: str,
        data: str,
        message_title: str,
        message_body: str,
        recipients: list,
        att_file_name: str,
    ) -> None:
        """Initialize the PublisherInput object.

        Args:
            name (str): The name of the publisher.
            type (str): The type of the publisher.
            parameter_values (list): The list of parameter values.
            mime_type (str): The MIME type of the data.
            data (str): The data to be published.
            message_title (str): The title of the message.
            message_body (str): The body of the message.
            recipients (list): The list of recipients.
            att_file_name (str): The attachment file name.
        """
        self.name = name
        self.type = type
        self.parameter_values = parameter_values
        self.mime_type = mime_type
        self.data = data
        self.message_title = message_title
        self.message_body = message_body
        self.recipients = recipients
        self.att_file_name = att_file_name

        self.param_key_values = {}
        for pv in parameter_values:
            self.param_key_values.update({pv.parameter.key: pv.value})


class PublisherInputSchema(Schema):
    """Schema for Publisher Input."""

    name = fields.Str()
    type = fields.Str()
    parameter_values = fields.List(fields.Nested(ParameterValueSchema))
    mime_type = fields.Str(allow_none=True)
    data = fields.Str(allow_none=True)
    message_title = fields.Str(allow_none=True)
    message_body = fields.Str(allow_none=True)
    recipients = fields.List(fields.String, allow_none=True)
    att_file_name = fields.Str(allow_none=True)

    @post_load
    def make(self, data: dict, **kwargs) -> PublisherInput:  # noqa: ANN003, ARG002
        """Create a PublisherInput object from the deserialized data.

        Args:
            data (dict): The deserialized data.
            **kwargs: Additional arguments.

        Returns:
            PublisherInput: The PublisherInput object.
        """
        return PublisherInput(**data)
