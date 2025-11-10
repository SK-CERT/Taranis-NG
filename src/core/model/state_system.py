"""State system models."""

import logging
from datetime import datetime
from typing import ClassVar, Optional

from managers.db_manager import db
from sqlalchemy import Enum, and_, exists

logger = logging.getLogger(__name__)


class StateDefinition(db.Model):
    """Definition of a state that can be assigned to entities."""

    __tablename__ = "state"

    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    color = db.Column(db.String(7))  # Hex color code
    icon = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    editable = db.Column(db.Boolean, default=True)
    created = db.Column(db.DateTime, default=datetime.now)

    @classmethod
    def get_active_states(cls) -> list["StateDefinition"]:
        """Get all active state definitions."""
        return cls.query.filter_by(is_active=True).order_by(cls.display_name).all()

    @classmethod
    def get_by_id(cls, state_id: int) -> Optional["StateDefinition"]:
        """Get state definition by ID."""
        return cls.query.filter_by(id=state_id, is_active=True).first()

    @classmethod
    def get_by_name(cls, display_name: str) -> Optional["StateDefinition"]:
        """Get state definition by display name."""
        return cls.query.filter_by(display_name=display_name, is_active=True).first()

    @classmethod
    def get_all_json(cls, search: str | None = None) -> dict:
        """Get all state definitions in JSON format."""
        query = cls.query
        if search:
            query = query.filter(db.or_(cls.display_name.ilike(f"%{search}%"), cls.description.ilike(f"%{search}%")))

        state_definitions = query.order_by(cls.display_name).all()

        items = [
            {
                "id": state_def.id,
                "display_name": state_def.display_name,
                "description": state_def.description,
                "color": state_def.color,
                "icon": state_def.icon,
                "is_active": state_def.is_active,
                "editable": state_def.editable,
                "created": state_def.created.isoformat() if state_def.created else None,
            }
            for state_def in state_definitions
        ]

        return {"total_count": len(items), "items": items}

    @classmethod
    def add_new(cls, data: dict) -> "StateDefinition":
        """Create a new state definition."""
        state_def = cls(
            display_name=data.get("display_name"),
            description=data.get("description"),
            color=data.get("color"),
            icon=data.get("icon"),
            is_active=data.get("is_active", True),
            editable=data.get("editable", True),
        )

        db.session.add(state_def)
        db.session.commit()
        return state_def

    def update(self, data: dict) -> "StateDefinition":
        """Update state definition."""
        # For non-editable states, only allow is_active changes
        if not self.editable:
            # Allow id and is_active fields for non-editable states
            allowed_fields = {"id", "is_active"}
            if set(data.keys()).issubset(allowed_fields) and "is_active" in data:
                old_is_active = self.is_active
                self.is_active = data["is_active"]

                # If deactivating, cascade to related state type definitions
                if old_is_active and not data["is_active"]:
                    self.cascade_deactivate_state_types()

                db.session.commit()
                return self
            msg = "This state definition is not editable"
            raise ValueError(msg)

        old_is_active = self.is_active

        if "display_name" in data:
            self.display_name = data["display_name"]
        if "description" in data:
            self.description = data["description"]
        if "color" in data:
            self.color = data["color"]
        if "icon" in data:
            self.icon = data["icon"]
        if "is_active" in data:
            self.is_active = data["is_active"]
        if "editable" in data:
            self.editable = data["editable"]

        # If deactivating, cascade to related state type definitions
        if old_is_active and "is_active" in data and not data["is_active"]:
            self.cascade_deactivate_state_types()

        db.session.commit()
        return self

    def cascade_deactivate_state_types(self) -> None:
        """Deactivate all state type definitions that use this state definition."""
        # Deactivate state type definitions that use this state
        state_types = StateTypeDefinition.query.filter_by(state_id=self.id, is_active=True).all()

        for state_type in state_types:
            state_type.is_active = False

    def delete(self) -> tuple[dict, int]:
        """Delete state definition."""
        if not self.editable:
            return {"error": "This state definition cannot be deleted"}, 403

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
            return {"error": "Cannot delete state definition that is in use"}, 409

        db.session.delete(self)
        db.session.commit()
        return {"message": "State definition deleted successfully"}, 200

    @classmethod
    def get_states_for_entity_type(cls, entity_type: str) -> list["StateDefinition"]:
        """Get all active states available for a specific entity type.

        Args:
            entity_type: The entity type to get states for

        Returns:
            List of StateDefinition objects
        """
        return (
            db.session.query(cls)
            .join(StateTypeDefinition, cls.id == StateTypeDefinition.state_id)
            .filter(
                StateTypeDefinition.entity_type == entity_type,
                StateTypeDefinition.is_active.is_(True),
                cls.is_active.is_(True),
            )
            .all()
        )

    @classmethod
    def get_states_with_defaults_for_entity_type(cls, entity_type: str) -> list[tuple["StateDefinition", bool]]:
        """Get all states available for an entity type with default indicators.

        Args:
            entity_type: The entity type to get states for

        Returns:
            List of tuples containing (StateDefinition, is_default)
        """
        try:
            query = (
                db.session.query(cls, StateTypeDefinition.state_type)
                .join(StateTypeDefinition, cls.id == StateTypeDefinition.state_id)
                .filter(
                    StateTypeDefinition.entity_type == entity_type,
                    StateTypeDefinition.is_active.is_(True),
                    cls.is_active.is_(True),
                )
            )

            return [(state_def, state_type == "default") for state_def, state_type in query.all()]
        except Exception as error:
            # If there's an error (e.g., tables don't exist), return empty list
            logger.exception(f"Error getting states for entity type {entity_type}: {error}")
            return []

    def is_applicable_to(self, entity_type: str) -> bool:
        """Check if this state can be applied to the given entity type."""
        # Use a single combined predicate for the EXISTS() where-clause to avoid
        # passing multiple positional arguments to where(), which may raise at
        # runtime with some SQLAlchemy versions. This mirrors usage elsewhere
        # in the codebase (see model/news_item.py).
        return db.session.query(
            exists().where(
                and_(
                    StateTypeDefinition.entity_type == entity_type,
                    StateTypeDefinition.state_id == self.id,
                ),
            ),
        ).scalar()


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
    created = db.Column(db.DateTime, default=datetime.now)

    state_definition = db.relationship("StateDefinition")

    __table_args__ = (db.UniqueConstraint("entity_type", "state_id", name="unique_state_type"),)

    @classmethod
    def get_allowed_states(cls, entity_type: str) -> list["StateDefinition"]:
        """Get all states allowed for a specific entity type."""
        return (
            db.session.query(StateDefinition)
            .join(cls)
            .filter(cls.entity_type == entity_type)
            .filter(cls.is_active.is_(True))
            .order_by(cls.sort_order)
            .all()
        )

    @classmethod
    def get_default_states(cls, entity_type: str) -> list["StateDefinition"]:
        """Get default states for a specific entity type."""
        return (
            db.session.query(StateDefinition)
            .join(cls)
            .filter(cls.entity_type == entity_type, cls.state_type == "default", cls.is_active.is_(True))
            .filter(StateDefinition.is_active.is_(True))
            .order_by(cls.sort_order)
            .all()
        )

    @classmethod
    def is_state_allowed(cls, entity_type: str, state_name: str) -> bool:
        """Check if a state is allowed for an entity type."""
        result = (
            db.session.query(cls)
            .join(StateDefinition)
            .filter(cls.entity_type == entity_type)
            .filter(cls.is_active.is_(True))
            .filter(StateDefinition.display_name == state_name)
            .filter(StateDefinition.is_active.is_(True))
            .first()
        )

        return result is not None

    def update(self, data: dict) -> "StateTypeDefinition":
        """Update state type definition."""
        # Only allow updating of certain fields
        if "state_type" in data:
            self.state_type = data["state_type"]
        if "is_active" in data:
            self.is_active = data["is_active"]
        if "editable" in data:
            self.editable = data["editable"]
        if "sort_order" in data:
            self.sort_order = data["sort_order"]

        db.session.commit()
        return self


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

                report_item = ReportItem.query.get(entity_id)
                if report_item:
                    report_item.state_id = state_id
                    return True
            elif entity_type == StateManager.ENTITY_PRODUCT:
                from model.product import Product  # noqa: PLC0415

                product = Product.query.get(entity_id)
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

                report_item = ReportItem.query.get(entity_id)
                if report_item:
                    report_item.state_id = None
                    return True
            elif entity_type == StateManager.ENTITY_PRODUCT:
                from model.product import Product  # noqa: PLC0415

                product = Product.query.get(entity_id)
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

                report_item = ReportItem.query.get(entity_id)
                return report_item and report_item.state_id == state_def.id
            if entity_type == StateManager.ENTITY_PRODUCT:
                from model.product import Product  # noqa: PLC0415

                product = Product.query.get(entity_id)
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

    @staticmethod
    def transition_state(
        entity_type: str,
        entity_id: int,
        from_state: str,
        to_state: str,
        commit: bool = True,
    ) -> bool:
        """Transition from one state to another (replaces current state).

        Args:
            entity_type: Type of entity
            entity_id: ID of the entity
            from_state: Current state to check (optional validation)
            to_state: New state to set
            commit: Whether to commit the transaction

        Returns:
            bool: True if transition was successful, False otherwise
        """
        # Optionally validate current state matches from_state
        if from_state and not StateManager.has_state(entity_type, entity_id, from_state):
            logger.debug(f"Entity {entity_type}:{entity_id} does not have expected from_state '{from_state}'")
            # Continue anyway since we're replacing the state

        # Set new state (this replaces any existing state)
        to_state_def = StateDefinition.get_by_name(to_state)
        if not to_state_def:
            logger.debug(f"State definition not found: {to_state}")
            return False

        success = StateManager.set_state(entity_type, entity_id, to_state_def.id)

        if commit:
            db.session.commit()

        return success

    @staticmethod
    def replace_state(
        entity_type: str,
        entity_id: int,
        new_state: str | None = None,
        commit: bool = True,
    ) -> bool:
        """Replace current state with a new state.

        Args:
            entity_type: Type of entity
            entity_id: ID of the entity
            new_state: New state to set (None to remove current state)
            commit: Whether to commit the transaction

        Returns:
            bool: True if replacement was successful, False otherwise
        """
        success = True

        # Set new state (this automatically replaces any existing state)
        if new_state:
            state_def = StateDefinition.get_by_name(new_state)
            success = StateManager.set_state(entity_type, entity_id, state_def.id) if state_def else False
        else:
            # No new state - remove current state
            success = StateManager.remove_state(entity_type, entity_id, None)

        if commit:
            db.session.commit()

        return success
