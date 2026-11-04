"""Publishing channel model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from managers.db_manager import db
from marshmallow import fields, post_load
from model.parameter import Parameter
from model.parameter_value import NewParameterValueSchema, ParameterValue
from model.publisher import Publisher
from shared.schema.publishing_channel import PublishingChannelPresentationSchema, PublishingChannelSchema
from sqlalchemy import or_, orm

if TYPE_CHECKING:
    from model.publishers_node import PublishersNode


class NewPublishingChannelSchema(PublishingChannelSchema):
    """New publishing channel schema.

    Attributes:
        parameter_values: List of parameter values
    """

    parameter_values = fields.List(fields.Nested(NewParameterValueSchema))

    @post_load
    def make(self, data: dict, **kwargs) -> PublishingChannel:  # noqa: ARG002, ANN003
        """Create a new publishing channel.

        Args:
            data: Publishing channel data
            **kwargs: Additional arguments.

        Returns:
            PublishingChannel: New publishing channel
        """
        return PublishingChannel(**data)


class PublishingChannel(db.Model):
    """Publishing channel model.

    Attributes:
        id: Publishing channel id
        name: Publishing channel name
        description: Publishing channel description
        publisher_id: Publisher id
        publisher: Publisher
        use_for_notifications: Use for notifications flag
        parameter_values: List of parameter values
    """

    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    publisher_id = db.Column(db.String, db.ForeignKey("publisher.id"))
    publisher = db.relationship("Publisher", back_populates="channels")

    use_for_notifications = db.Column(db.Boolean)

    parameter_values = db.relationship("ParameterValue", secondary="publishing_channel_parameter_value", cascade="all")

    def __init__(
        self,
        id: str,  # noqa: A002, ARG002
        name: str,
        description: str,
        publisher_id: str,
        use_for_notifications: bool,
        parameter_values: list[ParameterValue],
    ) -> None:
        """Initialize a new publishing channel."""
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.publisher_id = publisher_id
        self.parameter_values = parameter_values
        self.use_for_notifications = use_for_notifications
        self.title = ""
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self) -> None:
        """Reconstruct a publishing channel."""
        self.title = self.name
        self.subtitle = self.description
        self.tag = "mdi-file-star-outline"

    @classmethod
    def find(cls, channel_id: str) -> PublishingChannel | None:
        """Find a publishing channel by id.

        Args:
            channel_id: Publishing channel id
        Returns:
            PublishingChannel: Publishing channel
        """
        return db.session.get(cls, channel_id)

    @classmethod
    def find_for_notifications(cls) -> PublishingChannel | None:
        """Find a publishing channel for notifications.

        Returns:
            PublishingChannel: Publishing channel
        """
        return cls.query.filter_by(use_for_notifications=True).first()

    @classmethod
    def get_all(cls) -> list[PublishingChannel]:
        """Get all publishing channels.

        Returns:
            List[PublishingChannel]: List of publishing channels
        """
        return cls.query.order_by(db.asc(PublishingChannel.name)).all()

    @classmethod
    def get(cls, search: str) -> tuple[list[PublishingChannel], int]:
        """Get publishing channels.

        Args:
            search: Search string
        Returns:
            Tuple[List[PublishingChannel], int]: Tuple of list of publishing channels and count
        """
        query = cls.query

        if search is not None:
            search_string = f"%{search}%"
            query = query.filter(or_(PublishingChannel.name.ilike(search_string), PublishingChannel.description.ilike(search_string)))

        return query.order_by(db.asc(PublishingChannel.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search: str) -> dict:
        """Get all publishing channels in JSON format.

        Args:
            search: Search string
        Returns:
            dict: Publishing channels
        """
        publishers, count = cls.get(search)
        publisher_schema = PublishingChannelPresentationSchema(many=True)
        return {"total_count": count, "items": publisher_schema.dump(publishers)}

    @classmethod
    def get_all_for_publisher_json(cls, publisher_node: PublishersNode, publisher_type: str) -> dict | None:
        """Get all publishing channels for a publisher in JSON format.

        Args:
            publisher_node (PublisherNode): Publisher node object.
            publisher_type (str): Publisher type.

        Returns:
            dict: Publishing channels
        """
        for publisher in publisher_node.publishers:
            if publisher.type == publisher_type:
                channels_schema = PublishingChannelSchema(many=True)
                return channels_schema.dump(publisher.sources)
        return None

    @classmethod
    def add_new(cls, data: dict) -> None:
        """Add a new publishing channel.

        Args:
            data: Publishing channel data
        """
        new_channel_schema = NewPublishingChannelSchema()
        channel = new_channel_schema.load(data)
        db.session.add(channel)
        db.session.commit()

    @classmethod
    def delete(cls, channel_id: str) -> None:
        """Delete a publishing channel.

        Args:
            channel_id: Publishing channel id
        """
        channel = db.session.get(cls, channel_id)
        db.session.delete(channel)
        db.session.commit()

    @classmethod
    def update(cls, channel_id: str, data: dict) -> None:
        """Update a publishing channel.

        Args:
            channel_id: Publishing channel id
            data: Publishing channel data
        """
        new_channel_schema = NewPublishingChannelSchema()
        updated_channel = new_channel_schema.load(data)
        channel = db.session.get(cls, channel_id)
        channel.name = updated_channel.name
        channel.description = updated_channel.description

        if updated_channel.publisher_id and updated_channel.publisher_id != channel.publisher_id:
            target_publisher = db.session.get(Publisher, updated_channel.publisher_id)
            if target_publisher is None:
                msg = f"Target publisher {updated_channel.publisher_id} not found"
                raise ValueError(msg)
            channel.publisher_id = target_publisher.id

        # existing parameters are updated
        for value in channel.parameter_values:
            for updated_value in updated_channel.parameter_values:
                if value.parameter_id == updated_value.parameter_id:
                    value.value = updated_value.value
        # create missing parameters (re-save old version, re-assigning no new type)
        id_param_lookup = {param.parameter.id: param for param in channel.parameter_values}
        for par in updated_channel.parameter_values:
            if par.parameter_id not in id_param_lookup:
                param = Parameter.find(par.parameter_id)
                new_parameter_value = ParameterValue(par.value, param)
                channel.parameter_values.append(new_parameter_value)
        # delete removed parameters
        for value in channel.parameter_values:
            for updated_value in updated_channel.parameter_values:
                if value.parameter_id == updated_value.parameter_id:
                    break
            else:
                db.session.delete(value)
        db.session.commit()


class PublishingChannelParameterValue(db.Model):
    """Publishing channel parameter value model.

    Attributes:
        publishing_channel_id: Publishing channel id
        parameter_value_id: Parameter value id
    """

    publishing_channel_id = db.Column(db.String, db.ForeignKey("publishing_channel.id"), primary_key=True)
    parameter_value_id = db.Column(db.Integer, db.ForeignKey("parameter_value.id"), primary_key=True)
