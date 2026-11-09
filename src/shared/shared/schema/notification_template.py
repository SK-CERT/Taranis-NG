"""This module contains schemas and classes for notification templates."""

from marshmallow import EXCLUDE, Schema, fields, post_load

from shared.schema.presentation import PresentationSchema


class EmailRecipientSchema(Schema):
    """Schema for an email recipient of a notification template."""

    class Meta:  # ty: ignore[invalid-attribute-override]
        """Meta class for configuring the behavior of the schema."""

        unknown = EXCLUDE

    id = fields.Int()
    email = fields.Str()
    name = fields.Str()


class NotificationTemplateSchema(Schema):
    """Schema for Notification template."""

    class Meta:  # ty: ignore[invalid-attribute-override]
        """Meta class for configuring the behavior of the schema."""

        unknown = EXCLUDE

    id = fields.Int()
    name = fields.Str()
    description = fields.Str()
    message_title = fields.Str()
    message_body = fields.Str()


class NotificationTemplatePresentationSchema(NotificationTemplateSchema, PresentationSchema):
    """Schema for Notification template with presentation data and its recipients."""

    recipients = fields.Nested(EmailRecipientSchema, many=True)


class NotificationTemplateIdSchema(Schema):
    """Schema for a notification template id."""

    class Meta:  # ty: ignore[invalid-attribute-override]
        """Meta class for configuring the behavior of the schema."""

        unknown = EXCLUDE

    id = fields.Int()

    @post_load
    def make(self, data: dict, **kwargs) -> "NotificationTemplateId":  # noqa: ANN003, ARG002
        """Create a NotificationTemplateId instance from deserialized data."""
        return NotificationTemplateId(**data)


class NotificationTemplateId:
    """Wrapper class holding a notification template id."""

    def __init__(self, id: int) -> None:  # noqa: A002
        """Initialize a NotificationTemplateId instance."""
        self.id = id
