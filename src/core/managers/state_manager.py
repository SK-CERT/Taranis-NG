"""State management utilities."""

import logging

from managers.db_manager import db
from model.setting import Setting
from model.state import StateDefinition, StateEntityType, StateTypeEnum
from model.user import User

logger = logging.getLogger(__name__)


class StateManagementUtilities:
    """Utilities for managing the state system."""

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
            logger.exception(f"Failed to check if state is final: {error}")
            # Rollback any failed transaction to reset session state
            db.session.rollback()
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
        return StateManagementUtilities.is_final_state(state_id, entity_type)

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
        return not StateManagementUtilities.is_final_state(state_id, entity_type)

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
            # Rollback any failed transaction to reset session state
            db.session.rollback()
            return True  # Default to enabled if we can't read setting

    @staticmethod
    def get_final_state_for_entity_type(entity_type: str) -> StateDefinition | None:
        """Get the FINAL state definition for an entity type.

        Retrieves the state marked as FINAL for the given entity type (e.g., REPORT_ITEM, PRODUCT).
        This is used when cascading state changes to automatically transition entities to completion.

        Args:
            entity_type: The entity type (e.g., "report_item", "product")

        Returns:
            StateDefinition: The FINAL state for the entity type, or None if not found
        """
        try:
            return (
                db.session.query(StateDefinition)
                .join(StateEntityType, StateDefinition.id == StateEntityType.state_id)
                .filter(
                    StateEntityType.entity_type == entity_type,
                    StateEntityType.state_type == StateTypeEnum.FINAL.value,
                    StateEntityType.is_active.is_(True),
                )
                .first()
            )
        except Exception as error:
            logger.exception(f"Failed to get final state for entity type {entity_type}: {error}")
            db.session.rollback()
            return None
