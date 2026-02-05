"""This module contains the API for handling collectors."""

from flask import request
from flask_restful import Resource
from managers import collectors_manager
from managers.auth_manager import api_key_required

from shared.log_manager import logger


class Collectors(Resource):
    """This class represents a resource for handling collectors.

    Methods:
        post: Handles the POST request for creating a collector.
    """

    @api_key_required
    def post(self):
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
        return {"error": msg}, 400


class Collector(Resource):
    """This class represents a collector.

    Methods:
        put(collector_type): Refreshes the collector of the specified type.
    """

    @api_key_required
    def put(self, collector_type):
        """Refresh the specified collector.

        Parameters:
            collector_type (str): The type of collector to refresh.
        """
        return collectors_manager.refresh_collector(collector_type)


def initialize(api):
    """Initialize the API by adding resources for collectors.

    Parameters:
        api: The Flask-Restful API object.
    """
    api.add_resource(Collectors, "/api/v1/collectors")
    api.add_resource(Collector, "/api/v1/collectors/<string:collector_type>")
