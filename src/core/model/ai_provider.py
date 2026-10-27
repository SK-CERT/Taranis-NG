"""Local AI model Model."""

from __future__ import annotations

from datetime import datetime

from managers import tlp
from managers.db_manager import db
from marshmallow import post_load
from shared.common import TZ
from shared.schema.ai_provider import AiProviderSchema


class NewAiProviderSchema(AiProviderSchema):
    """New local AI model Schema."""

    @post_load
    def make(self, data: dict, **kwargs) -> AiProvider:  # noqa: ANN003, ARG002
        """Create a new local AI model.

        Args:
            data (dict): Data to create the new local AI model.
            **kwargs: Additional keyword arguments.

        Returns:
            AiProvider: New local AI model object.
        """
        return AiProvider(**data)


class AiProvider(db.Model):
    """Local AI model.

    This model represents an local AI model in the database.

    Attributes:
        id (int): Local AI model ID.
        name (str): Local AI model name.
        api_type (str): Local AI model type - currently only "openai" is supported (also valid for ollama)
        api_url (str): Local AI model API url.
        api_key (str): Local AI model API key.
        model (str): Local AI model.
        max_tlp (str): Highest TLP of a report whose text may be sent to it; None means no limit.
        updated_by (str): User who last updated the record.
        updated_at (datetime): Timestamp of the last update.
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    api_type = db.Column(db.String(), nullable=False, default="openai", server_default="openai")
    api_url = db.Column(db.String(), nullable=False)
    api_key = db.Column(db.String())
    model = db.Column(db.String())
    max_tlp = db.Column(db.String(16), nullable=True)
    updated_by = db.Column(db.String())
    updated_at = db.Column(db.DateTime)

    def __init__(self, name: str, api_type: str, api_url: str, api_key: str | None, model: str | None, max_tlp: str | None = None) -> None:
        """Create a new local AI model.

        Raises:
            ValueError: If max_tlp is not a TLP level.
        """
        # self.id = None
        self.name = name
        self.api_type = api_type
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.max_tlp = tlp.clean_limit(max_tlp)

    @classmethod
    def find(cls, id: int) -> AiProvider | None:  # noqa: A002
        """Find an local AI model by ID.

        Args:
            id (int): Local AI model ID.

        Returns:
            AiProvider: Local AI model object.
        """
        return db.session.get(cls, id)

    @classmethod
    def get_all(cls) -> list[AiProvider]:
        """Get all local AI models.

        Returns:
            list: List of local AI models.
        """
        return cls.query.order_by(db.asc(AiProvider.name)).all()

    @classmethod
    def get(cls, search_string: str | None) -> tuple[list[AiProvider], int]:
        """Get local AI models.

        Args:
            search_string (str | None): Search string.

        Returns:
            list: List of local AI models.
        """
        query = cls.query

        if search_string is not None:
            query = query.filter(AiProvider.name.ilike(f"%{search_string}%"))

        return query.order_by(db.asc(AiProvider.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search: str | None) -> dict:
        """Get all local AI models in JSON format based on a search query.

        Args:
            search (str): Search query.

        Returns:
            dict: Dictionary containing total count and list of local AI models in JSON format.
        """
        ai_providers, count = cls.get(search)
        schema = AiProviderSchema(many=True)
        return {"total_count": count, "items": schema.dump(ai_providers)}

    @classmethod
    def add_new(cls, data: dict, user_name: str) -> AiProvider:
        """Add a new local AI model.

        Args:
            data (dict): Data to create the new local AI model.
            user_name (str): User who is adding the local AI model.

        Returns:
            AiProvider: New local AI model object.
        """
        schema = NewAiProviderSchema()
        new = schema.load(data)
        new.updated_by = user_name
        new.updated_at = datetime.now(TZ)
        db.session.add(new)
        db.session.commit()
        return new

    @classmethod
    def update(cls, id: int, data: dict, user_name: str) -> AiProvider:  # noqa: A002
        """Update an existing local AI model.

        Args:
            id (int): ID of the local AI model to update.
            data (dict): Data to update the local AI model with.
            user_name (str): User who is updating the local AI model.

        Returns:
            AiProvider: The updated local AI model.
        """
        schema = AiProviderSchema()
        new = schema.load(data)
        old = db.session.get(cls, id)
        old.name = new.name
        old.api_type = new.api_type
        old.api_url = new.api_url
        old.api_key = new.api_key
        old.model = new.model
        old.max_tlp = tlp.clean_limit(new.max_tlp)
        old.updated_by = user_name
        old.updated_at = datetime.now(TZ)
        db.session.commit()
        return old

    @classmethod
    def delete(cls, id: int) -> None:  # noqa: A002
        """Delete an local AI model.

        Args:
            id (int): Local AI model ID.
        """
        record = db.session.get(cls, id)
        db.session.delete(record)
        db.session.commit()
