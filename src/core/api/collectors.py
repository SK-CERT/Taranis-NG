"""Collectors API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask_restful import Api
    from model.collectors_node import CollectorsNode

from http import HTTPStatus

from flask import request
from flask_restful import Resource, reqparse
from managers import run_state_cache
from managers.auth_manager import api_key_required
from managers.log_manager import logger
from managers.sse_manager import sse_manager
from model.news_item import NewsItemAggregate
from model.osint_source import OSINTSource


class OSINTSourcesForCollectors(Resource):
    """OSINT sources for collectors API endpoint."""

    @api_key_required("collectors")
    def get(self, collector_id: str, collectors_node: CollectorsNode = None) -> tuple[dict, HTTPStatus]:
        """Get all OSINT sources for a collector.

        Args:
            collector_id (str): The collector ID
            collectors_node (CollectorsNode): The collectors node
        Returns:
            (dict): All OSINT sources for a collector
        """
        parser = reqparse.RequestParser()
        parser.add_argument("collector_type", location="args")
        parameters = parser.parse_args()
        if collectors_node.id != collector_id:
            msg = "Forbidden: Collector ID does not match"
            logger.warning(msg)
            return {"error": msg}, HTTPStatus.FORBIDDEN

        collectors_node.update_last_seen()

        return OSINTSource.get_all_for_collector_json(collectors_node, parameters.collector_type)


class OSINTSourceLastAttempt(Resource):
    """OSINT source last attempt API endpoint."""

    @api_key_required("collectors")
    def get(
        self,
        osint_source_id: str,
        collectors_node: CollectorsNode = None,  # noqa: ARG002
    ) -> tuple[dict, HTTPStatus]:
        """Get the last attempt for an OSINT source.

        Args:
            osint_source_id (str): The OSINT source ID
            collectors_node (CollectorsNode): The collectors node
        Returns:
            (dict): Empty dictionary
            (int): The response code
        """
        source = OSINTSource.find(osint_source_id)
        if not source:
            msg = "OSINT source with this ID does not exists"
            logger.warning(msg)
            return {"error": msg}, 404
        # The collector calls this as a run begins, so it doubles as the "collecting" signal.
        OSINTSource.mark_collection_started(osint_source_id)
        return {}, HTTPStatus.OK


class CollectorSourcesSchedule(Resource):
    """When the node plans to collect each of its sources."""

    @api_key_required("collectors")
    def post(
        self,
        collector_id: str,  # noqa: ARG002
        collectors_node: CollectorsNode = None,  # noqa: ARG002
    ) -> tuple[dict, HTTPStatus]:
        """Record the next run time of every source the node reports.

        Only the node knows this: an interval can be minutes, a daily time or a weekday and time,
        and the node is also the only thing that knows how far behind its scheduler is running.

        Args:
            collector_id (str): The collectors node ID, from the path
            collectors_node (CollectorsNode): The collectors node
        Returns:
            (dict): Empty dictionary
            (int): The response code
        """
        for source_id, next_run in (request.json or {}).items():
            if next_run:
                run_state_cache.set_next_run(source_id, next_run)
        return {}, HTTPStatus.OK


class OSINTSourceLastErrorMessage(Resource):
    """OSINT source last error message API endpoint."""

    @api_key_required("collectors")
    def get(
        self,
        osint_source_id: str,
        collectors_node: CollectorsNode = None,  # noqa: ARG002
    ) -> tuple[dict, HTTPStatus]:
        """Get the last error message for an OSINT source.

        Args:
            osint_source_id (str): The OSINT source ID
            collectors_node (CollectorsNode): The collectors node
        Returns:
            (dict): Empty dictionary
            (int): The response code
        """
        source = OSINTSource.find(osint_source_id)
        if not source:
            msg = "OSINT source with this ID does not exists"
            logger.error(msg)
            return {"error": msg}, HTTPStatus.NOT_FOUND

        error_message = request.args.get("message", None)

        # The collector calls this as a run ends, whether or not anything went wrong, so it is
        # also what clears the "collecting" signal.
        OSINTSource.mark_collection_finished(osint_source_id, error_message)
        return {}, HTTPStatus.OK


class AddNewsItems(Resource):
    """Add news items API endpoint."""

    @api_key_required("collectors")
    def post(
        self,
        collectors_node: CollectorsNode = None,  # noqa: ARG002
    ) -> None:
        """Add news items to the database.

        Args:
            collectors_node (CollectorsNode): The collectors node
        """
        osint_source_ids = NewsItemAggregate.add_news_items(request.json)
        if osint_source_ids:  # we create some news items
            sse_manager.news_items_updated()
            sse_manager.remote_access_news_items_updated(osint_source_ids)


class CollectorStatusUpdate(Resource):
    """Collector status update API endpoint."""

    @api_key_required("collectors")
    def get(self, collector_id: str, collectors_node: CollectorsNode = None) -> tuple[dict, HTTPStatus]:
        """Update the status of a collector.

        Args:
            collector_id (str): The collector ID
            collectors_node (CollectorsNode): The collectors node
        Returns:
            (dict): Empty dictionary
            (int): The response code
        """
        if collectors_node.id != collector_id:
            msg = "Forbidden: Collector ID does not match"
            logger.warning(msg)
            return {"error": msg}, HTTPStatus.FORBIDDEN

        try:
            collectors_node.update_last_seen()
        except Exception as ex:
            msg = "Get CollectorStatusUpdate failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, HTTPStatus.BAD_REQUEST

        return {}, HTTPStatus.OK


def initialize(api: Api) -> None:
    """Initialize the API with the collectors endpoints."""
    api.add_resource(OSINTSourcesForCollectors, "/api/v1/collectors/<string:collector_id>/osint-sources")
    api.add_resource(OSINTSourceLastAttempt, "/api/v1/collectors/osint-sources/<string:osint_source_id>/attempt")
    api.add_resource(OSINTSourceLastErrorMessage, "/api/v1/collectors/osint-sources/<string:osint_source_id>/error_message")
    api.add_resource(CollectorSourcesSchedule, "/api/v1/collectors/<string:collector_id>/schedule")
    api.add_resource(CollectorStatusUpdate, "/api/v1/collectors/<string:collector_id>")
    api.add_resource(AddNewsItems, "/api/v1/collectors/news-items")
