"""This module contains the API for handling collectors."""

from http import HTTPStatus

from flask import request
from flask_restful import Api, Resource
from managers import collectors_manager
from managers.auth_manager import api_key_required
from shared.log_manager import logger


class Collectors(Resource):
    """This class represents a resource for handling collectors.

    Methods:
        post: Handles the POST request for creating a collector.
    """

    @api_key_required
    def post(self) -> tuple[dict, HTTPStatus] | list:
        """Process a POST request.

        Returns:
            If 'id' is present in the JSON payload of the request, it returns the registered collectors info for the given ID.
            Otherwise, it returns an empty string with a status code of 400.
        """
        if "id" in request.json:
            logger.debug(f"Got ID for collector: {request.json['id']}")
            return collectors_manager.get_registered_collectors_info(request.json["id"])
        msg = "Collector ID missing"
        logger.warning(msg)
        return {"error": msg}, HTTPStatus.BAD_REQUEST


class Collector(Resource):
    """This class represents a collector.

    Methods:
        put(collector_type): Refreshes the collector of the specified type.
    """

    @api_key_required
    def put(self, collector_type: str) -> HTTPStatus:
        """Refresh the specified collector.

        Parameters:
            collector_type (str): The type of collector to refresh.

        Returns:
            (HTTPStatus): OK once the refresh has been started, FORBIDDEN for an unknown type.
        """
        # Defaults to true so that an older core, which does not send the flag, keeps the
        # behaviour it expects: a refresh that also collects everything.
        collect_now = request.args.get("collect_now", "true").lower() != "false"
        return collectors_manager.refresh_collector(collector_type, collect_now=collect_now)


class CollectorSourceRun(Resource):
    """Collecting a single OSINT source on demand.

    Methods:
        post(collector_type, source_id): Starts a run for that source and returns immediately.
    """

    @api_key_required
    def post(self, collector_type: str, source_id: str) -> tuple[dict, HTTPStatus]:
        """Collect one source now.

        Parameters:
            collector_type (str): The type of collector owning the source.
            source_id (str): The id of the source to collect.

        Returns:
            202 when a run was started, 409 when one is already in progress for that source,
            404 when the collector does not know the source, 403 for an unknown collector type.
        """
        return collectors_manager.collect_source_now(collector_type, source_id)


def initialize(api: Api) -> None:
    """Initialize the API by adding resources for collectors.

    Parameters:
        api: The Flask-Restful API object.
    """
    api.add_resource(Collectors, "/api/v1/collectors")
    api.add_resource(Collector, "/api/v1/collectors/<string:collector_type>")
    api.add_resource(
        CollectorSourceRun,
        "/api/v1/collectors/<string:collector_type>/osint-sources/<string:source_id>/collect",
    )
