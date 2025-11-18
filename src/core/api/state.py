"""State management API endpoints."""

import traceback
from http import HTTPStatus

from flask import request
from flask_restful import Resource
from managers import auth_manager
from managers.auth_manager import auth_required
from managers.db_manager import db
from managers.sse_manager import sse_manager
from managers.state_manager import StateManagementUtilities
from model.product import Product
from model.report_item import ReportItem
from model.state import StateDefinition, StateManager, StateTypeDefinition

from shared.log_manager import logger

# class StateSync(Resource):
#     """State synchronization endpoint."""

#     @auth_required("ASSESS_CREATE")  # Require admin permissions for state sync
#     def post(self) -> dict:
#         """Synchronize all states in the system.

#         Returns:
#             dict: Synchronization results
#         """
#         return StateManagementUtilities.sync_all_states()


class StateStatistics(Resource):
    """State statistics endpoint."""

    @auth_required("ASSESS_ACCESS")
    def get(self) -> dict:
        """Get state system statistics.

        Returns:
            dict: State statistics
        """
        return StateManagementUtilities.get_state_statistics()


class EntityTypeStates(Resource):
    """Get available states for an entity type."""

    @auth_required("ANALYZE_ACCESS")
    def get(self, entity_type: str) -> dict:
        """Get available states for the specified entity type.

        Args:
            entity_type: The entity type (e.g., 'report_item', 'product')

        Query Parameters:
            include_inactive: If 'true', includes all states regardless of is_active status

        Returns:
            dict: List of available states with their details
        """
        try:
            # Check if we should include inactive states (for settings/admin views)
            include_inactive = request.args.get("include_inactive", "false").lower() == "true"

            # Query state_entity_type for states for this entity type
            query = (
                db.session.query(StateTypeDefinition, StateDefinition)
                .join(StateDefinition, StateTypeDefinition.state_id == StateDefinition.id)
                .filter(StateTypeDefinition.entity_type == entity_type)
            )

            # Only filter by is_active if not including inactive states
            if not include_inactive:
                query = query.filter(StateTypeDefinition.is_active.is_(True))

            state_type_defs = query.order_by(StateTypeDefinition.sort_order, StateDefinition.display_name).all()

            result = []
            for state_type_def, state in state_type_defs:
                result.append(
                    {
                        "id": state.id,
                        "display_name": state.display_name,
                        "description": state.description,
                        "color": state.color,
                        "icon": state.icon,
                        "is_default": state_type_def.state_type == "default",
                        "is_active": state_type_def.is_active,
                        "state_type": state_type_def.state_type,
                        "sort_order": state_type_def.sort_order,
                    },
                )

            return {"entity_type": entity_type, "states": result, "include_inactive": include_inactive}
        except Exception as error:
            error_details = traceback.format_exc()
            return {
                "message": f"Error getting states for entity type {entity_type}: {error}",
                "details": error_details,
            }, HTTPStatus.INTERNAL_SERVER_ERROR


