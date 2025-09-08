"""API endpoints for managing presenters."""

from flask import request
from flask_restful import Api, Resource
from managers import presenters_manager
from managers.auth_manager import api_key_required


class Presenters(Resource):
    """API endpoint for managing presenters."""

    @api_key_required
    def get(self) -> dict:
        """Get registered presenters information."""
        return presenters_manager.get_registered_presenters_info()

    @api_key_required
    def post(self) -> dict:
        """Register a new presenter."""
        return presenters_manager.generate(request.json)


def initialize(api: Api) -> None:
    """Initialize the API endpoint."""
    api.add_resource(Presenters, "/api/v1/presenters")
