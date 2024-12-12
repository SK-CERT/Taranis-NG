"""This module defines API resources for managing publishers nodes and presets using Flask-RESTful.

Classes:
    AddPublishersNode: API Resource for adding a new publishers node.
    PublisherPresets: API Resource for handling publisher presets.
    AddPublisherPreset: API Resource for adding a new publisher preset.
    PublisherPreset: API Resource for handling a publisher preset.
    PublisherNodes: API Resource for handling publisher nodes.
    PublishersNode: API Resource for handling a publisher node.

Functions:
    initialize(api): Initialize the API with publisher-related resources and permissions.

Each class contains methods to handle HTTP requests (GET, POST, PUT, DELETE) for the respective resources.
The methods are decorated with authentication and authorization requirements to ensure proper access control.
"""

from flask_restful import Resource, reqparse
from flask import request

from managers import publishers_manager
from managers.auth_manager import auth_required, api_key_required
from model import publishers_node, publisher_preset
from model.permission import Permission


class AddPublishersNode(Resource):
    """API Resource for adding a new publishers node."""

    @auth_required("CONFIG_PUBLISHERS_NODE_CREATE")
    def post(self):
        """Handle POST request to add a new publisher node.

        This method processes the incoming JSON data from the request and
        uses the publishers_manager to add a new publisher node.
        Returns:
            tuple: An empty string and the result of the add_publishers_node method.
        """
        return "", publishers_manager.add_publishers_node(request.json)


class PublisherPresets(Resource):
    """API Resource for handling publisher presets."""

    @auth_required("CONFIG_PUBLISHER_PRESET_ACCESS")
    def get(self):
        """Handle GET requests to retrieve publisher presets.

        If a "search" parameter is provided in the request arguments, it will be used
        to filter the publisher presets.
        Returns:
            JSON response containing the list of publisher presets, optionally filtered by the search term.
        """
        search = None
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        return publisher_preset.PublisherPreset.get_all_json(search)

    @api_key_required
    def post(self):
        """Handle POST requests to retrieve all publisher presets for a given publisher.

        This method parses the request arguments to extract the API key and collector type,
        and then retrieves the corresponding publisher presets in JSON format.
        Returns:
            dict: A dictionary containing all publisher presets for the specified publisher in JSON format.
        """
        parser = reqparse.RequestParser()
        parser.add_argument("api_key", location="args")
        parser.add_argument("collector_type", location="args")
        parameters = parser.parse_args()
        return publisher_preset.PublisherPreset.get_all_for_publisher_json(parameters)


class AddPublisherPreset(Resource):
    """API Resource for adding a new publisher preset."""

    @auth_required("CONFIG_PUBLISHER_PRESET_CREATE")
    def post(self):
        """Handle POST request to add a new publisher preset.

        This method retrieves JSON data from the request and passes it to the
        publishers_manager to add a new publisher preset.
        Raises:
            Exception: If there is an issue with adding the publisher preset.
        """
        publishers_manager.add_publisher_preset(request.json)


class PublisherPreset(Resource):
    """API Resource for handling a publisher preset."""

    @auth_required("CONFIG_PUBLISHER_PRESET_UPDATE")
    def put(self, id):
        """Update a publisher preset with the given ID using the provided JSON data.

        Args:
            id (int): The ID of the publisher preset to update.
        Returns:
            Response: The response object indicating the result of the update operation.
        """
        publisher_preset.PublisherPreset.update(id, request.json)

    @auth_required("CONFIG_PUBLISHER_PRESET_DELETE")
    def delete(self, id):
        """Delete a publisher preset by its ID.

        Args:
            id (int): The ID of the publisher preset to delete.
        Returns:
            bool: True if the deletion was successful, False otherwise.
        """
        return publisher_preset.PublisherPreset.delete(id)


class PublisherNodes(Resource):
    """API Resource for handling publisher nodes."""

    @auth_required("CONFIG_PUBLISHERS_NODE_ACCESS")
    def get(self):
        """Handle GET requests to retrieve publisher data.

        If a "search" parameter is provided in the request arguments, it will be used
        to filter the publisher data.
        Returns:
            JSON response containing the publisher data, optionally filtered by the search term.
        """
        search = None
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        return publishers_node.PublishersNode.get_all_json(search)


