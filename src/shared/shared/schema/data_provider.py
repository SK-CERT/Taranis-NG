"""This module defines the schema and data model for Data Providers using Marshmallow for serialization and deserialization."""

from marshmallow import EXCLUDE, Schema, fields, post_load


class DataProvider:
    """Data model for Data Providers."""

    def __init__(
        self,
        id: int,  # noqa: A002
        name: str,
        api_type: str,
        api_url: str,
        api_key: str,
        user_agent: str,
        web_url: str,
    ) -> None:
        """Initialize a DataProvider instance.

        Args:
            id (int): Unique identifier for the Data Provider.
            name (str): Name of the Data Provider.
            api_type (str): API type ("CVE, CWE, CPE, EUVD").
            api_url (str): API URL of the provider.
            api_key (str): API key for authentication.
            user_agent (str): User agent string.
            web_url (str): Web URL of the provider.
            updated_by (str): User who last updated the record.
        """
        self.id = id
        self.name = name
        self.api_type = api_type
        self.api_url = api_url
        self.api_key = api_key
        self.user_agent = user_agent
        self.web_url = web_url


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
    updated_by = fields.Str(dump_only=True)
    updated_at = fields.Str(dump_only=True)

    @post_load
    def make(self, data: dict, **kwargs: object) -> DataProvider:  # noqa: ARG002
        """Create a DataProvider instance from the deserialized data.

        Args:
            data (dict): The deserialized data containing DataProvider attributes.
            **kwargs: Additional keyword arguments passed by Marshmallow (unused but required).

        Returns:
            DataProvider: An instance of DataProvider initialized with the provided data.
        """
        return DataProvider(**data)
