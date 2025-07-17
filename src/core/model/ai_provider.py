"""AI Provider Model."""

from datetime import datetime
from managers.db_manager import db
from shared.schema.ai_provider import AiProviderSchema


# class NewAiProviderSchema(AiProviderSchema):
#     """New AI Provider Schema."""

#     @post_load
#     def make(self, data, **kwargs):
#         """Create a new AI Provider.

#         Args:
#             data (dict): Data to create the new AI Provider.
#         Returns:
#             AiProvider: New AI Provider object.
#         """
#         return AiProvider(**data)


class AiProvider(db.Model):
    """AI Provider Model.

    This model represents an AI Provider in the database.

    Attributes:
        id (int): AI Provider ID.
        name (str): AI Provider name.
        api_type (str): AI Provider type - currently only "openai" is supported (also valid for ollama)
        api_url (str): AI Provider API url.
        api_key (str): AI Provider API key.
        model (str): AI Provider model.
        updated_by (str): User who last updated the record.
        updated_at (datetime): Timestamp of the last update.
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    api_type = db.Column(db.String(), nullable=False, default="openai", server_default="openai")
    api_url = db.Column(db.String(), nullable=False)
    api_key = db.Column(db.String())
    model = db.Column(db.String())
    updated_by = db.Column(db.String())
    updated_at = db.Column(db.DateTime)

    def __init__(self, name, api_type, api_url, api_key, model, updated_by):
        """Create a new AI Provider."""
        # self.id = None
        self.name = name
        self.api_type = api_type
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.updated_by = updated_by

    @classmethod
    def find(cls, id):
        """Find an AI Provider by ID.

        Args:
            id (int): AI Provider ID.
        Returns:
            AiProvider: AI Provider object.
        """
        AiProvider = db.session.get(cls, id)
        return AiProvider

    @classmethod
    def get_all(cls):
        """Get all AI Providers.

        Returns:
            list: List of AI Providers.
        """
        return cls.query.order_by(db.asc(AiProvider.name)).all()

    @classmethod
    def get(cls, search):
        """Get AI Providers.

        Args:
            search (str): Search string.
        Returns:
            list: List of AI Providers.
        """
        query = cls.query

        if search is not None:
            query = query.filter(AiProvider.name.ilike(f"%{search}%"))

        return query.order_by(db.asc(AiProvider.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        """
        Get all AI Providers in JSON format based on a search query.

        Args:
            search (str): Search query.

        Returns:
            dict: Dictionary containing total count and list of AI Providers in JSON format.
        """
        ai_providers, count = cls.get(search)
        schema = AiProviderSchema(many=True)
        return {"total_count": count, "items": schema.dump(ai_providers)}

    @classmethod
    def add_new(cls, data):
        """Add a new AI Provider.

        Args:
            data (dict): Data to create the new AI Provider.
        Returns:
            AiProvider: New AI Provider object.
        """
        # schema = NewAiProviderSchema()
        schema = AiProviderSchema()
        new = schema.load(data)
        new.updated_at = datetime.now()
        db.session.add(new)
        db.session.commit()
        return new

    @classmethod
    def update(cls, id, data, user_name):
        """
        Update an existing AI Provider.

        Args:
            id (int): ID of the AI Provider to update.
            data (dict): Data to update the AI Provider with.
            user_mame (str): User who is updating the AI Provider.
        """
        schema = AiProviderSchema()
        new = schema.load(data)
        old = db.session.get(cls, id)
        old.name = new.name
        old.api_type = new.api_type
        old.api_url = new.api_url
        old.api_key = new.api_key
        old.model = new.model
        old.updated_by = user_name
        old.updated_at = datetime.now()
        db.session.commit()

    @classmethod
    def delete(cls, id):
        """Delete an AI Provider.

        Args:
            id (int): AI Provider ID.
        """
        AiProvider = db.session.get(cls, id)
        db.session.delete(AiProvider)
        db.session.commit()
