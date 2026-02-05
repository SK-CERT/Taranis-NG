"""PublishersNode model."""

import uuid

from managers.db_manager import db
from marshmallow import post_load
from sqlalchemy import or_, orm

from shared.schema.publishers_node import PublishersNodePresentationSchema, PublishersNodeSchema


class NewPublishersNodeSchema(PublishersNodeSchema):
    """New PublishersNode schema."""

    @post_load
    def make(self, data, **kwargs):
        """Return a new PublishersNode object.

        Args:
            data (dict): Data to create a new PublishersNode object.

        Returns:
            PublishersNode: New PublishersNode object.
        """
        return PublishersNode(**data)


class PublishersNode(db.Model):
    """PublishersNode model.

    Attributes:
        id (str): Publisher node ID.
        name (str): Publisher node name.
        description (str): Publisher node description.
        api_url (str): Publisher node API URL.
        api_key (str): Publisher node API key.
        publishers (list): List of publishers.
    """

    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), unique=True, nullable=False)
    description = db.Column(db.String())

    api_url = db.Column(db.String(), nullable=False)
    api_key = db.Column(db.String(), nullable=False)

    publishers = db.relationship("Publisher", back_populates="node", cascade="all")

    def __init__(self, id, name, description, api_url, api_key):
        """Initialize a new PublishersNode object."""
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.api_url = api_url
        self.api_key = api_key
        self.title = ""
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self):
        """Reconstruct the object."""
        self.title = self.name
        self.subtitle = self.description
        self.tag = "mdi-server-network"

    @classmethod
    def get_by_api_key(cls, api_key):
        """Get a publisher node by API key.

        Args:
            api_key (str): API key.

        Returns:
            PublishersNode: Publisher node object.
        """
        return cls.query.filter_by(api_key=api_key).first()

    @classmethod
    def get_all(cls):
        """Get all publisher nodes.

        Returns:
            list: List of publisher nodes.
        """
        return cls.query.order_by(db.asc(PublishersNode.name)).all()

    @classmethod
    def get(cls, search):
        """Get publisher nodes.

        Args:
            search (str): Search string.

        Returns:
            tuple: Publisher nodes and count.
        """
        query = cls.query

        if search is not None:
            search_string = f"%{search}%"
            query = query.filter(or_(PublishersNode.name.ilike(search_string), PublishersNode.description.ilike(search_string)))

        return query.order_by(db.asc(PublishersNode.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        """Get all publisher nodes in JSON format.

        Args:
            search (str): Search string.

        Returns:
            dict: Publisher nodes in JSON format.
        """
        nodes, count = cls.get(search)
        node_schema = PublishersNodePresentationSchema(many=True)
        return {"total_count": count, "items": node_schema.dump(nodes)}

    @classmethod
    def add_new(cls, node_data, publishers):
        """Add a new publisher node.

        Args:
            node_data (dict): Node data.
            publishers (list): List of publishers.
        """
        new_node_schema = NewPublishersNodeSchema()
        node = new_node_schema.load(node_data)
        node.publishers = publishers
        db.session.add(node)
        db.session.commit()

    @classmethod
    def update(cls, node_id, node_data, publishers):
        """Update a publisher node.

        Args:
            node_id (str): Node ID.
            node_data (dict): Node data.
            publishers (list): List of publishers.
        """
        new_node_schema = NewPublishersNodeSchema()
        updated_node = new_node_schema.load(node_data)
        node = db.session.get(cls, node_id)
        node.name = updated_node.name
        node.description = updated_node.description
        node.api_url = updated_node.api_url
        node.api_key = updated_node.api_key
        for publisher in publishers:
            found = False
            for existing_publisher in node.publishers:
                if publisher.type == existing_publisher.type:
                    found = True
                    break

            if found is False:
                node.publishers.append(publisher)

        db.session.commit()

    @classmethod
    def delete(cls, node_id):
        """Delete a publisher node.

        Args:
            node_id (str): Node ID.
        """
        node = db.session.get(cls, node_id)
        for publisher in node.publishers:
            if len(publisher.presets) > 0:
                raise Exception("Presenters has mapped presets")

        db.session.delete(node)
        db.session.commit()
