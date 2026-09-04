"""Schema for Publisher and Publisher Input."""

from marshmallow import EXCLUDE, Schema, fields, post_load

from shared.schema.message_header import MessageHeaderSchema
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
        message_body_mime_type: str | None = None,
        message_headers: list | None = None,
    ) -> None:
        """Initialize the PublisherInput object.

        Args:
            name (str): The name of the publisher.
            type (str): The type of the publisher.
            parameter_values (list): The list of parameter values.
            mime_type (str): The MIME type of the data (the attachment, when there is one).
            data (str): The data to be published.
            message_title (str): The title of the message.
            message_body (str): The body of the message.
            recipients (list): The list of recipients.
            att_file_name (str): The attachment file name.
            message_body_mime_type (str | None): MIME type of the message body, as declared by the
                presenter. None when no presenter was involved; publishers should then assume plain text.
            message_headers (list | None): Custom mail headers as {name, value} pairs. Empty when no
                presenter was involved, or when the presenter has no headers template configured.
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
        self.message_body_mime_type = message_body_mime_type
        self.message_headers = message_headers or []

        self.param_key_values = {}
        for pv in parameter_values:
            self.param_key_values.update({pv.parameter.key: pv.value})


class PublisherInputSchema(Schema):
    """Schema for Publisher Input."""

    class Meta:
        """Meta class to define schema behavior.

        Unknown fields are excluded so a core running ahead of a publishers node - they are
        deployed and upgraded separately - does not fail the whole publish on a field this
        version has never heard of.
        """

        unknown = EXCLUDE

    name = fields.Str()
    type = fields.Str()
    parameter_values = fields.List(fields.Nested(ParameterValueSchema))
    mime_type = fields.Str(allow_none=True)
    data = fields.Str(allow_none=True)
    message_title = fields.Str(allow_none=True)
    message_body = fields.Str(allow_none=True)
    recipients = fields.List(fields.String, allow_none=True)
    att_file_name = fields.Str(allow_none=True)
    message_body_mime_type = fields.Str(allow_none=True)
    message_headers = fields.List(fields.Nested(MessageHeaderSchema), allow_none=True)

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