class EntityStates(Resource):
    """Manage states for a specific entity."""

    @auth_required("ANALYZE_ACCESS")
    def get(self, entity_type: str, entity_id: str) -> dict:
        """Get current states for the specified entity.

        Args:
            entity_type: The entity type
            entity_id: The entity ID

        Returns:
            dict: Current states of the entity
        """
        try:
            # Convert entity_id to integer since the database expects it
            try:
                entity_id_int = int(entity_id)
            except ValueError:
                return {"message": f"Invalid entity_id: {entity_id}. Must be a valid integer."}, HTTPStatus.BAD_REQUEST

            # Get current state for the entity
            result = []
            try:
                if entity_type == "report_item":
                    entity = ReportItem.find(entity_id_int)
                    if entity and entity.state_id:
                        state_def = StateDefinition.get_by_id(entity.state_id)
                        if state_def:
                            result.append(
                                {
                                    "id": state_def.id,
                                    "display_name": state_def.display_name,
                                    "description": state_def.description,
                                    "color": state_def.color,
                                    "icon": state_def.icon,
                                    "assigned_at": None,  # Not tracked with state_id approach
                                    "notes": state_def.description,
                                },
                            )
                elif entity_type == "product":
                    entity = Product.find(entity_id_int)
                    if entity and entity.state_id:
                        state_def = StateDefinition.get_by_id(entity.state_id)
                        if state_def:
                            result.append(
                                {
                                    "id": state_def.id,
                                    "display_name": state_def.display_name,
                                    "description": state_def.description,
                                    "color": state_def.color,
                                    "icon": state_def.icon,
                                    "assigned_at": None,  # Not tracked with state_id approach
                                    "notes": state_def.description,
                                },
                            )
            except Exception as error:
                logger.exception(f"Failed to get entity state: {error}")

            return {"entity_type": entity_type, "entity_id": entity_id, "states": result}
        except Exception as error:
            return {"message": f"Error getting states for entity {entity_type}:{entity_id}: {error}"}, HTTPStatus.INTERNAL_SERVER_ERROR

    @auth_required("ANALYZE_UPDATE")
    def post(self, entity_type: str, entity_id: str) -> dict:  # noqa: C901, PLR0911, PLR0912
        """Set state for the specified entity (replaces any existing state).

        Args:
            entity_type: The entity type
            entity_id: The entity ID

        Request JSON:
            {
                "state": "state_name",           # Single state to set (replaces current)
                "states": ["state_name"],        # Alternative: list with single state
                "remove_state": true             # Remove current state (optional)
            }

        Returns:
            dict: Result of the operation
        """
        try:
            # Validate and convert entity_id
            try:
                entity_id_int = int(entity_id)
            except ValueError as error:
                return {"message": f"Invalid entity_id: {entity_id}. Must be integer.: {error}"}, HTTPStatus.BAD_REQUEST

            # Get and validate request data
            data = request.get_json() or {}
            # Support both "state" (single) and "states" (list) for compatibility
            state_to_set = data["state"]

            remove_state = data.get("remove_state", False)

            # Get current user
            try:
                user = auth_manager.get_user_from_jwt()
                user_id = user.id if user else None
            except Exception as error:
                return {"message": f"Authentication error: {error}"}, HTTPStatus.UNAUTHORIZED

            # Validate entity type
            if not StateManager.validate_entity_type(entity_type):
                return {"message": f"Invalid entity_type: {entity_type}"}, HTTPStatus.BAD_REQUEST

            # Handle remove state request
            if remove_state:
                try:
                    logger.debug(f"Removing current state for {entity_type}:{entity_id_int}")
                    success = StateManager.remove_current_state(entity_type, entity_id_int, user_id)
                    if success:
                        db.session.commit()
                        return {
                            "entity_type": entity_type,
                            "entity_id": entity_id_int,
                            "message": "State removed successfully",
                        }
                    return {"message": "Failed to remove state"}, 500
                except Exception as error:
                    db.session.rollback()
                    return {"message": f"Failed to remove state: {error}"}, 500

            # Set new state (if provided)
            if state_to_set:
                try:
                    logger.debug(f"Setting state: '{state_to_set}'")
                    state_def = StateDefinition.get_by_name(state_to_set)
                    if not state_def:
                        return {"message": f"State '{state_to_set}' not found"}, HTTPStatus.NOT_FOUND

                    logger.debug(f"Found state: id={state_def.id}, display_name='{state_def.display_name}'")

                    # Check if state is allowed for this entity type
                    if not StateManager.is_state_allowed(entity_type, state_to_set):
                        return {"message": f"State '{state_to_set}' not allowed for entity type '{entity_type}'"}, HTTPStatus.FORBIDDEN

                    # Set the state (this replaces any existing state)
                    success = StateManager.set_state_by_name(entity_type, entity_id_int, state_to_set, user_id)
                    if success:
                        logger.debug(f"Successfully set state: '{state_to_set}'")
                    else:
                        return {"message": f"Failed to set state '{state_to_set}'"}, HTTPStatus.INTERNAL_SERVER_ERROR

                except Exception as error:
                    logger.exception(f"Exception details: {error}")

                    db.session.rollback()
                    return {"message": f"Failed to set state: {error}"}, HTTPStatus.INTERNAL_SERVER_ERROR

            try:
                db.session.commit()
                logger.debug("Transaction committed successfully")
            except Exception as error:
                db.session.rollback()
                return {"message": f"Database commit failed: {error}"}, HTTPStatus.INTERNAL_SERVER_ERROR

            # Trigger SSE event for real-time updates
            # Get updated state information to send with the event
            try:
                logger.debug("Getting updated state for SSE")
                # Get updated state
                updated_state = None
                try:
                    if entity_type == "report_item":
                        entity = ReportItem.find(entity_id_int)
                        if entity and entity.state_id:
                            state_def = StateDefinition.get_by_id(entity.state_id)
                            if state_def:
                                updated_state = {
                                    "id": state_def.id,
                                    "display_name": state_def.display_name,
                                    "description": state_def.description,
                                    "color": state_def.color,
                                    "icon": state_def.icon,
                                }
                    elif entity_type == "product":
                        entity = Product.find(entity_id_int)
                        if entity and entity.state_id:
                            state_def = StateDefinition.get_by_id(entity.state_id)
                            if state_def:
                                updated_state = {
                                    "id": state_def.id,
                                    "display_name": state_def.display_name,
                                    "description": state_def.description,
                                    "color": state_def.color,
                                    "icon": state_def.icon,
                                }
                except Exception as error:
                    logger.exception(f"Failed to get updated state: {error}")

                # Send SSE event with the updated state information
                if updated_state:
                    sse_data = {
                        "entity_type": entity_type,
                        "entity_id": entity_id_int,
                        "state": updated_state["display_name"],
                        "state_object": {
                            "id": updated_state["id"],
                            "name": updated_state["display_name"],
                            "display_name": updated_state["display_name"],
                            "description": updated_state["description"],
                            "color": updated_state["color"],
                            "icon": updated_state["icon"],
                        },
                    }
                else:
                    sse_data = {
                        "entity_type": entity_type,
                        "entity_id": entity_id_int,
                        "state": None,
                        "state_object": None,
                    }
                sse_manager.report_item_updated(sse_data)
                logger.debug("SSE notification sent successfully")
            except Exception as sse_error:
                # Log SSE error but don't fail the API call
                logger.exception(f"SSE notification failed: {sse_error}")

            return {
                "entity_type": entity_type,
                "entity_id": entity_id_int,
                "state_set": state_to_set,
                "message": f"Successfully set state to '{state_to_set}'" if state_to_set else "State cleared",
            }

        except Exception as error:
            db.session.rollback()
            return {"message": f"Error setting states for entity {entity_type}:{entity_id}: {error}"}, HTTPStatus.INTERNAL_SERVER_ERROR


