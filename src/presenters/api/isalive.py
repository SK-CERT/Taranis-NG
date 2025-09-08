"""API endpoint to check if the service is alive."""

from flask_restful import Api, Resource


class IsAlive(Resource):
    """API endpoint to check if the service is alive."""

    def get(self) -> dict:
        """Check if the service is alive."""
        return {"isalive": True}


def initialize(api: Api) -> None:
    """Initialize the API endpoint."""
    api.add_resource(IsAlive, "/api/v1/isalive")
