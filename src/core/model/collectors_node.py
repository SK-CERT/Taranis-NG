"""Collectors Node Model."""

import uuid
from datetime import datetime
from marshmallow import post_load
from sqlalchemy import orm, or_, func

from managers.db_manager import db
from managers.log_manager import logger
from shared.schema.collectors_node import CollectorsNodeSchema, CollectorsNodePresentationSchema


class NewCollectorsNodeSchema(CollectorsNodeSchema):
    """New Collectors Node Schema."""

    @post_load
    def make_collectors_node(self, data, **kwargs):
        """Create Collectors Node object.

        Args:
            data (dict): The data to load
        Returns:
            (CollectorsNode): The CollectorsNode object
        """
        return CollectorsNode(name=data["name"], description=data["description"], api_url=data["api_url"], api_key=data["api_key"])


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

    def __init__(self, name, description, api_url, api_key):
        """Initialize CollectorsNode object."""
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.api_url = api_url
        self.api_key = api_key
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self):
        """Reconstruct CollectorsNode object."""
        self.tag = "mdi-server-network"

    @classmethod
    def get_by_api_key(cls, api_key):
        """Get a node by API key.

        Args:
            api_key (str): The API key
        Returns:
            (CollectorsNode): The CollectorsNode object
        """
        return cls.query.filter_by(api_key=api_key).first()

    @classmethod
    def get_all(cls):
        """Get all nodes.

        Returns:
            (list): The list of nodes
        """
        return cls.query.order_by(db.asc(CollectorsNode.name)).all()

    @classmethod
    def get(cls, search):
        """Get nodes.

        Args:
            search (str): The search string
        Returns:
            (list): The list of nodes
            (int): The count of nodes
        """
        query = cls.query

        if search is not None:
            search_string = f"%{search.lower()}%"
            query = query.filter(
                or_(func.lower(CollectorsNode.name).like(search_string), func.lower(CollectorsNode.description).like(search_string))
            )

        return query.order_by(db.asc(CollectorsNode.name)).all(), query.count()

    @classmethod
    def get_by_id(cls, id):
        """Get a node by ID.

        Args:
            id (str): The ID of the node
        Returns:
            (CollectorsNode): The CollectorsNode object
        """
        return cls.query.filter_by(id=id).first()

    @classmethod
    def get_by_name(cls, name):
        """Get a node by name.

        Args:
            name (str): The name of the node
        Returns:
            (CollectorsNode): The CollectorsNode object
        """
        return cls.query.filter_by(name=name).first()

    def find_collector_by_type(self, collector_type):
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
    def get_all_json(cls, search):
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
                time_inactive = datetime.now() - max(nodes[i].created, nodes[i].last_seen)
                items[i]["status"] = "green" if time_inactive.seconds < 60 else "orange" if time_inactive.seconds < 300 else "red"
            except Exception as ex:
                logger.exception(f"Cannot update collector status: {ex}")
                # if never collected before
                items[i]["status"] = "red"

        return {"total_count": count, "items": items}

    @classmethod
    def add_new(cls, node_data, collectors):
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
    def update(cls, node_id, node_data, collectors):
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
    def delete(cls, node_id):
        """Delete a node.

        Args:
            node_id (str): The ID of the node
        """
        node = db.session.get(cls, node_id)
        for collector in node.collectors:
            if len(collector.sources) > 0:
                raise Exception("Collectors has mapped sources")

        db.session.delete(node)
        db.session.commit()

    def updateLastSeen(self):
        """Update the last seen date of the node."""
        self.last_seen = datetime.now()
        db.session.add(self)
        db.session.commit()