# class StateCleanup(Resource):
#     """State cleanup endpoint."""

#     @auth_required("ASSESS_CREATE")  # Require admin permissions for state cleanup
#     def post(self) -> dict:
#         """Clean up orphaned state records.

#         Returns:
#             dict: Cleanup results
#         """
#         cleanup_count = 0

#         try:
#             # Find report items with invalid state_id references
#             invalid_report_items = ReportItem.query.filter(
#                 ReportItem.state_id.isnot(None),
#                 ~ReportItem.state_id.in_(db.session.query(StateDefinition.id)),
#             ).all()

#             for item in invalid_report_items:
#                 item.state_id = None
#                 cleanup_count += 1

#             # Find products with invalid state_id references
#             invalid_products = Product.query.filter(
#                 Product.state_id.isnot(None),
#                 ~Product.state_id.in_(db.session.query(StateDefinition.id)),
#             ).all()

#             for product in invalid_products:
#                 product.state_id = None
#                 cleanup_count += 1

#             db.session.commit()

#             return {"message": f"Cleaned up {cleanup_count} orphaned state references", "cleanup_count": cleanup_count}

#         except Exception as error:
#             db.session.rollback()
#             return {"message": f"Cleanup failed: {error}"}, HTTPStatus.INTERNAL_SERVER_ERROR


def initialize(api: object) -> None:
    """Initialize state management API.

    Args:
        api: Flask-RESTful API instance
    """
    # api.add_resource(StateSync, "/api/v1/state/sync")
    api.add_resource(StateStatistics, "/api/v1/state/statistics")
    # api.add_resource(StateCleanup, "/api/v1/state/cleanup")
    api.add_resource(EntityTypeStates, "/api/v1/state/entity-types/<string:entity_type>/states")
    api.add_resource(EntityStates, "/api/v1/state/entities/<string:entity_type>/<string:entity_id>/states")
