"""BotPreset model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from managers.db_manager import db
from marshmallow import fields, post_load
from model.bot import Bot
from model.parameter_value import NewParameterValueSchema
from shared.schema.bot_preset import BotPresetPresentationSchema, BotPresetSchema
from sqlalchemy import or_, orm

if TYPE_CHECKING:
    from model.bots_node import BotsNode
    from model.parameter_value import ParameterValue


class NewBotPresetSchema(BotPresetSchema):
    """Schema for creating a new BotPreset.

    Attributes:
        parameter_values: List of parameter values for the preset.
    """

    parameter_values = fields.List(fields.Nested(NewParameterValueSchema))

    @post_load
    def make(self, data: dict, **kwargs) -> BotPreset:  # noqa: ARG002, ANN003
        """Create a new BotPreset object from the schema data.

        Args:
            data: Data from the schema.
            **kwargs: Additional arguments.

        Returns:
            BotPreset object.
        """
        return BotPreset(**data)


class BotPreset(db.Model):
    """BotPreset model.

    Attributes:
        id: Unique identifier for the preset.
        name: Name of the preset.
        description: Description of the preset.
        bot_id: Identifier of the bot the preset belongs to.
        bot: Bot object the preset belongs to.
        parameter_values: List of parameter values for the preset.
    """

    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    bot_id = db.Column(db.String, db.ForeignKey("bot.id"))
    bot = db.relationship("Bot", back_populates="presets")

    parameter_values = db.relationship("ParameterValue", secondary="bot_preset_parameter_value", cascade="all")

    def __init__(
        self,
        id: str,  # noqa: A002, ARG002
        name: str,
        description: str,
        bot_id: str,
        parameter_values: list[ParameterValue],
    ) -> None:
        """Initialize a new BotPreset object."""
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.bot_id = bot_id
        self.parameter_values = parameter_values
        self.title = ""
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self) -> None:
        """Reconstruct the BotPreset object."""
        self.title = self.name
        self.subtitle = self.description
        self.tag = "mdi-robot"

    @classmethod
    def find(cls, preset_id: str) -> BotPreset | None:
        """Find a BotPreset object by its identifier.

        Args:
            preset_id: Identifier of the preset.

        Returns:
            BotPreset object.
        """
        return db.session.get(cls, preset_id)

    @classmethod
    def get_all(cls) -> list[BotPreset]:
        """Get all BotPreset objects.

        Returns:
            List of BotPreset objects.
        """
        return cls.query.order_by(db.asc(BotPreset.name)).all()

    @classmethod
    def get(cls, search: str) -> tuple[list[BotPreset], int]:
        """Get all BotPreset objects that match the search string.

        Args:
            search: Search string.

        Returns:
            List of BotPreset objects.
        """
        query = cls.query

        if search is not None:
            search_string = f"%{search}%"
            query = query.filter(or_(BotPreset.name.ilike(search_string), BotPreset.description.ilike(search_string)))

        return query.order_by(db.asc(BotPreset.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search: str) -> dict:
        """Get all BotPreset objects in JSON format.

        Args:
            search: Search string.

        Returns:
            JSON object with the total count and a list of BotPreset objects.
        """
        bots, count = cls.get(search)
        bot_schema = BotPresetPresentationSchema(many=True)
        return {"total_count": count, "items": bot_schema.dump(bots)}

    @classmethod
    def get_all_for_bot_json(cls, bots_node: BotsNode, bot_type: str) -> dict | None:
        """Get all BotPreset objects for a bot in JSON format.

        Args:
            bots_node: Bots Node.
            bot_type: Bot type.

        Returns:
            JSON object with a list of BotPreset objects.
        """
        if bots_node is not None:
            for bot in bots_node.bots:
                if bot.type == bot_type:
                    presets_schema = BotPresetSchema(many=True)
                    return presets_schema.dump(bot.presets)
        return None

    @classmethod
    def add_new(cls, data: dict) -> None:
        """Add a new BotPreset object.

        Args:
            data: Data for the new preset.
        """
        new_preset_schema = NewBotPresetSchema()
        preset = new_preset_schema.load(data)
        db.session.add(preset)
        db.session.commit()

    @classmethod
    def delete(cls, preset_id: str) -> None:
        """Delete a BotPreset object.

        Args:
            preset_id: Identifier of the preset.
        """
        preset = db.session.get(cls, preset_id)
        db.session.delete(preset)
        db.session.commit()

    @classmethod
    def update(cls, preset_id: str, data: dict) -> None:
        """Update a BotPreset object.

        Args:
            preset_id: Identifier of the preset.
            data: Data for the updated preset.
        """
        new_preset_schema = NewBotPresetSchema()
        updated_preset = new_preset_schema.load(data)
        preset = db.session.get(cls, preset_id)
        preset.name = updated_preset.name
        preset.description = updated_preset.description

        # Reassign the preset to a different bot (and possibly a different bots
        # node) when the operator changed bot_id via the GUI. The target bot
        # must already exist and be of the same type as the current bot so
        # that the parameter set is compatible. Parameter values are re-mapped
        # by parameter.key.
        if updated_preset.bot_id and updated_preset.bot_id != preset.bot_id:
            target_bot = db.session.get(Bot, updated_preset.bot_id)
            if target_bot is None:
                msg = f"Target bot {updated_preset.bot_id} not found"
                raise ValueError(msg)
            if target_bot.type != preset.bot.type:
                msg = f"Cannot move preset to bot of type '{target_bot.type}' (preset is bound to type '{preset.bot.type}')"
                raise ValueError(msg)
            preset.bot_id = target_bot.id
            for pv in preset.parameter_values:
                for target_param in target_bot.parameters:
                    if pv.parameter.key == target_param.key:
                        pv.parameter_id = target_param.id
                        break

        for value in preset.parameter_values:
            for updated_value in updated_preset.parameter_values:
                if value.parameter_id == updated_value.parameter_id:
                    value.value = updated_value.value

        db.session.commit()


class BotPresetParameterValue(db.Model):
    """Association table between BotPreset and ParameterValue.

    Attributes:
        bot_preset_id: Identifier of the preset.
        parameter_value_id: Identifier of the parameter value.
    """

    bot_preset_id = db.Column(db.String, db.ForeignKey("bot_preset.id"), primary_key=True)
    parameter_value_id = db.Column(db.Integer, db.ForeignKey("parameter_value.id"), primary_key=True)
