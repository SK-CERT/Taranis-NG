"""Schemas and transfer object for API keys with UTC timestamps."""

from __future__ import annotations

from typing import TYPE_CHECKING

from marshmallow import EXCLUDE, Schema, fields, post_load

from shared.schema.datetime import UTCDateTime
from shared.schema.user import UserSchemaBase

if TYPE_CHECKING:
    from datetime import datetime
    from typing import Any


class ApiKeyBaseSchema(Schema):
    """Describe API key fields shared by transfer and persistence schemas."""

    class Meta:
        """Ignore fields that are not part of the API key contract."""

        unknown = EXCLUDE

    id = fields.Int()
    name = fields.Str()
    key = fields.Str()  # length 40
    created_at = UTCDateTime(load_default=None, allow_none=True)
    user_id = fields.Int(load_default=None, allow_none=True)
    expires_at = UTCDateTime(load_default=None, allow_none=True)


class ApiKeySchema(ApiKeyBaseSchema):
    """Include the owner's public user details when serializing an API key."""

    user = fields.Nested(UserSchemaBase, exclude=("password",))

    @post_load
    def make(self, data: dict[str, Any], **kwargs: object) -> ApiKey:  # noqa: ARG002 -- Marshmallow supplies hook options
        """Create the API key transfer object from deserialized fields.

        Args:
            data: Deserialized API key fields.
            **kwargs: Marshmallow post-load hook options.

        Returns:
            The API key transfer object.
        """
        return ApiKey(**data)


class ApiKey:
    """Carry deserialized API key fields without owning database defaults."""

    def __init__(
        self,
        # id,
        name: str,
        key: str,
        created_at: datetime | None,  # noqa: ARG002 -- Accepted schema field; database default owns creation time
        user_id: int | None,
        expires_at: datetime | None,
    ) -> None:
        """Create an API key transfer object.

        Args:
            name: API key name.
            key: API key secret.
            created_at: Accepted for schema compatibility; persistence supplies creation time.
            user_id: Owner's user ID, or None for an unassigned key.
            expires_at: Expiration timestamp, or None for no expiration.
        """
        self.id = id
        self.name = name
        self.key = key
        # created_at - database take care about it
        self.user_id = user_id
        self.expires_at = expires_at
