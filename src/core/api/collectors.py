"""Collectors API endpoints."""

from flask import request
from flask_restful import Resource, reqparse

from managers.sse_manager import sse_manager
from managers.auth_manager import api_key_required
from managers.log_manager import logger
from model import osint_source, news_item
from shared.schema.osint_source import OSINTSourceUpdateStatusSchema


class OSINTSourcesForCollectors(Resource):
    """OSINT sources for collectors API endpoint."""

    @api_key_required("collectors")
    def get(self, collector_id, collectors_node=None):
        """Get all OSINT sources for a collector.

        Args:
            collector_id (str): The collector ID
        Returns:
            (dict): All OSINT sources for a collector
        """
        parser = reqparse.RequestParser()
        parser.add_argument("collector_type", location="args")
        parameters = parser.parse_args()
        if collectors_node.id != collector_id:
            return "", 404

        collectors_node.updateLastSeen()

        return osint_source.OSINTSource.get_all_for_collector_json(collectors_node, parameters.collector_type)


class OSINTSourceLastAttempt(Resource):
    """OSINT source last attempt API endpoint."""

    @api_key_required("collectors")
    def get(self, osint_source_id, collectors_node=None):
        """Get the last attempt for an OSINT source.

        Args:
            osint_source_id (str): The OSINT source ID
        Returns:
            (dict): Empty dictionary
            (int): The response code
        """
        source = osint_source.OSINTSource.get_by_id(osint_source_id)
        if not source:
            return {}, 404
        source.update_last_attempt(osint_source_id)
        return {}, 200


class AddNewsItems(Resource):
    """Add news items API endpoint."""

    @api_key_required("collectors")
    def post(self, collectors_node=None):
        """Add news items to the database."""
        osint_source_ids = news_item.NewsItemAggregate.add_news_items(request.json)
        sse_manager.news_items_updated()
        sse_manager.remote_access_news_items_updated(osint_source_ids)


class OSINTSourceStatusUpdate(Resource):
    """OSINT source status update API endpoint."""

    @api_key_required("collectors")
    def put(self, osint_source_id, collectors_node=None):
        """Update the status of an OSINT source.

        Args:
            osint_source_id (str): The OSINT source ID
        Returns:
            (dict): Empty dictionary
            (int): The response code
        """
        source = osint_source.OSINTSource.get_by_id(osint_source_id)
        if not source:
            return {}, 404

        try:
            osint_source_status_schema = OSINTSourceUpdateStatusSchema()
            osint_source_status = osint_source_status_schema.load(request.json)  # noqa F841
        except Exception as ex:
            logger.exception(f"Put OSINTSourceStatusUpdate failed: {ex}")
            return {}, 400

        return {}, 200


class CollectorStatusUpdate(Resource):
    """Collector status update API endpoint."""

    @api_key_required("collectors")
    def get(self, collector_id, collectors_node=None):
        """Update the status of a collector.

        Args:
            collector_id (str): The collector ID
        Returns:
            (dict): Empty dictionary
            (int): The response code
        """
        if collectors_node.id != collector_id:
            return "", 404

        try:
            collectors_node.updateLastSeen()
        except Exception as ex:
            logger.exception(f"Get CollectorStatusUpdate failed: {ex}")
            return {}, 400

        return {}, 200


def initialize(api):
    """Initialize the API with the collectors endpoints."""
    api.add_resource(OSINTSourcesForCollectors, "/api/v1/collectors/<string:collector_id>/osint-sources")
    api.add_resource(OSINTSourceStatusUpdate, "/api/v1/collectors/osint-sources/<string:osint_source_id>")
    api.add_resource(OSINTSourceLastAttempt, "/api/v1/collectors/osint-sources/<string:osint_source_id>/attempt")
    api.add_resource(CollectorStatusUpdate, "/api/v1/collectors/<string:collector_id>")
    api.add_resource(AddNewsItems, "/api/v1/collectors/news-items")
