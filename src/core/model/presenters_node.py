"""PresentersNode model."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from model.presenter import Presenter
    from model.presenters_node import PresentersNode

import uuid

from managers.db_manager import db
from marshmallow import post_load
from sqlalchemy import or_, orm

from shared.schema.presenters_node import PresentersNodePresentationSchema, PresentersNodeSchema


class PresentersNode(db.Model):
    """PresentersNode class.

    Attributes:
        id (str): GUID.
        name (str): Name.
        description (str): Description.
        api_url (str): API URL.
        api_key (str): API key.
        presenters (list): Presenters.
    """

    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), unique=True, nullable=False)
    description = db.Column(db.String())

    api_url = db.Column(db.String(), nullable=False)
    api_key = db.Column(db.String(), nullable=False)

    presenters = db.relationship("Presenter", back_populates="node", cascade="all")

    def __init__(
        self,
        id: str,  # noqa: A002, ARG002
        name: str,
        description: str,
        api_url: str,
        api_key: str,
    ) -> None:
        """Initilize PresentersNode."""
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.api_url = api_url
        self.api_key = api_key
        self.title = ""
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self) -> None:
        """Reconstruct method."""
        self.title = self.name
        self.subtitle = self.description
        self.tag = "mdi-server-network"

    @classmethod
    def get_by_api_key(cls, api_key: str) -> PresentersNode:
        """Get by API key.

        Args:
            api_key (str): API key.

        Returns:
            PresentersNode: PresentersNode object.
        """
        return cls.query.filter_by(api_key=api_key).first()

    @classmethod
    def get_all(cls) -> list[PresentersNode]:
        """Get all.

        Returns:
            list: List of PresentersNode objects.
        """
        return cls.query.order_by(db.asc(PresentersNode.name)).all()

    @classmethod
    def get(cls, search: str) -> tuple[list[PresentersNode], int]:
        """Get.

        Args:
            search (str): Search.

        Returns:
            list: List of PresentersNode objects.
        """
        query = cls.query

        if search is not None:
            search_string = f"%{search}%"
            query = query.filter(or_(PresentersNode.name.ilike(search_string), PresentersNode.description.ilike(search_string)))

        return query.order_by(db.asc(PresentersNode.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search: str) -> dict:
        """Get all JSON.

        Args:
            search (str): Search.

        Returns:
            dict: Dictionary.
        """
        nodes, count = cls.get(search)
        node_schema = PresentersNodePresentationSchema(many=True)
        return {"total_count": count, "items": node_schema.dump(nodes)}

    @classmethod
    def add_new(cls, node_data: dict, presenters: list[Presenter]) -> None:
        """Add new.

        Args:
            node_data (dict): Node data.
            presenters (list): Presenters.
        """
        new_node_schema = NewPresentersNodeSchema()
        node = new_node_schema.load(node_data)
        node.presenters = presenters
        db.session.add(node)
        db.session.commit()

    @classmethod
    def update(cls, node_id: str, node_data: dict, presenters: list[Presenter]) -> None:
        """Update.

        Args:
            node_id (str): Node GUID.
            node_data (dict): Node data.
            presenters (list): Presenters.
        """
        new_node_schema = NewPresentersNodeSchema()
        updated_node = new_node_schema.load(node_data)
        node = db.session.get(cls, node_id)
        node.name = updated_node.name
        node.description = updated_node.description
        node.api_url = updated_node.api_url
        node.api_key = updated_node.api_key
        for presenter in presenters:
            found = False
            for existing_presenter in node.presenters:
                if presenter.type == existing_presenter.type:
                    found = True
                    break

            if found is False:
                node.presenters.append(presenter)

        db.session.commit()

    @classmethod
    def delete(cls, node_id: str) -> None:
        """Delete.

        Args:
            node_id (str): Node GUID.
        """
        node = db.session.get(cls, node_id)
        for presenter in node.presenters:
            if len(presenter.product_types) > 0:
                msg = "Presenters has mapped product types"
                raise Exception(msg)  # noqa: TRY002

        db.session.delete(node)
        db.session.commit()


class NewPresentersNodeSchema(PresentersNodeSchema):
    """NewPresentersNodeSchema class."""

    @post_load
    def make(self, data: dict, **kwargs) -> PresentersNode:  # noqa: ARG002, ANN003
        """Make method.

        Args:
            data (dict): Data.
            **kwargs: Additional arguments.

        Returns:
            PresentersNode: PresentersNode object.
        """
        return PresentersNode(**data)
