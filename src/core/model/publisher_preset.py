"""Publisher preset model."""

from marshmallow import post_load, fields
from sqlalchemy import func, or_, orm
import uuid

from managers.db_manager import db
from model.parameter_value import NewParameterValueSchema
from shared.schema.publisher_preset import PublisherPresetSchema, PublisherPresetPresentationSchema


class NewPublisherPresetSchema(PublisherPresetSchema):
    """New publisher preset schema.

    Attributes:
        parameter_values: List of parameter values
    """

    parameter_values = fields.List(fields.Nested(NewParameterValueSchema))

    @post_load
    def make(self, data, **kwargs):
        """Create a new publisher preset.

        Args:
            data: Publisher preset data
        Returns:
            PublisherPreset: New publisher preset
        """
        return PublisherPreset(**data)


class PublisherPreset(db.Model):
    """Publisher preset model.

    Attributes:
        id: Publisher preset id
        name: Publisher preset name
        description: Publisher preset description
        publisher_id: Publisher id
        publisher: Publisher
        use_for_notifications: Use for notifications flag
        parameter_values: List of parameter values
    """

    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    publisher_id = db.Column(db.String, db.ForeignKey("publisher.id"))
    publisher = db.relationship("Publisher", back_populates="presets")

    use_for_notifications = db.Column(db.Boolean)

    parameter_values = db.relationship("ParameterValue", secondary="publisher_preset_parameter_value", cascade="all")

    def __init__(self, id, name, description, publisher_id, use_for_notifications, parameter_values):
        """Initialize a new publisher preset."""
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
    def reconstruct(self):
        """Reconstruct a publisher preset."""
        self.title = self.name
        self.subtitle = self.description
        self.tag = "mdi-file-star-outline"

    @classmethod
    def find(cls, preset_id):
        """Find a publisher preset by id.

        Args:
            preset_id: Publisher preset id
        Returns:
            PublisherPreset: Publisher preset
        """
        preset = db.session.get(cls, preset_id)
        return preset

    @classmethod
    def find_for_notifications(cls):
        """Find a publisher preset for notifications.

        Returns:
            PublisherPreset: Publisher preset
        """
        return cls.query.filter_by(use_for_notifications=True).first()

    @classmethod
    def get_all(cls):
        """Get all publisher presets.

        Returns:
            List[PublisherPreset]: List of publisher presets
        """
        return cls.query.order_by(db.asc(PublisherPreset.name)).all()

    @classmethod
    def get(cls, search):
        """Get publisher presets.

        Args:
            search: Search string
        Returns:
            Tuple[List[PublisherPreset], int]: Tuple of list of publisher presets and count
        """
        query = cls.query

        if search is not None:
            search_string = "%" + search.lower() + "%"
            query = query.filter(
                or_(func.lower(PublisherPreset.name).like(search_string), func.lower(PublisherPreset.description).like(search_string))
            )

        return query.order_by(db.asc(PublisherPreset.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        """Get all publisher presets in JSON format.

        Args:
            search: Search string
        Returns:
            dict: Publisher presets
        """
        publishers, count = cls.get(search)
        publisher_schema = PublisherPresetPresentationSchema(many=True)
        return {"total_count": count, "items": publisher_schema.dump(publishers)}

    @classmethod
    def get_all_for_publisher_json(cls, publisher_node, publisher_type):
        """Get all publisher presets for a publisher in JSON format.

        Args:
            publisher_node (PublisherNode): Publisher node object.
            publisher_type (str): Publisher type.
        Returns:
            dict: Publisher presets
        """
        for publisher in publisher_node.publishers:
            if publisher.type == publisher_type:
                presets_schema = PublisherPresetSchema(many=True)
                return presets_schema.dump(publisher.sources)

    @classmethod
    def add_new(cls, data):
        """Add a new publisher preset.

        Args:
            data: Publisher preset data
        """
        new_preset_schema = NewPublisherPresetSchema()
        preset = new_preset_schema.load(data)
        db.session.add(preset)
        db.session.commit()

    @classmethod
    def delete(cls, preset_id):
        """Delete a publisher preset.

        Args:
            preset_id: Publisher preset id
        """
        preset = db.session.get(cls, preset_id)
        db.session.delete(preset)
        db.session.commit()

    @classmethod
    def update(cls, preset_id, data):
        """Update a publisher preset.

        Args:
            preset_id: Publisher preset id
            data: Publisher preset data
        """
        new_preset_schema = NewPublisherPresetSchema()
        updated_preset = new_preset_schema.load(data)
        preset = db.session.get(cls, preset_id)
        preset.name = updated_preset.name
        preset.description = updated_preset.description

        for value in preset.parameter_values:
            for updated_value in updated_preset.parameter_values:
                if value.parameter_id == updated_value.parameter_id:
                    value.value = updated_value.value

        db.session.commit()


class PublisherPresetParameterValue(db.Model):
    """Publisher preset parameter value model.

    Attributes:
        publisher_preset_id: Publisher preset id
        parameter_value_id: Parameter value id
    """

    publisher_preset_id = db.Column(db.String, db.ForeignKey("publisher_preset.id"), primary_key=True)
    parameter_value_id = db.Column(db.Integer, db.ForeignKey("parameter_value.id"), primary_key=True)
