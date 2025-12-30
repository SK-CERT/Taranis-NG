"""BotsNode scheme."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.schema.bots_node import BotsNode

from marshmallow import EXCLUDE, Schema, fields, post_load

from shared.schema.bot import BotSchema
from shared.schema.presentation import PresentationSchema


class BotsNode:
    """Lightweight model representing a Bots node."""

    def __init__(
        self,
        id: str,  # noqa: A002
        name: str,
        description: str,
        api_url: str,
        api_key: str,
    ) -> None:
        """Initialize a BotsNode model.

        Parameters are mapped directly to instance attributes.

        Args:
            id (str): GUID identifier.
            name (str): Node display name.
            description (str): Description text.
            api_url (str): API endpoint URL.
            api_key (str): API key string.
        """
        self.id = id
        self.name = name
        self.description = description
        self.api_url = api_url
        self.api_key = api_key

    @classmethod
    def create(cls, data: dict) -> BotsNode:
        """Create a `BotsNode` instance from raw data using `BotsNodeSchema`.

        This helper wraps schema validation and deserialization. It will raise
        marshmallow exceptions (e.g., `ValidationError`) if the input is invalid.

        Args:
            data (dict): Raw mapping with keys matching `BotsNodeSchema`.

        Returns:
            BotsNode: The deserialized BotsNode instance.
        """
        node_schema = BotsNodeSchema()
        return node_schema.load(data)


class BotsNodeSchema(Schema):
    """Schema for (de)serializing a Bots node."""

    class Meta:
        """Meta class."""

        unknown = EXCLUDE

    id = fields.Str()
    name = fields.Str()
    description = fields.Str()
    api_url = fields.Str()
    api_key = fields.Str()
    bots = fields.List(fields.Nested(BotSchema))
    created = fields.DateTime("%d.%m.%Y - %H:%M", dump_only=True)
    last_seen = fields.DateTime("%d.%m.%Y - %H:%M", dump_only=True)

    @post_load
    def make(self, data: dict, **kwargs) -> BotsNode:  # noqa: ANN003, ARG002
        """Construct a `BotsNode` instance from the deserialized data.

        Args:
            data (dict): The deserialized data from the schema.
            **kwargs: Additional keyword arguments.

        Returns:
            BotsNode: A new BotsNode instance populated from `data`.
        """
        return BotsNode(**data)


class BotsNodePresentationSchema(BotsNodeSchema, PresentationSchema):
    """Presentation variant of `BotsNodeSchema`."""
