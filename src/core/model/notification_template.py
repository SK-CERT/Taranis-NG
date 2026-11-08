"""Module for NotificationTemplate model."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

from managers.db_manager import db
from marshmallow import fields, post_load
from shared.schema.notification_template import EmailRecipientSchema, NotificationTemplatePresentationSchema, NotificationTemplateSchema
from sqlalchemy import or_, orm

if TYPE_CHECKING:
    from model.organization import Organization
    from model.user import User


class NewEmailRecipientSchema(EmailRecipientSchema):
    """This class represents a schema for creating a new email recipient.

    Attributes:
        Inherits EmailRecipientSchema.

    Returns:
        An instance of EmailRecipient.
    """

    @post_load
    def make(self, data: dict, **kwargs) -> EmailRecipient:  # noqa: ARG002, ANN003
        """Create an instance of EmailRecipient using the provided data.

        Args:
            data (dict): A dictionary containing the data for creating the EmailRecipient instance.
            **kwargs: Additional keyword arguments.

        Returns:
            EmailRecipient: An instance of EmailRecipient created using the provided data.
        """
        return EmailRecipient(**data)


class EmailRecipient(db.Model):
    """Represents an email recipient.

    Attributes:
        id (int): The unique identifier of the recipient.
        email (str): The email address of the recipient.
        name (str): The name of the recipient.
        notification_template_id (int): The ID of the associated notification template.
    """

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(), nullable=False)
    name = db.Column(db.String())

    notification_template_id = db.Column(db.Integer, db.ForeignKey("notification_template.id"))

    def __init__(self, email: str, name: str | None) -> None:
        """Initialize a NotificationTemplate object."""
        self.id = None
        self.email = email
        self.name = name


class NewNotificationTemplateSchema(NotificationTemplateSchema):
    """NewNotificationTemplateSchema class is a schema for creating a new notification template.

    Attributes:
        recipients (list): A list of NewEmailRecipientSchema objects representing the recipients of the notification.
    """

    recipients = fields.Nested(NewEmailRecipientSchema, many=True)

    @post_load
    def make(self, data: dict, **kwargs) -> NotificationTemplate:  # noqa: ARG002, ANN003
        """Create a new `NotificationTemplate` object based on the given data.

        Args:
            data (dict): A dictionary containing the data for the notification template.
            **kwargs: Additional keyword arguments.

        Returns:
            NotificationTemplate: A new `NotificationTemplate` object.
        """
        return NotificationTemplate(**data)


class NotificationTemplate(db.Model):
    """NotificationTemplate class represents a template for notifications.

    Attributes:
        id (int): The unique identifier of the template.
        name (str): The name of the template.
        description (str): The description of the template.
        message_title (str): The title of the notification message.
        message_body (str): The body of the notification message.
        recipients (list): The list of email recipients for the notification.
        organizations (list): The list of organizations associated with the template.
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    message_title = db.Column(db.String())
    message_body = db.Column(db.String())

    recipients = db.relationship("EmailRecipient", cascade="all, delete-orphan")

    organizations = db.relationship("Organization", secondary="notification_template_organization")

    def __init__(
        self,
        id: int | None,  # noqa: A002, ARG002
        name: str,
        description: str | None,
        message_title: str | None,
        message_body: str | None,
        recipients: list[EmailRecipient],
    ) -> None:
        """Initialize a NotificationTemplate object."""
        self.id = None
        self.name = name
        self.description = description
        self.message_title = message_title
        self.message_body = message_body
        self.recipients = recipients
        self.title = ""
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self) -> None:
        """Reconstruct the notification template."""
        self.title = self.name
        self.subtitle = self.description
        self.tag = "mdi-email-outline"

    @classmethod
    def find(cls, template_id: int) -> NotificationTemplate | None:
        """Find a notification template by its ID.

        Args:
            cls: The class object.
            template_id: The ID of the notification template.

        Returns:
            The notification template with the specified ID, or None.
        """
        return db.session.get(cls, template_id)

    @classmethod
    def get(cls, search: str | None, organization: Organization | None) -> tuple[list[NotificationTemplate], int]:
        """Retrieve notification templates based on search criteria and organization.

        Args:
            search (str): The search string to filter notification templates by name or description.
            organization (str): The organization to filter notification templates.

        Returns:
            tuple: A tuple containing:
                A list of notification templates matching the search criteria and organization.
                The count of notification templates matching the search criteria and organization.
        """
        query = cls.query

        if organization is not None:
            query = query.join(
                NotificationTemplateOrganization,
                NotificationTemplate.id == NotificationTemplateOrganization.notification_template_id,
            )

        if search is not None:
            search_string = f"%{search}%"
            query = query.filter(
                or_(
                    NotificationTemplate.name.ilike(search_string),
                    NotificationTemplate.description.ilike(search_string),
                ),
            )

        return query.order_by(db.asc(NotificationTemplate.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, user: User, search: str | None) -> dict:
        """Retrieve all notification templates in JSON format.

        Args:
            cls (class): The class itself.
            user (User): The user object.
            search (str): The search query.

        Returns:
            dict: A dictionary containing the total count and a list of template items in JSON format.
        """
        if user.organizations:
            templates, count = cls.get(search, user.organizations[0])
        else:
            return {"total_count": 0, "items": []}
        template_schema = NotificationTemplatePresentationSchema(many=True)
        return {"total_count": count, "items": template_schema.dump(templates)}

    @classmethod
    def add(cls, user: User, data: dict) -> None:
        """Add a new notification template to the database.

        Args:
            cls: The class object.
            user: The user object.
            data: The data for the new notification template.
        """
        new_template_schema = NewNotificationTemplateSchema()
        template = new_template_schema.load(data)
        template.organizations = user.organizations
        db.session.add(template)
        db.session.commit()

    @classmethod
    def delete(cls, user: User, template_id: int) -> tuple[dict, HTTPStatus] | None:
        """Delete a notification template.

        Args:
            cls (class): The class itself.
            user (User): The user performing the delete operation.
            template_id (int): The ID of the template to be deleted.
        """
        template = db.session.get(cls, template_id)
        if template is None:
            return {"error": "Notification template not found"}, HTTPStatus.NOT_FOUND
        if any(org in user.organizations for org in template.organizations):
            db.session.delete(template)
            db.session.commit()
        return None

    @classmethod
    def update(cls, user: User, template_id: int, data: dict) -> tuple[dict, HTTPStatus] | None:
        """Update a notification template.

        Args:
            cls: The class object.
            user: The user performing the update.
            template_id: The ID of the template to update.
            data: The updated template data.
        """
        new_template_schema = NewNotificationTemplateSchema()
        updated_template = new_template_schema.load(data)
        template = db.session.get(cls, template_id)
        if template is None:
            return {"error": "Notification template not found"}, HTTPStatus.NOT_FOUND
        if any(org in user.organizations for org in template.organizations):
            template.name = updated_template.name
            template.description = updated_template.description
            template.message_title = updated_template.message_title
            template.message_body = updated_template.message_body
            template.recipients = updated_template.recipients
            db.session.commit()
        return None


class NotificationTemplateOrganization(db.Model):
    """Model class representing the association table between NotificationTemplate and Organization.

    Attributes:
        notification_template_id (int): The ID of the notification template.
        organization_id (int): The ID of the organization.
    """

    notification_template_id = db.Column(db.Integer, db.ForeignKey("notification_template.id"), primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organization.id"), primary_key=True)
