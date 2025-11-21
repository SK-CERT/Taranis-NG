"""Data Provider Model."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from model.data_provider import DataProvider

from datetime import UTC, datetime

from managers.db_manager import db
from marshmallow import post_load

from shared.schema.data_provider import DataProviderSchema


class DataProvider(db.Model):
    """This model represents a Data Provider in the database.

    Attributes:
        id (int): Data Provider ID.
        name (str): Data Provider name.
        api_type (enum): Data Provider type - CVE, CWE, CPE, EUVD.
        api_url (str): Data Provider API url.
        api_key (str): Data Provider API key.
        user_agent (str): Data Provider user agent.
        updated_by (str): User who last updated the record.
        updated_at (datetime): Timestamp of the last update.
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    api_type = db.Column(db.String(), nullable=False, server_default="EUVD")
    api_url = db.Column(db.String(), nullable=False)
    api_key = db.Column(db.String())
    user_agent = db.Column(db.String())
    web_url = db.Column(db.String())
    updated_by = db.Column(db.String())
    updated_at = db.Column(db.DateTime)

    def __init__(self, name: str, api_type: str, api_url: str, api_key: str, user_agent: str, web_url: str) -> None:
        """Create a new Data Provider."""
        self.name = name
        self.api_type = api_type
        self.api_url = api_url
        self.api_key = api_key
        self.user_agent = user_agent
        self.web_url = web_url

    @classmethod
    def find(cls, data_provider_id: int) -> DataProvider:
        """Find a Data Provider by ID.

        Args:
            data_provider_id (int): Data Provider ID.

        Returns:
            Data Provider object.
        """
        return db.session.get(cls, data_provider_id)

    @classmethod
    def get_all(cls) -> list:
        """Get all Data Providers.

        Returns:
            list: List of Data Providers.
        """
        return cls.query.order_by(db.asc(DataProvider.name)).all()

    @classmethod
    def get(cls, search: str) -> tuple:
        """Get Data Providers.

        Args:
            search (str): Search string.

        Returns:
            list: List of Data Providers.
        """
        query = cls.query

        if search is not None:
            query = query.filter(DataProvider.name.ilike(f"%{search}%"))

        return query.order_by(db.asc(DataProvider.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search: str) -> dict:
        """Get all Data Providers in JSON format based on a search query.

        Args:
            search (str): Search query.

        Returns:
            dict: Dictionary containing total count and list of Data Providers in JSON format.
        """
        data_providers, count = cls.get(search)
        schema = DataProviderSchema(many=True)
        return {"total_count": count, "items": schema.dump(data_providers)}

    @classmethod
    def add_new(cls, data: dict, user_name: str) -> DataProvider:
        """Add a new Data Provider.

        Args:
            data (dict): Data to create the new Data Provider.
            user_name (str): User who is adding the Data Provider.

        Returns:
            DataProvider: New Data Provider object.
        """
        schema = NewDataProviderSchema()
        new = schema.load(data)
        new.updated_by = user_name
        new.updated_at = datetime.now(tz=UTC)
        db.session.add(new)
        db.session.commit()
        return new

    @classmethod
    def update(cls, data_provider_id: int, data: dict, user_name: str) -> DataProvider:
        """Update an existing Data Provider.

        Args:
            data_provider_id (int): ID of the Data Provider to update.
            data (dict): Data to update the Data Provider with.
            user_name (str): User who is updating the Data Provider.
        """
        schema = DataProviderSchema()
        new = schema.load(data)
        old = db.session.get(cls, data_provider_id)
        old.name = new.name
        old.api_type = new.api_type
        old.api_url = new.api_url
        old.api_key = new.api_key
        old.user_agent = new.user_agent
        old.web_url = new.web_url
        old.updated_by = user_name
        old.updated_at = datetime.now(tz=UTC)
        db.session.commit()
        return old

    @classmethod
    def delete(cls, data_provider_id: int) -> None:
        """Delete a Data Provider.

        Args:
            data_provider_id (int): Data Provider ID.
        """
        record = db.session.get(cls, data_provider_id)
        db.session.delete(record)
        db.session.commit()


class NewDataProviderSchema(DataProviderSchema):
    """New Data Provider Schema."""

    @post_load
    def make(self, data: dict, **kwargs) -> DataProvider:  # noqa: ARG002, ANN003
        """Create a new Data Provider.

        Args:
            data (dict): Data to create the new Data Provider.
            **kwargs: Additional keyword arguments passed by Marshmallow (unused but required).

        Returns:
            DataProvider: New Data Provider object.
        """
        return DataProvider(**data)
