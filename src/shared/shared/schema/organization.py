"""This module contains schemas and classes for organization."""

from marshmallow import EXCLUDE, Schema, fields, post_load

from shared.schema.address import AddressSchema
from shared.schema.presentation import PresentationSchema


class OrganizationSchema(Schema):
    """Schema for Organization."""

    class Meta:
        """Meta class for configuring the behavior of the schema."""

        unknown = EXCLUDE

    id = fields.Int()
    name = fields.Str()
    description = fields.Str()
    require_mfa = fields.Bool(load_default=False)
    address = fields.Nested(AddressSchema)


class OrganizationPresentationSchema(OrganizationSchema, PresentationSchema):
    """Schema for Organization with presentation data."""


class OrganizationIdSchema(Schema):
    """Schema for an organization id."""

    class Meta:
        """Meta class for configuring the behavior of the schema."""

        unknown = EXCLUDE

    id = fields.Int()

    @post_load
    def make(self, data: dict, **kwargs) -> "OrganizationId":  # noqa: ANN003, ARG002
        """Create an OrganizationId instance from deserialized data."""
        return OrganizationId(**data)


class OrganizationId:
    """Wrapper class holding an organization id."""

    def __init__(self, id: int) -> None:  # noqa: A002
        """Initialize an OrganizationId instance."""
        self.id = id
