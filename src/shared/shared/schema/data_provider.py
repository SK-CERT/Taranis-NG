"""This module defines the schema and data model for Data Providers using Marshmallow for serialization and deserialization."""

from marshmallow import Schema, fields, post_load, EXCLUDE


class DataProviderSchema(Schema):
    """Marshmallow schema for serializing and deserializing DataProvider objects."""

    class Meta:
        """Meta class to define schema behavior."""

        unknown = EXCLUDE

    id = fields.Int()
    name = fields.Str()
    api_type = fields.Str()
    api_url = fields.Str()
    api_key = fields.Str()
    user_agent = fields.Str()
    web_url = fields.Str()
    updated_by = fields.Str()
    updated_at = fields.Str()

    @post_load
    def make(self, data, **kwargs):
        """Create a DataProvider instance from the deserialized data.

        Args:
            data (dict): The deserialized data containing DataProvider attributes.
            **kwargs: Additional keyword arguments.
        Returns:
            DataProvider: An instance of DataProvider initialized with the provided data.
        """
        return DataProvider(**data)


class DataProvider:
    """Data model for Data Providers."""

    def __init__(
        self,
        name,
        api_type,
        api_url,
        api_key,
        user_agent,
        web_url,
        updated_by,
    ):
        """Initialize a DataProvider instance.

        Args:
            name (str): Name of the Data Provider.
            api_type (str): API type ("CVE, CWE, CPE, EUVD").
            api_url (str): API URL of the provider.
            api_key (str): API key for authentication.
            user_agent (str): User agent string.
            updated_by (str): User who last updated the provider.
        """
        self.name = name
        self.api_type = api_type
        self.api_url = api_url
        self.api_key = api_key
        self.user_agent = user_agent
        self.web_url = web_url
        self.updated_by = updated_by
