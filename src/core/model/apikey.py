"""API Key Model."""

from datetime import datetime

from managers.db_manager import db
from marshmallow import post_load

from shared.schema.apikey import ApiKeySchema


class NewApiKeySchema(ApiKeySchema):
    """New API Key Schema."""

    @post_load
    def make(self, data, **kwargs):
        """Create a new API Key.

        Args:
            data (dict): Data to create the new API Key.

        Returns:
            ApiKey: New API Key object.
        """
        return ApiKey(**data)


class ApiKey(db.Model):
    """API Key Model.

    This model represents an API Key in the database.

    Attributes:
        id (int): API Key ID.
        name (str): API Key name.
        key (str): API Key key.
        created_at (datetime): API Key creation date.
        user_id (int): User ID that owns the API Key.
        expires_at (datetime): API Key expiration date.
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    key = db.Column(db.String())  # length 40
    created_at = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True, default=None)

    def __init__(self, name, key, created_at, user_id, expires_at):
        """Create a new API Key."""
        # self.id = None
        self.name = name
        self.key = key
        # created_at - automatically populated by database
        self.user_id = user_id
        self.expires_at = expires_at

    @classmethod
    def find(cls, apikey_id):
        """Find an API Key by ID.

        Args:
            apikey_id (int): API Key ID.

        Returns:
            ApiKey: API Key object.
        """
        apikey = db.session.get(cls, apikey_id)
        return apikey

    @classmethod
    def find_by_name(cls, apikey_name):
        """Find an API Key by name.

        Args:
            apikey_name (str): API Key name.

        Returns:
            ApiKey: API Key object.
        """
        apikey = cls.query.filter_by(name=apikey_name).first()
        return apikey

    @classmethod
    def find_by_key(cls, key_str):
        """Find an API Key by key.

        Args:
            key_str (str): API Key key.

        Returns:
            ApiKey: API Key object.s
        """
        apikey = cls.query.filter_by(key=key_str).first()
        return apikey

    @classmethod
    def get_all(cls):
        """Get all API Keys.

        Returns:
            list: List of API Keys.
        """
        return cls.query.order_by(db.asc(ApiKey.name)).all()

    @classmethod
    def get(cls, search):
        """Get API Keys.

        Args:
            search (str): Search string.

        Returns:
            list: List of API Keys.
        """
        query = cls.query

        if search is not None:
            search_string = f"%{search}%"
            query = query.filter(ApiKey.name.ilike(search_string))

        return query.order_by(db.asc(ApiKey.name)).all(), query.count()

    @classmethod
    def add_new(cls, data):
        """Add a new API Key.

        Args:
            data (dict): Data to create the new API Key.

        Returns:
            ApiKey: New API Key object.
        """
        schema = NewApiKeySchema()
        apikey = schema.load(data)
        # db.session.add(apikey.user)
        db.session.add(apikey)
        db.session.commit()
        return apikey

    @classmethod
    def delete(cls, id):
        """Delete an API Key.

        Args:
            id (int): API Key ID.
        """
        apikey = db.session.get(cls, id)
        db.session.delete(apikey)
        db.session.commit()
