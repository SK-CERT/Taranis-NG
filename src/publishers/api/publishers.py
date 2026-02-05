"""Publishers API resource module."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from http import HTTPStatus

    from flask_restful import Api


from flask import request
from flask_restful import Resource
from managers import publishers_manager
from managers.auth_manager import api_key_required


class Publishers(Resource):
    """Represent a publishers resource.

    Args:
        Resource -- The base class for API resources.
    """

    @api_key_required
    def get(self) -> dict:
        """Get registered publishers information.

        Returns:
            dict: Registered publishers information.
        """
        return publishers_manager.get_registered_publishers_info()

    @api_key_required
    def post(self) -> tuple[dict, HTTPStatus]:
        """Publish data to a publisher.

        Args:
            body (dict): JSON payload from the request body.

        Returns:
            tuple[dict, HTTPStatus]: Response payload and HTTP status.
        """
        return publishers_manager.publish(request.json)


def initialize(api: Api) -> None:
    """Initialize the publishers API resource."""
    api.add_resource(Publishers, "/api/v1/publishers")
