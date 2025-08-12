"""Data Provider Model."""

from datetime import datetime
from marshmallow import post_load
from managers.db_manager import db
from shared.schema.data_provider import DataProviderSchema


class NewDataProviderSchema(DataProviderSchema):
    """New Data Provider Schema."""

    @post_load
    def make(self, data, **kwargs):
        """Create a new Data Provider.

        Args:
            data (dict): Data to create the new Data Provider.
        Returns:
            DataProvider: New Data Provider object.
        """
        return DataProvider(**data)


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
    user_agent = db.Column(db.String(), server_default="Mozilla/5.0 (compatible; TaranisNG/1.0; +https://github.com/SK-CERT/Taranis-NG)")
    updated_by = db.Column(db.String())
    updated_at = db.Column(db.DateTime)

    def __init__(self, name, api_type, api_url, api_key, user_agent):
        """Create a new Data Provider."""
        # self.id = None
        self.name = name
        self.api_type = api_type
        self.api_url = api_url
        self.api_key = api_key
        self.user_agent = user_agent

    @classmethod
    def find(cls, id):
        """Find a Data Provider by ID.

        Args:
            id (int): Data Provider ID.
        Returns:
            DataProvider: Data Provider object.
        """
        DataProvider = db.session.get(cls, id)
        return DataProvider

    @classmethod
    def get_all(cls):
        """Get all Data Providers.

        Returns:
            list: List of Data Providers.
        """
        return cls.query.order_by(db.asc(DataProvider.name)).all()

    @classmethod
    def get(cls, search):
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
    def get_all_json(cls, search):
        """
        Get all Data Providers in JSON format based on a search query.

        Args:
            search (str): Search query.
        Returns:
            dict: Dictionary containing total count and list of AI Providers in JSON format.
        """
        data_providers, count = cls.get(search)
        schema = DataProviderSchema(many=True)
        return {"total_count": count, "items": schema.dump(data_providers)}

    @classmethod
    def add_new(cls, data, user_name):
        """Add a new Data Provider.

        Args:
            data (dict): Data to create the new Data Provider.
        Returns:
            DataProvider: New Data Provider object.
        """
        schema = NewDataProviderSchema()
        new = schema.load(data)
        new.updated_by = user_name
        new.updated_at = datetime.now()
        db.session.add(new)
        db.session.commit()
        return new

    @classmethod
    def update(cls, id, data, user_name):
        """Update an existing Data Provider.

        Args:
            id (int): ID of the Data Provider to update.
            data (dict): Data to update the Data Provider with.
            user_name (str): User who is updating the Data Provider.
        """
        schema = DataProviderSchema()
        new = schema.load(data)
        old = db.session.get(cls, id)
        old.name = new.name
        old.api_type = new.api_type
        old.api_url = new.api_url
        old.api_key = new.api_key
        old.user_agent = new.user_agent
        old.updated_by = user_name
        old.updated_at = datetime.now()
        db.session.commit()
        return old

    @classmethod
    def delete(cls, id):
        """Delete a Data Provider.

        Args:
            id (int): Data Provider ID.
        """
        record = db.session.get(cls, id)
        db.session.delete(record)
        db.session.commit()
