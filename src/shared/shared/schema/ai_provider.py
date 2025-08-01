"""This module defines the schema and data model for local AI models using Marshmallow for serialization and deserialization."""

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
    updated_by = fields.Str(dump_only=True)
    updated_at = fields.Str(dump_only=True)

    @post_load
    def make(self, data, **kwargs):
        """Create a AiProvider instance from the deserialized data.

        Args:
            data (dict): The deserialized data containing local AI modelr attributes.
            **kwargs: Additional keyword arguments.
        Returns:
            AiProvider: An instance of AiProvider initialized with the provided data.
        """
        return AiProvider(**data)


class AiProvider:
    """Data model for Local AI models."""

    def __init__(self, id, name, api_type, api_url, api_key, model):
        """Initialize an AiProvider instance.

        Args:
            id (int): Unique identifier for the local AI model.
            name (str): Name of the local AI model.
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
