"""This module defines API resources for managing publishers nodes and publishing channels using Flask-RESTful.

Classes:
    AddPublishersNode: API Resource for adding a new publishers node.
    PublishingChannels: API Resource for handling publishing channels.
    AddPublishingChannel: API Resource for adding a new publishing channel.
    PublishingChannel: API Resource for handling a publishing channel.
    PublisherNodes: API Resource for handling publisher nodes.
    PublishersNode: API Resource for handling a publisher node.

Functions:
    initialize(api): Initialize the API with publisher-related resources and permissions.

Each class contains methods to handle HTTP requests (GET, POST, PUT, DELETE) for the respective resources.
The methods are decorated with authentication and authorization requirements to ensure proper access control.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from flask import request
from flask_restful import Resource, reqparse
from managers import publishers_manager
from managers.auth_manager import api_key_required, auth_required
from model import publishers_node, publishing_channel
from model.permission import Permission

if TYPE_CHECKING:
    from flask_restful import Api


class AddPublishersNode(Resource):
    """API Resource for adding a new publishers node."""

    @auth_required("CONFIG_PUBLISHERS_NODE_CREATE")
    def post(self) -> tuple[str, object]:
        """Handle POST request to add a new publisher node.

        This method processes the incoming JSON data from the request and
        uses the publishers_manager to add a new publisher node.

        Returns:
            tuple: An empty string and the result of the add_publishers_node method.
        """
        return "", publishers_manager.add_publishers_node(request.json)


class PublishingChannels(Resource):
    """API Resource for handling publishing channels."""

    @auth_required("CONFIG_PUBLISHING_CHANNEL_ACCESS")
    def get(self) -> dict:
        """Handle GET requests to retrieve publishing channels.

        If a "search" parameter is provided in the request arguments, it will be used
        to filter the publishing channels.

        Returns:
            JSON response containing the list of publishing channels, optionally filtered by the search term.
        """
        search = None
        if request.args.get("search"):
            search = request.args["search"]
        return publishing_channel.PublishingChannel.get_all_json(search)

    @api_key_required("publishers")
    def post(self, publishers_node: publishers_node.PublishersNode | None = None) -> dict | None:
        """Handle POST requests to retrieve all publishing channels for a given publisher.

        This method parses the request arguments to extract the API key and collector type,
        and then retrieves the corresponding publishing channels in JSON format.

        Returns:
            dict: A dictionary containing all publishing channels for the specified publisher in JSON format.
        """
        parser = reqparse.RequestParser()
        parser.add_argument("publisher_type", location="args")
        parameters = parser.parse_args()
        return publishing_channel.PublishingChannel.get_all_for_publisher_json(publishers_node, parameters.publisher_type)


class AddPublishingChannel(Resource):
    """API Resource for adding a new publishing channel."""

    @auth_required("CONFIG_PUBLISHING_CHANNEL_CREATE")
    def post(self) -> None:
        """Handle POST request to add a new publishing channel.

        This method retrieves JSON data from the request and passes it to the
        publishers_manager to add a new publishing channel.

        Raises:
            Exception: If there is an issue with adding the publishing channel.
        """
        publishers_manager.add_publishing_channel(request.json)


class PublishingChannel(Resource):
    """API Resource for handling a publishing channel."""

    @auth_required("CONFIG_PUBLISHING_CHANNEL_UPDATE")
    def put(self, id: str) -> None:  # noqa: A002
        """Update a publishing channel with the given ID using the provided JSON data.

        Args:
            id (int): The ID of the publishing channel to update.

        Returns:
            Response: The response object indicating the result of the update operation.
        """
        publishing_channel.PublishingChannel.update(id, request.json)

    @auth_required("CONFIG_PUBLISHING_CHANNEL_DELETE")
    def delete(self, id: str) -> object:  # noqa: A002
        """Delete a publishing channel by its ID.

        Args:
            id (int): The ID of the publishing channel to delete.

        Returns:
            bool: True if the deletion was successful, False otherwise.
        """
        return publishing_channel.PublishingChannel.delete(id)


class PublisherNodes(Resource):
    """API Resource for handling publisher nodes."""

    @auth_required("CONFIG_PUBLISHERS_NODE_ACCESS")
    def get(self) -> dict:
        """Handle GET requests to retrieve publisher data.

        If a "search" parameter is provided in the request arguments, it will be used
        to filter the publisher data.

        Returns:
            JSON response containing the publisher data, optionally filtered by the search term.
        """
        search = None
        if request.args.get("search"):
            search = request.args["search"]
        return publishers_node.PublishersNode.get_all_json(search)


class PublishersNode(Resource):
    """API Resource for handling a publisher node."""

    @auth_required("CONFIG_PUBLISHERS_NODE_UPDATE")
    def put(self, id: str) -> None:  # noqa: A002
        """Update a publisher's node with the given ID using the provided JSON data.

        Args:
            id (int): The ID of the publisher's node to update.
        """
        publishers_manager.update_publishers_node(id, request.json)

    @auth_required("CONFIG_PUBLISHERS_NODE_DELETE")
    def delete(self, id: str) -> object:  # noqa: A002
        """Delete a publisher by its ID.

        Args:
            id (int): The ID of the publisher to delete.

        Returns:
            bool: True if the deletion was successful, False otherwise.
        """
        return publishers_node.PublishersNode.delete(id)


def initialize(api: Api) -> None:
    """Initialize the API with publisher-related resources and permissions.

    This function adds various publisher-related resources to the provided API
    instance and sets up the necessary permissions for accessing, creating,
    updating, and deleting publisher nodes and publishing channels.

    Args:
        api: The API instance to which the resources and permissions will be added.
    Resources:
        - /api/publishers/nodes: Endpoint for PublisherNodes resource.
        - /api/publishers/nodes/add: Endpoint for AddPublishersNode resource.
        - /api/publishers/node/<id>: Endpoint for PublishersNode resource.
        - /api/publishers/channels: Endpoint for PublishingChannels resource.
        - /api/publishers/channels/add: Endpoint for AddPublishingChannel resource.
        - /api/publishers/channel/<id>: Endpoint for PublishingChannel resource.
    Permissions:
        - CONFIG_PUBLISHERS_NODE_ACCESS: Access to publishers nodes configuration.
        - CONFIG_PUBLISHERS_NODE_CREATE: Create publishers node configuration.
        - CONFIG_PUBLISHERS_NODE_UPDATE: Update publishers node configuration.
        - CONFIG_PUBLISHERS_NODE_DELETE: Delete publishers node configuration.
        - CONFIG_PUBLISHING_CHANNEL_ACCESS: Access to publishing channels configuration.
        - CONFIG_PUBLISHING_CHANNEL_CREATE: Create publishing channel configuration.
        - CONFIG_PUBLISHING_CHANNEL_UPDATE: Update publishing channel configuration.
        - CONFIG_PUBLISHING_CHANNEL_DELETE: Delete publishing channel configuration.
    """
    api.add_resource(PublisherNodes, "/api/publishers/nodes")
    api.add_resource(AddPublishersNode, "/api/publishers/nodes/add")
    api.add_resource(PublishersNode, "/api/publishers/node/<id>")

    api.add_resource(PublishingChannels, "/api/publishers/channels")
    api.add_resource(AddPublishingChannel, "/api/publishers/channels/add")
    api.add_resource(PublishingChannel, "/api/publishers/channel/<id>")

    Permission.add("CONFIG_PUBLISHERS_NODE_ACCESS", "Config publishers nodes access", "Access to publishers nodes configuration")
    Permission.add("CONFIG_PUBLISHERS_NODE_CREATE", "Config publishers node create", "Create publishers node configuration")
    Permission.add("CONFIG_PUBLISHERS_NODE_UPDATE", "Config publishers node update", "Update publishers node configuration")
    Permission.add("CONFIG_PUBLISHERS_NODE_DELETE", "Config publishers node delete", "Delete publishers node configuration")

    Permission.add("CONFIG_PUBLISHING_CHANNEL_ACCESS", "Config publishing channels access", "Access to publishing channels configuration")
    Permission.add("CONFIG_PUBLISHING_CHANNEL_CREATE", "Config publishing channel create", "Create publishing channel configuration")
    Permission.add("CONFIG_PUBLISHING_CHANNEL_UPDATE", "Config publishing channel update", "Update publishing channel configuration")
    Permission.add("CONFIG_PUBLISHING_CHANNEL_DELETE", "Config publishing channel delete", "Delete publishing channel configuration")
