"""Collectors Node Model."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from model.collector import Collector
    from model.collectors_node import CollectorsNode

import uuid
from datetime import datetime
from http import HTTPStatus

from managers.db_manager import db
from managers.log_manager import logger
from marshmallow import post_load
from model.parameter import Parameter
from sqlalchemy import or_, orm

from shared.common import TZ
from shared.schema.collectors_node import CollectorsNodePresentationSchema, CollectorsNodeSchema


class CollectorsNode(db.Model):
    """Collectors Node model.

    Attributes:
        id (str): The ID of the node
        name (str): The name of the node
        description (str): The description of the node
        api_url (str): The API URL of the node
        api_key (str): The API key of the node
        created (datetime): The creation date of the node
        last_seen (datetime): The last seen date of the node
        collectors (list): The collectors associated with the node
    """

    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), unique=True, nullable=False)
    description = db.Column(db.String())

    api_url = db.Column(db.String(), nullable=False)
    api_key = db.Column(db.String(), nullable=False)

    created = db.Column(db.DateTime, default=datetime.now)
    last_seen = db.Column(db.DateTime, default=datetime.now)

    collectors = db.relationship("Collector", back_populates="node", cascade="all")

    def __init__(self, name: str, description: str, api_url: str, api_key: str) -> None:
        """Initialize CollectorsNode object."""
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.api_url = api_url
        self.api_key = api_key
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self) -> None:
        """Reconstruct CollectorsNode object."""
        self.tag = "mdi-server-network"

    @classmethod
    def get_by_api_key(cls, api_key: str) -> CollectorsNode:
        """Get a node by API key.

        Args:
            api_key (str): The API key
        Returns:
            (CollectorsNode): The CollectorsNode object
        """
        return cls.query.filter_by(api_key=api_key).first()

    @classmethod
    def get_by_api_key_id(cls, api_key: str, node_id: str) -> CollectorsNode:
        """Get a node by API key and node ID (more nodes can have the same key).

        Args:
            api_key (str): The API key
            node_id (str): The ID of the collectors node
        Returns:
            (CollectorsNode): The CollectorsNode object
        """
        return cls.query.filter_by(api_key=api_key, id=node_id).first()

    @classmethod
    def get_all(cls) -> list[CollectorsNode]:
        """Get all nodes.

        Returns:
            (list): The list of nodes
        """
        return cls.query.order_by(db.asc(CollectorsNode.name)).all()

    @classmethod
    def get(cls, search: str) -> tuple[list[CollectorsNode], int]:
        """Get nodes.

        Args:
            search (str): The search string
        Returns:
            (list): The list of nodes
            (int): The count of nodes
        """
        query = cls.query

        if search is not None:
            search_string = f"%{search}%"
            query = query.filter(or_(CollectorsNode.name.ilike(search_string), CollectorsNode.description.ilike(search_string)))

        return query.order_by(db.asc(CollectorsNode.name)).all(), query.count()

    @classmethod
    def get_by_id(cls, node_id: str) -> CollectorsNode:
        """Get a node by ID.

        Args:
            node_id (str): The ID of the node
        Returns:
            (CollectorsNode): The CollectorsNode object
        """
        return cls.query.filter_by(id=node_id).first()

    @classmethod
    def get_by_name(cls, name: str) -> CollectorsNode:
        """Get a node by name.

        Args:
            name (str): The name of the node
        Returns:
            (CollectorsNode): The CollectorsNode object
        """
        return cls.query.filter_by(name=name).first()

    def find_collector_by_type(self, collector_type: str) -> Collector | None:
        """Find a collector by type.

        Args:
            collector_type (str): The collector type
        Returns:
            (Collector): The collector object or None
        """
        for collector in self.collectors:
            if collector.type == collector_type:
                return collector

        return None

    @classmethod
    def get_all_json(cls, search: str) -> dict:
        """Get all nodes in JSON format.

        Args:
            search (str): The search string
        Returns:
            (dict): The nodes in JSON format
        """
        nodes, count = cls.get(search)
        node_schema = CollectorsNodePresentationSchema(many=True)
        items = node_schema.dump(nodes)

        for i in range(len(items)):
            # calculate collector status
            #   green (last ping in time) < 60s
            #   orange (last ping late) < 300s
            #   red (no ping in a long time) > 300s
            try:
                time_inactive = datetime.now(TZ) - max(nodes[i].created.replace(tzinfo=TZ), nodes[i].last_seen.replace(tzinfo=TZ))
                items[i]["status"] = "green" if time_inactive.seconds < 60 else "orange" if time_inactive.seconds < 300 else "red"  # noqa: PLR2004
            except Exception as ex:
                logger.exception(f"Cannot update collector status: {ex}")
                # if never collected before
                items[i]["status"] = "red"

        return {"total_count": count, "items": items}

    @classmethod
    def add_new(cls, node_data: dict, collectors: list) -> CollectorsNode:
        """Add a new node.

        Args:
            node_data (dict): The node data
            collectors (list): The collectors
        Returns:
            (CollectorsNode): The CollectorsNode object
        """
        new_node_schema = NewCollectorsNodeSchema()
        node = new_node_schema.load(node_data)
        node.collectors = collectors
        db.session.add(node)
        db.session.commit()
        return node

    @classmethod
    def update(cls, node_id: str, node_data: dict, collectors: list) -> CollectorsNode:
        """Update a node.

        Args:
            node_id (str): The ID of the node
            node_data (dict): The node data
            collectors (list): The collectors
        """
        new_node_schema = NewCollectorsNodeSchema()
        updated_node = new_node_schema.load(node_data)
        node = db.session.get(cls, node_id)
        node.name = updated_node.name
        node.description = updated_node.description
        node.api_url = updated_node.api_url
        node.api_key = updated_node.api_key
        for collector in collectors:
            found = False
            for existing_collector in node.collectors:
                if collector.type == existing_collector.type:
                    found = True
                    break

            if found is False:
                node.collectors.append(collector)

        db.session.commit()

    @classmethod
    def delete(cls, node_id: str) -> tuple[dict, HTTPStatus]:
        """Delete a node.

        Args:
            node_id (str): The ID of the node
        """
        node = db.session.get(cls, node_id)

        exist_some_source = False
        for collector in node.collectors:
            if len(collector.sources) > 0:
                exist_some_source = True
                break

        if exist_some_source:
            node_def = cls.query.filter(CollectorsNode.id != node_id).first()
            if node_def is None:
                msg = "Cannot delete the last collectors node. If you need to delete it, delete associated OSINT sources first!"
                logger.warning(msg)
                return {"error": msg}, HTTPStatus.BAD_REQUEST

            for collector in node.collectors:
                for source in collector.sources:
                    # remap collector_id
                    for coll_def in node_def.collectors:
                        if coll_def.type == collector.type:
                            source.collector_id = coll_def.id
                            # remap parameter values
                            for pv in source.parameter_values:
                                for coll_def_param in coll_def.parameters:
                                    if pv.parameter.key == coll_def_param.key:
                                        pv.parameter_id = coll_def_param.id
                            break
            db.session.commit()

        db.session.delete(node)
        db.session.commit()
        Parameter.delete_unused()
        return "", HTTPStatus.OK

    def update_last_seen(self) -> None:
        """Update the last seen date of the node."""
        self.last_seen = datetime.now(TZ)
        db.session.add(self)
        db.session.commit()


class NewCollectorsNodeSchema(CollectorsNodeSchema):
    """New Collectors Node Schema."""

    @post_load
    def make_collectors_node(self, data: dict, **kwargs) -> CollectorsNode:  # noqa: ANN003, ARG002
        """Create Collectors Node object.

        Args:
            data (dict): The data to load
            **kwargs: Additional arguments.

        Returns:
            (CollectorsNode): The CollectorsNode object
        """
        return CollectorsNode(name=data["name"], description=data["description"], api_url=data["api_url"], api_key=data["api_key"])
