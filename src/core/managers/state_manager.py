"""State management utilities."""

import contextlib
import logging

from managers.db_manager import db
from model.product import Product
from model.report_item import ReportItem

logger = logging.getLogger(__name__)


class StateManagementUtilities:
    """Utilities for managing the state system."""

    # @staticmethod
    # def sync_all_states() -> dict:
    #     """Synchronize all states in the system.

    #     Note: With the new state_id column approach,
    #     synchronization is not needed as states are directly stored.

    #     Returns:
    #         dict: Summary of synchronization results
    #     """
    #     try:
    #         # Get summary statistics
    #         total_states = StateDefinition.get_active_states()

    #         return {
    #             "success": True,
    #             "message": "State system using direct state_id columns - no sync needed",
    #             "statistics": {
    #                 "available_states": len(total_states),
    #                 "state_names": [s.display_name for s in total_states],
    #             },
    #         }
    #     except Exception as error:
    #         return {"success": False, "message": f"State synchronization failed: {error}"}

    @staticmethod
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
