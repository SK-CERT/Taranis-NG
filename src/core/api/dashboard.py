"""Dashboard API."""

from flask import request
from flask_jwt_extended import jwt_required
from flask_restful import Resource
from managers.log_manager import logger
from model.news_item import NewsItemData
from model.product import Product
from model.report_item import ReportItem
from model.tag_cloud import TagCloud


class Dashboard(Resource):
    """Dashboard API class."""

    @jwt_required()
    def get(self) -> dict:
        """Get the dashboard data.

        Returns:
            (dict): The dashboard data.
        """
        try:
            number_of_days = 0
            if request.args.get("tag_cloud_day"):
                number_of_days = min(int(request.args["tag_cloud_days"]), 7)
        except Exception as ex:
            msg = "Get Dashboard failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, 400

        total_news_items = NewsItemData.count_all()
        total_products = Product.count_all()

        # Get comprehensive state-based counts for report items
        report_item_states = ReportItem.count_by_states()

        # Get comprehensive state-based counts for products
        product_states = Product.count_by_states()

        total_report_items = sum(state["count"] for state in report_item_states.values())

        total_database_items = total_news_items + total_products + total_report_items
        latest_collected = NewsItemData.latest_collected()
        grouped_words = TagCloud.get_grouped_words(number_of_days)

        return {
            "total_news_items": total_news_items,
            "total_products": total_products,
            "total_report_items": total_report_items,
            "report_item_states": report_item_states,
            "product_states": product_states,
            "total_database_items": total_database_items,
            "latest_collected": latest_collected,
            "tag_cloud": grouped_words,
        }


def initialize(api: object) -> None:
    """Initialize the dashboard API.

    Args:
        api (Flask): The Flask app.
    """
    api.add_resource(Dashboard, "/api/v1/dashboard-data")
