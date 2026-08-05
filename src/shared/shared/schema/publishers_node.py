"""PublishersNode schema."""

from __future__ import annotations

from marshmallow import EXCLUDE, Schema, fields, post_load, validate

from shared.schema.presentation import PresentationSchema
from shared.schema.publisher import PublisherSchema


class PublishersNode:
    """Lightweight data container created by `PublishersNodeSchema`."""

    def __init__(
        self,
        id: str,  # noqa: A002
        name: str,
        description: str,
        api_url: str,
        api_key: str,
    ) -> None:
        """Initialize a publishers node.

        Args:
            id (str): GUID for the publishers node.
            name (str): Human-readable node name.
            description (str): Short description or notes about the node.
            api_url (str): Base URL for the node's API endpoint.
            api_key (str): API key used to authenticate requests to the node.
        """
        self.id = id
        self.name = name
        self.description = description
        self.api_url = api_url
        self.api_key = api_key

    @classmethod
    def create(cls, data: dict) -> PublishersNode:
        """Create a publishers node from raw schema data.

        Args:
            data (dict): Raw data to validate and deserialize.

        Returns:
            PublishersNode: Instance created from the validated data.
        """
        node_schema = PublishersNodeSchema()
        return node_schema.load(data)


class PublishersNodeSchema(Schema):
    """Marshmallow schema for a publishers node."""

    class Meta:
        """Configure unknown-field handling."""

        unknown = EXCLUDE

    id = fields.Str()
    name = fields.Str()
    description = fields.Str()
    api_url = fields.Str()
    api_key = fields.Str(required=True, validate=validate.Regexp(r".*\S"))
    publishers = fields.List(fields.Nested(PublisherSchema))

    @post_load
    def make(self, data: dict, **kwargs) -> PublishersNode:  # noqa: ANN003, ARG002
        """Construct a publishers node from deserialized data.

        Args:
            data (dict): Deserialized schema data.
            **kwargs: Additional Marshmallow callback arguments.

        Returns:
            PublishersNode: A populated publishers node.
        """
        return PublishersNode(**data)


class PublishersNodePresentationSchema(PublishersNodeSchema, PresentationSchema):
    """Presentation-oriented schema for publishers nodes."""
