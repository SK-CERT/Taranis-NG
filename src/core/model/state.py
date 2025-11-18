"""State system models."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from model.state import StateDefinition

import logging
from datetime import datetime
from http import HTTPStatus
from typing import ClassVar

from managers.db_manager import db
from marshmallow import post_load
from sqlalchemy import Enum

from shared.common import TZ
from shared.schema.state import StateDefinitionSchema, StateTypeDefinitionSchema

logger = logging.getLogger(__name__)


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

    # @classmethod
    # def get_active_states(cls) -> list[StateDefinition]:
    #     """Get all active state definitions."""
    #     return cls.query.filter_by(is_active=True).order_by(cls.display_name).all()

    @classmethod
    def get_by_id(cls, state_id: int) -> StateDefinition | None:
        """Get state definition by ID."""
        return cls.query.filter_by(id=state_id).first()

    @classmethod
    def get_by_name(cls, display_name: str) -> StateDefinition | None:
        """Get state definition by display name."""
        return cls.query.filter_by(display_name=display_name).first()

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
        # # For non-editable states, only allow is_active changes
        # if not self.editable:
        #     # Allow id and is_active fields for non-editable states
        #     allowed_fields = {"id", "is_active"}
        #     if set(data.keys()).issubset(allowed_fields) and "is_active" in data:
        #         old_is_active = self.is_active
        #         self.is_active = data["is_active"]

        #         # If deactivating, cascade to related state type definitions
        #         if old_is_active and not data["is_active"]:
        #             self.cascade_deactivate_state_types()

        #         db.session.commit()
        #         return self
        #     msg = "This state definition is not editable"
        #     raise ValueError(msg)

        # old_is_active = self.is_active

        schema = StateDefinitionSchema()
        new = schema.load(data)
        self.display_name = new.display_name
        self.description = new.description
        self.color = new.color
        self.icon = new.icon
        self.editable = new.editable
        self.updated_by = user_name
        self.updated_at = datetime.now(TZ)

        # # If deactivating, cascade to related state type definitions
        # if old_is_active and "is_active" in data and not data["is_active"]:
        #     self.cascade_deactivate_state_types()

        db.session.commit()
        return self

    # def cascade_deactivate_state_types(self) -> None:
    #     """Deactivate all state type definitions that use this state definition."""
    #     # Deactivate state type definitions that use this state
    #     state_types = StateTypeDefinition.query.filter_by(state_id=self.id, is_active=True).all()

    #     for state_type in state_types:
    #         state_type.is_active = False

    def delete(self) -> tuple[dict, HTTPStatus]:
        """Delete state definition."""
        if not self.editable:
            return {"error": "This state definition cannot be deleted"}, HTTPStatus.FORBIDDEN

        # Check if state is in use by checking entity state_id columns
        in_use_count = 0

        # Check if any report_items have this state
        try:
            from model.report_item import ReportItem  # noqa: PLC0415

            in_use_count += db.session.query(ReportItem).filter(ReportItem.state_id == self.id).count()
        except Exception as exc:
            logger.exception("Error checking ReportItem usage for state %s: %s", self.id, exc)

        # Check if any products have this state
        try:
            from model.product import Product  # noqa: PLC0415

            in_use_count += db.session.query(Product).filter(Product.state_id == self.id).count()
        except Exception as exc:
            logger.exception("Error checking Product usage for state %s: %s", self.id, exc)

        if in_use_count > 0:
            return {"error": "Cannot delete state definition that is in use"}, HTTPStatus.CONFLICT

        db.session.delete(self)
        db.session.commit()
        return {"message": "State definition deleted successfully"}, HTTPStatus.OK

    # @classmethod
    # def get_states_for_entity_type(cls, entity_type: str) -> list[StateDefinition]:
    #     """Get all active states available for a specific entity type.

    #     Args:
    #         entity_type: The entity type to get states for

    #     Returns:
    #         List of StateDefinition objects
    #     """
    #     return (
    #         db.session.query(cls)
    #         .join(StateTypeDefinition, cls.id == StateTypeDefinition.state_id)
    #         .filter(
    #             StateTypeDefinition.entity_type == entity_type,
    #             StateTypeDefinition.is_active.is_(True),
    #             cls.is_active.is_(True),
    #         )
    #         .all()
    #     )

    # @classmethod
    # def get_states_with_defaults_for_entity_type(cls, entity_type: str) -> list[tuple[StateDefinition, bool]]:
    #     """Get all states available for an entity type with default indicators.

    #     Args:
    #         entity_type: The entity type to get states for

    #     Returns:
    #         List of tuples containing (StateDefinition, is_default)
    #     """
    #     try:
    #         query = (
    #             db.session.query(cls, StateTypeDefinition.state_type)
    #             .join(StateTypeDefinition, cls.id == StateTypeDefinition.state_id)
    #             .filter(
    #                 StateTypeDefinition.entity_type == entity_type,
    #                 StateTypeDefinition.is_active.is_(True),
    #                 cls.is_active.is_(True),
    #             )
    #         )

    #         return [(state_def, state_type == "default") for state_def, state_type in query.all()]
    #     except Exception as error:
    #         # If there's an error (e.g., tables don't exist), return empty list
    #         logger.exception(f"Error getting states for entity type {entity_type}: {error}")
    #         return []

    # def is_applicable_to(self, entity_type: str) -> bool:
    #     """Check if this state can be applied to the given entity type."""
    #     # Use a single combined predicate for the EXISTS() where-clause to avoid
    #     # passing multiple positional arguments to where(), which may raise at
    #     # runtime with some SQLAlchemy versions. This mirrors usage elsewhere
    #     # in the codebase (see model/news_item.py).
    #     return db.session.query(
    #         exists().where(
    #             and_(
    #                 StateTypeDefinition.entity_type == entity_type,
    #                 StateTypeDefinition.state_id == self.id,
    #             ),
    #         ),
    #     ).scalar()


