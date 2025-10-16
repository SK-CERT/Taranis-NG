"""This module contains schemas and classes for user."""

from marshmallow import EXCLUDE, Schema, fields, post_load

from shared.schema.organization import OrganizationSchema
from shared.schema.presentation import PresentationSchema
from shared.schema.role import PermissionSchema, RoleSchema


class User:
    """User model class."""

    def __init__(self, username: str, name: str, password: str, permissions: list) -> None:
        """Initialize a User instance."""
        self.username = username
        self.name = name
        self.password = password
        self.permissions = permissions


class UserSchemaBase(Schema):
    """Base schema for User with common fields."""

    class Meta:
        """Meta class for configuring the behavior of the schema."""

        unknown = EXCLUDE

    id = fields.Int()
    username = fields.Str()
    name = fields.Str()
    password = fields.Str()


class UserSchema(UserSchemaBase):
    """Schema for User with nested roles, permissions, and organizations."""

    roles = fields.Nested(RoleSchema, many=True)
    permissions = fields.Nested(PermissionSchema, many=True)
    organizations = fields.Nested(OrganizationSchema, many=True)

    @post_load
    def make(self, data: dict, **kwargs) -> User:  # noqa: ANN003, ARG002
        """Post-load processing to create a User instance."""
        return User(**data)


class UserPresentationSchema(UserSchema, PresentationSchema):
    """Schema for User with presentation details."""


class UserId:
    """UserId model class."""

    def __init__(
        self,
        id: int,  # noqa: A002
    ) -> None:
        """Initialize a UserId instance."""
        self.id = id


class UserIdSchema(Schema):
    """Schema for User ID."""

    class Meta:
        """Meta class for configuring the behavior of the schema."""

        unknown = EXCLUDE

    id = fields.Int()

    @post_load
    def make(self, data: dict, **kwargs) -> UserId:  # noqa: ANN003, ARG002
        """Post-load processing to create a UserId instance."""
        return UserId(**data)


class HotkeySchema(Schema):
    """Schema for Hotkey."""

    class Meta:
        """Meta class for configuring the behavior of the schema."""

        unknown = EXCLUDE

    key = fields.Str(load_default=None, allow_none=True)
    alias = fields.Str()
