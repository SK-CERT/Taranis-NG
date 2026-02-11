"""This module defines the schema and data model for AI model."""

from marshmallow import EXCLUDE, Schema, fields, post_load


class AiProvider:
    """Data model for AI model."""

    def __init__(
        self,
        id: int,  # noqa: A002
        name: str,
        api_type: str,
        api_url: str,
        api_key: str,
        model: str,
    ) -> None:
        """Initialize an AiProvider instance.

        Args:
            id (int): Unique identifier for the AI model.
            name (str): Name of the AI model.
            api_type (str): API type ("openai").
            api_url (str): The endpoint URL.
            api_key (str): API key for authentication.
            model (str): Model name or identifier.
        """
        self.id = id
        self.name = name
        self.api_type = api_type
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        # updated_by and updated_at are set on the server


class AiProviderSchema(Schema):
    """Marshmallow schema for serializing and deserializing AiProvider objects."""

    class Meta:
        """Meta class to define schema behavior."""

        unknown = EXCLUDE

    id = fields.Int()
    name = fields.Str()
    api_type = fields.Str()
    api_url = fields.Str()
    api_key = fields.Str()
    model = fields.Str()
    updated_by = fields.Str(dump_only=True)
    updated_at = fields.Str(dump_only=True)

    @post_load
    def make(self, data: dict, **kwargs) -> AiProvider:  # noqa: ANN003, ARG002
        """Create a AiProvider instance from the deserialized data.

        Args:
            data (dict): The deserialized data containing AI model attributes.
            **kwargs: Additional keyword arguments.

        Returns:
            AiProvider: An instance of AiProvider initialized with the provided data.
        """
        return AiProvider(**data)
