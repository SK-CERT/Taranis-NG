"""This module contains schemas and classes for roles and permissions."""

from marshmallow import EXCLUDE, Schema, fields, post_load

from shared.schema.presentation import PresentationSchema


class PermissionSchema(Schema):
    """Schema for Permission."""

    id = fields.Str()
    name = fields.Str()
    description = fields.Str()


class PermissionIdSchema(Schema):
    """Schema for a permission id."""

    class Meta:  # ty: ignore[invalid-attribute-override]
        """Meta class for configuring the behavior of the schema."""

        unknown = EXCLUDE

    id = fields.Str()

    @post_load
    def make(self, data: dict, **kwargs) -> "PermissionId":  # noqa: ANN003, ARG002
        """Create a PermissionId instance from deserialized data."""
        return PermissionId(**data)


class PermissionId:
    """Wrapper class holding a permission id."""

    def __init__(self, id: str) -> None:  # noqa: A002
        """Initialize a PermissionId instance."""
        self.id = id


class RoleSchemaBase(Schema):
    """Base schema for Role."""

    class Meta:  # ty: ignore[invalid-attribute-override]
        """Meta class for configuring the behavior of the schema."""

        unknown = EXCLUDE

    id = fields.Str()
    name = fields.Str()
    description = fields.Str()


class RoleSchema(RoleSchemaBase):
    """Schema for Role with its permissions."""

    permissions = fields.Nested(PermissionSchema, many=True)


class RolePresentationSchema(RoleSchema, PresentationSchema):
    """Schema for Role with presentation data."""


class RoleIdSchema(Schema):
    """Schema for a role id."""

    class Meta:  # ty: ignore[invalid-attribute-override]
        """Meta class for configuring the behavior of the schema."""

        unknown = EXCLUDE

    id = fields.Str()

    @post_load
    def make(self, data: dict, **kwargs) -> "RoleId":  # noqa: ANN003, ARG002
        """Create a RoleId instance from deserialized data."""
        return RoleId(**data)


class RoleId:
    """Wrapper class holding a role id."""

    def __init__(self, id: str) -> None:  # noqa: A002
        """Initialize a RoleId instance."""
        self.id = id