class NewStateTypeDefinitionSchema(StateTypeDefinitionSchema):
    """New State type Schema."""

    @post_load
    def make(self, data: dict, **kwargs) -> StateTypeDefinition:  # noqa: ARG002, ANN003
        """Create a new State type.

        Args:
            data (dict): Data to create the new State type.
            **kwargs: Additional keyword arguments.

        Returns:
            StateTypeDefinition: New State type object.
        """
        return StateTypeDefinition(**data)


class StateTypeDefinition(db.Model):
    """Defines which states are allowed for which entity types with additional metadata."""

    __tablename__ = "state_entity_type"

    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(Enum("report_item", "product", name="entity_type_enum"), nullable=False)
    state_id = db.Column(db.Integer, db.ForeignKey("state.id"), nullable=False)
    state_type = db.Column(Enum("normal", "default", "final", name="state_type_enum"), default="normal")
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
            entity_type (str): entity type filter.

        Returns:
            dict: Dictionary containing total count and list of state types in JSON format.
        """
        query = cls.query
        if entity_type:
            query = query.filter(StateTypeDefinition.entity_type == entity_type)
        results = query.order_by(StateTypeDefinition.entity_type, StateTypeDefinition.sort_order).all()

        schema = StateTypeDefinitionSchema(many=True)
        return {"total_count": len(results), "items": schema.dump(results)}, HTTPStatus.OK

    @classmethod
    def add_new(cls, data: dict, user_name: str) -> StateTypeDefinition:
        """Create a new state type."""
        schema = NewStateTypeDefinitionSchema()
        new = schema.load(data)
        new.updated_by = user_name
        new.updated_at = datetime.now(TZ)
        db.session.add(new)
        db.session.commit()
        return new

    def update(self, data: dict, user_name: str) -> StateTypeDefinition:
        """Update state type definition."""
        schema = StateTypeDefinitionSchema()
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

    @classmethod
    def get_allowed_states(cls, entity_type: str) -> list[StateDefinition]:
        """Get all states allowed for a specific entity type."""
        return (
            db.session.query(StateDefinition)
            .join(cls)
            .filter(cls.entity_type == entity_type)
            .filter(cls.is_active.is_(True))
            .order_by(cls.sort_order)
            .all()
        )

    # @classmethod
    # def get_default_statesget_default_states(cls, entity_type: str) -> list[StateDefinition]:
    #     """Get default states for a specific entity type."""
    #     return (
    #         db.session.query(StateDefinition)
    #         .join(cls)
    #         .filter(cls.entity_type == entity_type, cls.state_type == "default", cls.is_active.is_(True))
    #         .filter(StateDefinition.is_active.is_(True))
    #         .order_by(cls.sort_order)
    #         .all()
    #     )

    @classmethod
    def is_state_allowed(cls, entity_type: str, state_name: str) -> bool:
        """Check if a state is allowed for an entity type."""
        result = (
            db.session.query(cls)
            .join(StateDefinition)
            .filter(cls.entity_type == entity_type)
            .filter(cls.is_active.is_(True))
            .filter(StateDefinition.display_name == state_name)
            .first()
        )

        return result is not None


class StateManager:
    """Manages state operations for entities with generic, flexible methods."""

    # Entity type constants
    ENTITY_REPORT_ITEM = "report_item"
    ENTITY_PRODUCT = "product"

    # Valid entity types (removed news_item_aggregate as it won't have state_id column)
    VALID_ENTITY_TYPES: ClassVar[set[str]] = {ENTITY_REPORT_ITEM, ENTITY_PRODUCT}

    @staticmethod
    def validate_entity_type(entity_type: str) -> bool:
        """Validate that entity type is supported."""
        return entity_type in StateManager.VALID_ENTITY_TYPES

    @staticmethod
    def get_allowed_states(entity_type: str) -> list[str]:
        """Get list of state names allowed for an entity type."""
        if not StateManager.validate_entity_type(entity_type):
            return []

        allowed_states = StateTypeDefinition.get_allowed_states(entity_type)
        return [state.display_name for state in allowed_states]

    @staticmethod
    def is_state_allowed(entity_type: str, state_name: str) -> bool:
        """Check if a state is allowed for an entity type."""
        if not StateManager.validate_entity_type(entity_type):
            return False

        return StateTypeDefinition.is_state_allowed(entity_type, state_name)

    @staticmethod
    def set_state(
        entity_type: str,
        entity_id: int,
        state_id: int,
    ) -> bool:
        """Set a state for an entity using the state_id column.

        Args:
            entity_type: Type of entity ('report_item', 'product')
            entity_id: ID of the entity
            state_id: ID of the state to set

        Returns:
            bool: True if state was set successfully, False otherwise
        """
        # Validate entity type
        if not StateManager.validate_entity_type(entity_type):
            logger.debug(f"Invalid entity type: {entity_type}")
            return False

        # Ensure entity_id is an integer
        try:
            entity_id = int(entity_id)
        except (TypeError, ValueError):
            logger.debug(f"Invalid entity_id: {entity_id}")
            return False

        state_def = StateDefinition.get_by_id(state_id)
        if not state_def:
            logger.debug(f"State definition not found: {state_id}")
            return False

        # Validate state is allowed for this entity type
        if not StateManager.is_state_allowed(entity_type, state_def.display_name):
            logger.debug(f"State '{state_def.display_name}' not allowed for entity type '{entity_type}'")
            return False

        # Update the entity's state_id column
        try:
            if entity_type == StateManager.ENTITY_REPORT_ITEM:
                from model.report_item import ReportItem  # noqa: PLC0415

                report_item = ReportItem.find(entity_id)
                if report_item:
                    report_item.state_id = state_id
                    return True
            elif entity_type == StateManager.ENTITY_PRODUCT:
                from model.product import Product  # noqa: PLC0415

                product = Product.find(entity_id)
                if product:
                    product.state_id = state_id
                    return True

            logger.debug(f"Entity not found: {entity_type}:{entity_id}")
            return False

        except Exception as error:
            logger.exception(f"Error setting state for {entity_type}:{entity_id}: {error}")
            return False

    @staticmethod
    def remove_state(entity_type: str, entity_id: str) -> bool:
        """Remove a state from an entity by setting state_id to None.

        Args:
            entity_type: Type of entity ('report_item', 'product')
            entity_id: ID of the entity

        Returns:
            bool: True if state was removed successfully, False otherwise
        """
        # Coerce entity_id to int for safety
        try:
            entity_id = int(entity_id)
        except (TypeError, ValueError):
            logger.debug(f"Invalid entity_id provided to StateManager.remove_state: {entity_id}")
            return False

        try:
            if entity_type == StateManager.ENTITY_REPORT_ITEM:
                from model.report_item import ReportItem  # noqa: PLC0415

                report_item = ReportItem.find(entity_id)
                if report_item:
                    report_item.state_id = None
                    return True
            elif entity_type == StateManager.ENTITY_PRODUCT:
                from model.product import Product  # noqa: PLC0415

                product = Product.find(entity_id)
                if product:
                    product.state_id = None
                    return True

            logger.debug(f"Entity not found: {entity_type}:{entity_id}")
            return False

        except Exception as e:
            logger.exception(f"Error removing state for {entity_type}:{entity_id}: {e}")
            return False

    @staticmethod
    def has_state(entity_type: str, entity_id: int, state_name: str) -> bool:
        """Check if an entity has a specific state.

        Args:
            entity_type: Type of entity ('report_item', 'product')
            entity_id: ID of the entity
            state_name: Name of the state to check

        Returns:
            bool: True if entity has the state, False otherwise
        """
        # Validate entity type
        if not StateManager.validate_entity_type(entity_type):
            return False

        # Get state definition
        state_def = StateDefinition.get_by_name(state_name)
        if not state_def:
            return False

        # Check if entity has this state
        try:
            if entity_type == StateManager.ENTITY_REPORT_ITEM:
                from model.report_item import ReportItem  # noqa: PLC0415

                report_item = ReportItem.find(entity_id)
                return report_item and report_item.state_id == state_def.id
            if entity_type == StateManager.ENTITY_PRODUCT:
                from model.product import Product  # noqa: PLC0415

                product = Product.find(entity_id)
                return product and product.state_id == state_def.id

            return False

        except Exception:
            return False

    @staticmethod
    def set_state_by_name(
        entity_type: str,
        entity_id: int,
        state_name: str | None = None,
        commit: bool = True,
    ) -> bool:
        """Set a state for an entity by name (replaces any existing state).

        Args:
            entity_type: Type of entity
            entity_id: ID of the entity
            state_name: Name of the state to set (None to remove current state)
            commit: Whether to commit the transaction

        Returns:
            bool: True if state was set successfully, False otherwise
        """
        if not state_name:
            # No state provided - remove current state
            success = StateManager.remove_state(entity_type, entity_id, None)
        else:
            # Set the specified state
            state_def = StateDefinition.get_by_name(state_name)
            success = StateManager.set_state(entity_type, entity_id, state_def.id) if state_def else False

        if commit:
            db.session.commit()

        return success

    @staticmethod
    def remove_current_state(entity_type: str, entity_id: int, user_id: int | None = None, commit: bool = True) -> bool:
        """Remove current state from an entity (clears the state_id).

        Args:
            entity_type: Type of entity
            entity_id: ID of the entity
            user_id: ID of the user performing the action
            commit: Whether to commit the transaction

        Returns:
            bool: True if state was removed successfully, False otherwise
        """
        # Clear the entity's current state
        success = StateManager.remove_state(entity_type, entity_id, None, user_id)

        if commit:
            db.session.commit()

        return success

    # @staticmethod
    # def transition_state(
    #     entity_type: str,
    #     entity_id: int,
    #     from_state: str,
    #     to_state: str,
    #     commit: bool = True,
    # ) -> bool:
    #     """Transition from one state to another (replaces current state).

    #     Args:
    #         entity_type: Type of entity
    #         entity_id: ID of the entity
    #         from_state: Current state to check (optional validation)
    #         to_state: New state to set
    #         commit: Whether to commit the transaction

    #     Returns:
    #         bool: True if transition was successful, False otherwise
    #     """
    #     # Optionally validate current state matches from_state
    #     if from_state and not StateManager.has_state(entity_type, entity_id, from_state):
    #         logger.debug(f"Entity {entity_type}:{entity_id} does not have expected from_state '{from_state}'")
    #         # Continue anyway since we're replacing the state

    #     # Set new state (this replaces any existing state)
    #     to_state_def = StateDefinition.get_by_name(to_state)
    #     if not to_state_def:
    #         logger.debug(f"State definition not found: {to_state}")
    #         return False

    #     success = StateManager.set_state(entity_type, entity_id, to_state_def.id)

    #     if commit:
    #         db.session.commit()

    #     return success

    # @staticmethod
    # def replace_state(
    #     entity_type: str,
    #     entity_id: int,
    #     new_state: str | None = None,
    #     commit: bool = True,
    # ) -> bool:
    #     """Replace current state with a new state.

    #     Args:
    #         entity_type: Type of entity
    #         entity_id: ID of the entity
    #         new_state: New state to set (None to remove current state)
    #         commit: Whether to commit the transaction

    #     Returns:
    #         bool: True if replacement was successful, False otherwise
    #     """
    #     success = True

    #     # Set new state (this automatically replaces any existing state)
    #     if new_state:
    #         state_def = StateDefinition.get_by_name(new_state)
    #         success = StateManager.set_state(entity_type, entity_id, state_def.id) if state_def else False
    #     else:
    #         # No new state - remove current state
    #         success = StateManager.remove_state(entity_type, entity_id, None)

    #     if commit:
    #         db.session.commit()

    #     return success
