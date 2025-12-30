"""BotsNode model."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from model.bot import Bot
    from model.bots_node import BotsNode

import uuid
from datetime import datetime

from managers.db_manager import db
from marshmallow import post_load
from sqlalchemy import or_, orm

from shared.common import TZ
from shared.schema.bots_node import BotsNodePresentationSchema, BotsNodeSchema


class BotsNode(db.Model):
    """BotsNode model.

    Attributes:
        id: Unique identifier for the node.
        name: Name of the node.
        description: Description of the node.
        api_url: URL of the node's API.
        api_key: API key for the node.
        bots: List of bots for the node.
    """

    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), unique=True, nullable=False)
    description = db.Column(db.String())

    api_url = db.Column(db.String(), nullable=False)
    api_key = db.Column(db.String(), nullable=False)

    created = db.Column(db.DateTime, default=datetime.now)
    last_seen = db.Column(db.DateTime)

    bots = db.relationship("Bot", back_populates="node", cascade="all")

    def __init__(
        self,
        id: str,  # noqa: A002, ARG002
        name: str,
        description: str,
        api_url: str,
        api_key: str,
    ) -> None:
        """Initialize a new BotsNode object."""
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
        """Reconstruct the BotsNode object."""
        self.title = self.name
        self.subtitle = self.description
        self.tag = "mdi-server-network"

    @classmethod
    def get_by_api_key(cls, api_key: str) -> BotsNode:
        """Get a node by API key.

        Args:
            api_key: API key to search for.

        Returns:
            Node with the given API key.
        """
        return cls.query.filter_by(api_key=api_key).first()

    @classmethod
    def get_all(cls) -> list[BotsNode]:
        """Get all nodes.

        Returns:
            List of all nodes.
        """
        return cls.query.order_by(db.asc(BotsNode.name)).all()

    @classmethod
    def get(cls, search: str) -> tuple[list[BotsNode], int]:
        """Get nodes with search filter.

        Args:
            search: Search filter.

        Returns:
            List of nodes and the count of nodes.
        """
        query = cls.query

        if search is not None:
            search_string = f"%{search}%"
            query = query.filter(or_(BotsNode.name.ilike(search_string), BotsNode.description.ilike(search_string)))

        return query.order_by(db.asc(BotsNode.name)).all(), query.count()

    @classmethod
    def get_by_id(cls, node_id: str) -> BotsNode:
        """Get a node by ID.

        Args:
            node_id (str): The GUID of the node
        Returns:
            (BotsNode): The BotsNode object
        """
        return cls.query.filter_by(id=node_id).first()

    @classmethod
    def get_by_name(cls, name: str) -> BotsNode:
        """Get a node by name.

        Args:
            name (str): The name of the node
        Returns:
            (BotsNode): The BotsNode object
        """
        return cls.query.filter_by(name=name).first()

    @classmethod
    def get_all_json(cls, search: str) -> dict:
        """Get all nodes in JSON format.

        Args:
            search: Search filter.

        Returns:
            JSON object with the total count of nodes and the items.
        """
        nodes, count = cls.get(search)
        node_schema = BotsNodePresentationSchema(many=True)
        return {"total_count": count, "items": node_schema.dump(nodes)}

    @classmethod
    def add_new(cls, node_data: dict, bots: list[Bot]) -> None:
        """Add a new node.

        Args:
            node_data: Data for the new node.
            bots: List of bots for the node.
        """
        new_node_schema = NewBotsNodeSchema()
        node = new_node_schema.load(node_data)
        node.bots = bots
        db.session.add(node)
        db.session.commit()

    @classmethod
    def update(cls, node_id: str, node_data: dict, bots: list[Bot]) -> None:
        """Update a node.

        Args:
            node_id: ID of the node to update.
            node_data: Updated data for the node.
            bots: List of bots for the node.
        """
        new_node_schema = NewBotsNodeSchema()
        updated_node = new_node_schema.load(node_data)
        node = db.session.get(cls, node_id)
        node.name = updated_node.name
        node.description = updated_node.description
        node.api_url = updated_node.api_url
        node.api_key = updated_node.api_key
        for b in bots:
            found = False
            for existing_bot in node.bots:
                if b.type == existing_bot.type:
                    found = True
                    break

            if found is False:
                node.bots.append(b)

        db.session.commit()

    @classmethod
    def delete(cls, node_id: str) -> None:
        """Delete a node.

        Args:
            node_id: ID of the node to delete.
        """
        node = db.session.get(cls, node_id)
        for b in node.bots:
            if len(b.presets) > 0:
                msg = "Bots has mapped presets"
                raise Exception(msg)  # noqa: TRY002

        db.session.delete(node)
        db.session.commit()

    def update_last_seen(self) -> None:
        """Update the last seen date of the node."""
        self.last_seen = datetime.now(TZ)
        db.session.add(self)
        db.session.commit()


class NewBotsNodeSchema(BotsNodeSchema):
    """Schema for creating a new BotsNode."""

    @post_load
    def make(self, data: dict, **kwargs) -> BotsNode:  # noqa: ARG002, ANN003
        """Create a new BotsNode object from the schema data.

        Args:
            data: Data from the schema.
            **kwargs: Additional arguments.

        Returns:
            BotsNode object.
        """
        return BotsNode(**data)
