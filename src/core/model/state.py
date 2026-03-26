"""State system models."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from model.state import StateDefinition
    from model.user import User

import logging
from datetime import datetime
from enum import Enum as PyEnum  # to avoid name clash with SQLAlchemy Enum
from http import HTTPStatus

from managers.db_manager import db
from marshmallow import post_load
from model.setting import Setting
from shared.common import TZ
from shared.schema.state import StateDefinitionSchema, StateEntityTypeSchema
from sqlalchemy import Enum

logger = logging.getLogger(__name__)


class StateEnum(PyEnum):
    """States."""

    COMPLETED = "completed"
    PUBLISHED = "published"
    WORK_IN_PROGRESS = "work_in_progress"


class StateEntityTypeEnum(PyEnum):
    """State entity types."""

    PRODUCT = "product"
    REPORT_ITEM = "report_item"


class StateTypeEnum(PyEnum):
    """State types."""

    NORMAL = "normal"
    INITIAL = "initial"
    FINAL = "final"


class NewStateDefinitionSchema(StateDefinitionSchema):
    """New StateDefinition Schema."""

    @post_load
    def make(self, data: dict, **kwargs) -> StateDefinition:  # noqa: ARG002, ANN003
        """Create a new StateDefinition.

        Args:
            data (dict): Data to create the new StateDefinition.
            **kwargs: Additional keyword arguments.

        Returns:
            StateDefinition: New StateDefinition object.
        """
        return StateDefinition(**data)


class StateDefinition(db.Model):
    """Definition of a state that can be assigned to entities."""

    __tablename__ = "state"

    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    color = db.Column(db.String(7))  # Hex color code
    icon = db.Column(db.String(50))
    editable = db.Column(db.Boolean, default=True)
    updated_by = db.Column(db.String())
    updated_at = db.Column(db.DateTime)

    @classmethod
    def get_by_name(cls, display_name: str) -> StateDefinition | None:
        """Get state definition by display name."""
        return cls.query.filter_by(display_name=display_name).first()

    @classmethod
    def get_initial_state(cls, entity_type: str) -> StateDefinition | None:
        """Get the initial state for an entity type.

        Args:
            entity_type: The entity type (e.g., "report_item", "product")

        Returns:
            StateDefinition: The initial state for the entity type, or None if not found
        """
        return cls.get_state_for_entity_type(entity_type, StateTypeEnum.INITIAL.value)

    @classmethod
    def get_final_state(cls, entity_type: str) -> StateDefinition | None:
        """Get the FINAL state definition for an entity type.

        Retrieves the state marked as FINAL for the given entity type (e.g., REPORT_ITEM, PRODUCT).
        This is used when cascading state changes to automatically transition entities to completion.

        Args:
            entity_type: The entity type (e.g., "report_item", "product")

        Returns:
            StateDefinition: The FINAL state for the entity type, or None if not found
        """
        return cls.get_state_for_entity_type(entity_type, StateTypeEnum.FINAL.value)

    @classmethod
    def get_state_for_entity_type(cls, entity_type: str, state_type: StateTypeEnum) -> StateDefinition | None:
        """Get the state definition for an entity type.

        Retrieves the state for the given entity type (e.g., REPORT_ITEM, PRODUCT).

        Args:
            entity_type: The entity type (e.g., "report_item", "product")
            state_type: The state type (e.g., StateTypeEnum.FINAL.value)

        Returns:
            StateDefinition: The state for the entity type, or None if not found
        """
        try:
            return (
                db.session.query(StateDefinition)
                .join(StateEntityType, StateEntityType.state_id == StateDefinition.id)
                .filter(
                    StateEntityType.entity_type == entity_type,
                    StateEntityType.state_type == state_type,
                    StateEntityType.is_active.is_(True),
                )
                .order_by(db.asc(StateEntityType.sort_order))
                .first()
            )
        except Exception as error:
            logger.exception(f"Failed to get state for entity type {entity_type} and state type {state_type}: {error}")
            return None

    @classmethod
    def get_all_json(cls, search: str | None = None) -> tuple[dict, HTTPStatus]:
        """Get all state definitions in JSON format."""
        query = cls.query
        if search:
            query = query.filter(db.or_(cls.display_name.ilike(f"%{search}%"), cls.description.ilike(f"%{search}%")))
        results = query.order_by(cls.display_name).all()

        schema = StateDefinitionSchema(many=True)
        return {"total_count": len(results), "items": schema.dump(results)}, HTTPStatus.OK

    @classmethod
    def get_full_by_entity_json(cls, entity_type: str, include_inactive: bool | None = None) -> dict:
        """Get states by entity type in JSON format."""
        query = (
            db.session.query(StateEntityType, StateDefinition)
            .join(StateDefinition, StateEntityType.state_id == StateDefinition.id)
            .filter(StateEntityType.entity_type == entity_type)
        )
        if not include_inactive:
            query = query.filter(StateEntityType.is_active.is_(True))
        records = query.order_by(StateEntityType.sort_order, StateDefinition.display_name).all()

        result = []
        for state_type_def, state in records:
            result.append(
                {
                    "id": state.id,
                    "display_name": state.display_name,
                    "description": state.description,
                    "color": state.color,
                    "icon": state.icon,
                    "is_default": state_type_def.state_type == StateTypeEnum.INITIAL.value,
                    "is_active": state_type_def.is_active,
                    "state_type": state_type_def.state_type,
                    "sort_order": state_type_def.sort_order,
                },
            )

        return {"entity_type": entity_type, "states": result, "include_inactive": include_inactive}

    @classmethod
    def add_new(cls, data: dict, user_name: str) -> StateDefinition:
        """Create a new state definition."""
        schema = NewStateDefinitionSchema()
        new = schema.load(data)
        new.updated_by = user_name
        new.updated_at = datetime.now(TZ)
        db.session.add(new)
        db.session.commit()
        return new

    def update(self, data: dict, user_name: str) -> StateDefinition:
        """Update state definition."""
        schema = StateDefinitionSchema()
        new = schema.load(data)
        self.display_name = new.display_name
        self.description = new.description
        self.color = new.color
        self.icon = new.icon
        self.editable = new.editable
        self.updated_by = user_name
        self.updated_at = datetime.now(TZ)

        db.session.commit()
        return self

    def delete(self) -> tuple[dict, HTTPStatus]:
        """Delete state definition."""
        if not self.editable:
            return {"error": "This state definition cannot be deleted"}, HTTPStatus.FORBIDDEN

        db.session.delete(self)
        db.session.commit()
        return {"message": "State definition deleted successfully"}, HTTPStatus.OK


class NewStateEntityTypeSchema(StateEntityTypeSchema):
    """New State type Schema."""

    @post_load
    def make(self, data: dict, **kwargs) -> StateEntityType:  # noqa: ARG002, ANN003
        """Create a new State type.

        Args:
            data (dict): Data to create the new State type.
            **kwargs: Additional keyword arguments.

        Returns:
            StateEntityType: New State type object.
        """
        return StateEntityType(**data)


class StateEntityType(db.Model):
    """Defines which states are allowed for which entity types with additional metadata."""

    __tablename__ = "state_entity_type"

    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(
        Enum(StateEntityTypeEnum.REPORT_ITEM.value, StateEntityTypeEnum.PRODUCT.value, name="entity_type_enum"),
        nullable=False,
    )
    state_id = db.Column(db.Integer, db.ForeignKey("state.id"), nullable=False)
    state_type = db.Column(
        Enum(StateTypeEnum.NORMAL.value, StateTypeEnum.INITIAL.value, StateTypeEnum.FINAL.value, name="state_type_enum"),
        default=StateTypeEnum.NORMAL.value,
    )
    is_active = db.Column(db.Boolean, default=True)
    editable = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    updated_by = db.Column(db.String())
    updated_at = db.Column(db.DateTime)

    state = db.relationship(StateDefinition)

    __table_args__ = (db.UniqueConstraint("entity_type", "state_id", name="unique_state_type"),)

    @classmethod
    def get_all_json(cls, entity_type: str | None = None) -> tuple[dict, HTTPStatus]:
        """Get all state types in JSON format based on a search query.

        Args:
            entity_type (str | None): entity type filter.

        Returns:
            dict: Dictionary containing total count and list of state types in JSON format.
        """
        query = cls.query
        if entity_type:
            query = query.filter(StateEntityType.entity_type == entity_type)
        results = query.order_by(StateEntityType.entity_type, StateEntityType.sort_order).all()

        schema = StateEntityTypeSchema(many=True)
        return {"total_count": len(results), "items": schema.dump(results)}, HTTPStatus.OK

    @classmethod
    def add_new(cls, data: dict, user_name: str) -> StateEntityType:
        """Create a new state type."""
        schema = NewStateEntityTypeSchema()
        new = schema.load(data)
        new.updated_by = user_name
        new.updated_at = datetime.now(TZ)
        db.session.add(new)
        db.session.commit()
        return new

    def update(self, data: dict, user_name: str) -> StateEntityType:
        """Update state type definition."""
        schema = StateEntityTypeSchema()
        new = schema.load(data)
        self.entity_type = new.entity_type
        self.state_id = new.state_id
        self.state_type = new.state_type
        self.is_active = new.is_active
        self.sort_order = new.sort_order
        self.editable = True  # user state types are always editable
        self.updated_by = user_name
        self.updated_at = datetime.now(TZ)

        db.session.commit()
        return self


class StateManager:
    """Manages state operations for entities with generic, flexible methods."""

    @staticmethod
    def is_this_state_same_as(state_id: int, state_enum: StateEnum) -> bool:
        """Check if a State ID belongs to the State name.

        Can be used in case when entity record isn't created yet (doesn't have ID).

        Args:
            state_id: ID of the state
            state_enum: StateEnum value to compare against
        Returns:
            bool: True if the state ID matches the state name, False otherwise
        """
        try:
            state = StateDefinition.get_by_name(state_enum.value)
            return state and state.id == state_id

        except Exception as exc:
            logger.exception(f"Failed to check if state {state_id} is same as {state_enum}: {exc}")
            return False

    @staticmethod
    def is_final_state(state_id: int, entity_type: str) -> bool:
        """Check if a given state is a FINAL state for an entity type.

        Args:
            state_id: The state ID to check
            entity_type: The entity type (e.g., "REPORT_ITEM" or "PRODUCT")

        Returns:
            bool: True if the state is a FINAL state, False otherwise
        """
        try:
            if not state_id:
                return False

            state_entity = (
                db.session.query(StateEntityType)
                .filter_by(
                    entity_type=entity_type,
                    state_id=state_id,
                )
                .first()
            )

            if not state_entity:
                return False
            return state_entity.state_type == StateTypeEnum.FINAL.value

        except Exception as error:
            logger.exception(f"Failed to check if state {state_id} for {entity_type} is final: {error}")
            return False

    @staticmethod
    def should_mark_as_read(state_id: int, entity_type: str) -> bool:
        """Determine if news items should be marked as READ for this state.

        A news item should be marked as read when transitioning to a FINAL state.

        Args:
            state_id: The new state ID
            entity_type: The entity type (e.g., "REPORT_ITEM")

        Returns:
            bool: True if news items should be marked as read, False otherwise
        """
        return StateManager.is_final_state(state_id, entity_type)

    @staticmethod
    def should_mark_as_unread(state_id: int, entity_type: str) -> bool:
        """Determine if news items should be marked as UNREAD for this state.

        A news item should be marked as unread when transitioning to a non-FINAL state.

        Args:
            state_id: The new state ID
            entity_type: The entity type (e.g., "REPORT_ITEM")

        Returns:
            bool: True if news items should be marked as unread, False otherwise
        """
        return not StateManager.is_final_state(state_id, entity_type)

    @staticmethod
    def is_cascade_states_enabled(user: User) -> bool:
        """Check if cascade states feature is enabled for the given user.

        The CASCADE_STATES_ENABLED setting is global, so all users see the same value.
        This method uses the global setting with a default of True (enabled).

        Args:
            user: The user to check the setting for

        Returns:
            bool: True if cascade states is enabled, False otherwise
        """
        try:
            return Setting.get_setting_bool(user, "CASCADE_STATES_ENABLED", default_value=True)
        except Exception as error:
            logger.exception(f"Failed to check if cascade states is enabled: {error}")
            return True  # Default enabled
