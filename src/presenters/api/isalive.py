"""API endpoint to check if the service is alive."""

from flask_restful import Api, Resource
from managers.auth_manager import api_key_required


class IsAlive(Resource):
    """API endpoint to check if the service is alive."""

    @api_key_required
    def get(self) -> dict:
        """Check if the service is alive.

        Authenticated like every other endpoint here: in a distributed deployment this
        answers on the public internet, and an open liveness probe advertises the node.

        Returns:
            (dict): The liveness marker.
        """
        return {"isalive": True}


def initialize(api: Api) -> None:
    """Initialize the API endpoint.

    Args:
        api (Api): The Flask-RESTful API to register the resource on.
    """
    api.add_resource(IsAlive, "/api/v1/isalive")
