"""This module defines the schema and data model for AI Providers using Marshmallow for serialization and deserialization."""

from marshmallow import Schema, fields, post_load, EXCLUDE


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
    updated_by = fields.Str()
    updated_at = fields.Str()

    @post_load
    def make(self, data, **kwargs):
        """Create a AiProvider instance from the deserialized data.

        Args:
            data (dict): The deserialized data containing Ai provider attributes.
            **kwargs: Additional keyword arguments.
        Returns:
            AiProvider: An instance of AiProvider initialized with the provided data.
        """
        return AiProvider(**data)


class AiProvider:
    """Data model for AI Providers."""

    def __init__(
        self,
        name,
        api_type,
        api_url,
        api_key,
        model,
        updated_by,
    ):
        """Initialize an AiProvider instance.

        Args:
            name (str): Name of the AI provider.
            api_type (str): API type ("openai", "ollama").
            api_url (str): API URL of the provider.
            api_key (str): API key for authentication.
            model (str): Model name or identifier.
            updated_by (str): User who last updated the provider.
        """
        self.name = name
        self.api_type = api_type
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.updated_by = updated_by