class PublishersNode(Resource):
    """API Resource for handling a publisher node."""

    @auth_required("CONFIG_PUBLISHERS_NODE_UPDATE")
    def put(self, id):
        """Update a publisher's node with the given ID using the provided JSON data.

        Args:
            id (int): The ID of the publisher's node to update.
        """
        publishers_manager.update_publishers_node(id, request.json)

    @auth_required("CONFIG_PUBLISHERS_NODE_DELETE")
    def delete(self, id):
        """Delete a publisher by its ID.

        Args:
            id (int): The ID of the publisher to delete.
        Returns:
            bool: True if the deletion was successful, False otherwise.
        """
        return publishers_node.PublishersNode.delete(id)


def initialize(api):
    """Initialize the API with publisher-related resources and permissions.

    This function adds various publisher-related resources to the provided API
    instance and sets up the necessary permissions for accessing, creating,
    updating, and deleting publisher nodes and presets.
    Args:
        api: The API instance to which the resources and permissions will be added.
    Resources:
        - /api/publishers/nodes: Endpoint for PublisherNodes resource.
        - /api/publishers/nodes/add: Endpoint for AddPublishersNode resource.
        - /api/publishers/node/<id>: Endpoint for PublishersNode resource.
        - /api/publishers/presets: Endpoint for PublisherPresets resource.
        - /api/publishers/presets/add: Endpoint for AddPublisherPreset resource.
        - /api/publishers/preset/<id>: Endpoint for PublisherPreset resource.
    Permissions:
        - CONFIG_PUBLISHERS_NODE_ACCESS: Access to publishers nodes configuration.
        - CONFIG_PUBLISHERS_NODE_CREATE: Create publishers node configuration.
        - CONFIG_PUBLISHERS_NODE_UPDATE: Update publishers node configuration.
        - CONFIG_PUBLISHERS_NODE_DELETE: Delete publishers node configuration.
        - CONFIG_PUBLISHER_PRESET_ACCESS: Access to publisher presets configuration.
        - CONFIG_PUBLISHER_PRESET_CREATE: Create publisher preset configuration.
        - CONFIG_PUBLISHER_PRESET_UPDATE: Update publisher preset configuration.
        - CONFIG_PUBLISHER_PRESET_DELETE: Delete publisher preset configuration.
    """
    api.add_resource(PublisherNodes, "/api/publishers/nodes")
    api.add_resource(AddPublishersNode, "/api/publishers/nodes/add")
    api.add_resource(PublishersNode, "/api/publishers/node/<id>")

    api.add_resource(PublisherPresets, "/api/publishers/presets")
    api.add_resource(AddPublisherPreset, "/api/publishers/presets/add")
    api.add_resource(PublisherPreset, "/api/publishers/preset/<id>")

    Permission.add("CONFIG_PUBLISHERS_NODE_ACCESS", "Config publishers nodes access", "Access to publishers nodes configuration")
    Permission.add("CONFIG_PUBLISHERS_NODE_CREATE", "Config publishers node create", "Create publishers node configuration")
    Permission.add("CONFIG_PUBLISHERS_NODE_UPDATE", "Config publishers node update", "Update publishers node configuration")
    Permission.add("CONFIG_PUBLISHERS_NODE_DELETE", "Config publishers node delete", "Delete publishers node configuration")

    Permission.add("CONFIG_PUBLISHER_PRESET_ACCESS", "Config publisher presets access", "Access to publisher presets configuration")
    Permission.add("CONFIG_PUBLISHER_PRESET_CREATE", "Config publisher preset create", "Create publisher preset configuration")
    Permission.add("CONFIG_PUBLISHER_PRESET_UPDATE", "Config publisher preset update", "Update publisher preset configuration")
    Permission.add("CONFIG_PUBLISHER_PRESET_DELETE", "Config publisher preset delete", "Delete publisher preset configuration")
