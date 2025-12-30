"""CollectorsNode scheme."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.schema.collectors_node import CollectorsNode

from marshmallow import Schema, fields, post_load

from shared.schema.collector import CollectorSchema
from shared.schema.presentation import PresentationSchema


class CollectorsNode:
    """Lightweight data container created by `CollectorsNodeSchema`."""

    def __init__(
        self,
        id: str,  # noqa: A002
        name: str,
        description: str,
        api_url: str,
        api_key: str,
    ) -> None:
        """Initialize a CollectorsNode.

        Args:
            id (str): GUID for the collectors node.
            name (str): Human-readable name of the node.
            description (str): Short description or notes about the node.
            api_url (str): Base URL for the node's API endpoint.
            api_key (str): API key or token used to authenticate requests to the node.
        """
        self.id = id
        self.name = name
        self.description = description
        self.api_url = api_url
        self.api_key = api_key

    @classmethod
    def create(cls, data: dict) -> CollectorsNode:
        """Create a `CollectorsNode` from a dict via `CollectorsNodeSchema`.

        Args:
            data (dict): Raw data to be validated and deserialized.

        Returns:
            CollectorsNode: Instance created from the validated data.
        """
        node_schema = CollectorsNodeSchema()
        return node_schema.load(data)


class CollectorsNodeSchema(Schema):
    """Marshmallow schema for a collectors node."""

    id = fields.Str()
    name = fields.Str()
    description = fields.Str()
    api_url = fields.Str()
    api_key = fields.Str()
    collectors = fields.List(fields.Nested(CollectorSchema))
    status = fields.Str(dump_only=True)
    created = fields.DateTime("%d.%m.%Y - %H:%M", dump_only=True)
    last_seen = fields.DateTime("%d.%m.%Y - %H:%M", dump_only=True)

    @post_load
    def make(self, data: dict, **kwargs) -> CollectorsNode:  # noqa: ANN003, ARG002
        """Construct a `CollectorsNode` instance from the deserialized data.

        Args:
            data (dict): The deserialized data from the schema.
            **kwargs: Additional keyword arguments.

        Returns:
            CollectorsNode: A new CollectorsNode instance populated from `data`.
        """
        return CollectorsNode(**data)


class CollectorsNodePresentationSchema(CollectorsNodeSchema, PresentationSchema):
    """Presentation-oriented schema for collectors nodes."""
