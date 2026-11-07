"""Publisher model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from managers.db_manager import db
from marshmallow import fields, post_load
from model.parameter import NewParameterSchema
from shared.schema.publisher import PublisherSchema

if TYPE_CHECKING:
    from model.parameter import Parameter


class NewPublisherSchema(PublisherSchema):
    """New publisher schema.

    Attributes:
        parameters: List of parameters
    """

    parameters = fields.List(fields.Nested(NewParameterSchema))

    @post_load
    def make(self, data: dict, **kwargs) -> Publisher:  # noqa: ARG002, ANN003
        """Create a new publisher.

        Args:
            data: Publisher data
            **kwargs: Additional arguments.

        Returns:
            Publisher: New publisher
        """
        return Publisher(**data)


class Publisher(db.Model):
    """Publisher model: one publisher of a publishers node.

    Attributes:
        id: Publisher GUID
        name: Publisher name
        description: Publisher description
        type: Publisher type
        parameters: List of parameters
        node_id: Publishers node GUID
        node: Publishers node
        channels: The publishing channels that send through this publisher
    """

    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    type = db.Column(db.String(), nullable=False)

    parameters = db.relationship("Parameter", secondary="publisher_parameter")

    node_id = db.Column(db.String, db.ForeignKey("publishers_node.id"))
    node = db.relationship("PublishersNode", back_populates="publishers")

    channels = db.relationship("PublishingChannel", back_populates="publisher")

    def __init__(self, name: str, description: str, type: str, parameters: list[Parameter]) -> None:  # noqa: A002
        """Initialize publisher."""
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.type = type
        self.parameters = parameters

    @classmethod
    def create_all(cls, publishers_data: list[dict]) -> list[Publisher]:
        """Create publishers from their data.

        Args:
            publishers_data: Publishers data

        Returns:
            List[Publisher]: New publishers
        """
        new_publisher_schema = NewPublisherSchema(many=True)
        return new_publisher_schema.load(publishers_data)


class PublisherParameter(db.Model):
    """Publisher parameter model.

    Attributes:
        publisher_id: Publisher GUID
        parameter_id: Parameter id
    """

    publisher_id = db.Column(db.String, db.ForeignKey("publisher.id"), primary_key=True)
    parameter_id = db.Column(db.Integer, db.ForeignKey("parameter.id"), primary_key=True)
