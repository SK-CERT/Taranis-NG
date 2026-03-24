"""State management API endpoints."""

import contextlib
from http import HTTPStatus

from flask import request
from flask_restful import Resource
from managers import log_manager
from managers.auth_manager import auth_required, get_user_from_jwt
from managers.db_manager import db
from model.product import Product
from model.report_item import ReportItem
from model.state import StateDefinition
from shared.log_manager import logger


def get_state_statistics() -> dict:
    """Get statistics about the current state system.

    Returns:
        dict: State system statistics
    """
    try:
        # Get count of entities with states
        report_items_with_states = 0
        products_with_states = 0

        with contextlib.suppress(Exception):
            report_items_with_states = db.session.query(ReportItem).filter(ReportItem.state_id.isnot(None)).count()

        with contextlib.suppress(Exception):
            products_with_states = db.session.query(Product).filter(Product.state_id.isnot(None)).count()

        return {
            "total_report_items_with_states": report_items_with_states,
            "total_products_with_states": products_with_states,
            "total_entities_with_states": report_items_with_states + products_with_states,
        }
    except Exception as error:
        logger.exception(f"Failed to get state statistics: {error}")
        return {
            "total_report_items_with_states": 0,
            "total_products_with_states": 0,
            "total_entities_with_states": 0,
        }


class StateStatisticsResource(Resource):
    """State statistics endpoint."""

    @auth_required("ASSESS_ACCESS")
    def get(self) -> dict:
        """Get state system statistics.

        Returns:
            dict: State statistics
        """
        return get_state_statistics()


class EntityTypeStatesResource(Resource):
    """Get available states for an entity type."""

    @auth_required("ANALYZE_ACCESS")
    def get(self, entity_type: str) -> tuple[dict, HTTPStatus]:
        """Get available states for the specified entity type.

        Args:
            entity_type: The entity type (e.g., 'report_item', 'product')

        Query Parameters:
            include_inactive: If 'true', includes all states regardless of is_active status

        Returns:
            dict: List of available states with their details
        """
        try:
            # Check if we should include inactive states
            include_inactive = request.args.get("include_inactive", "false").lower() == "true"
            return StateDefinition.get_full_by_entity_json(entity_type, include_inactive), HTTPStatus.OK

        except Exception as error:
            msg = f"Error getting states for entity type {entity_type}"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, error)
            return {"error": msg}, HTTPStatus.INTERNAL_SERVER_ERROR


def initialize(api: object) -> None:
    """Initialize state management API.

    Args:
        api: Flask-RESTful API instance
    """
    api.add_resource(StateStatisticsResource, "/api/v1/state/statistics")
    api.add_resource(EntityTypeStatesResource, "/api/v1/state/entity-types/<string:entity_type>/states")
