"""This module defines API resources for managing assets, asset groups, notification templates in the "My Assets" module.

It uses Flask-RESTful to define resource classes and Flask for handling HTTP requests.
Authentication is enforced using decorators from the `auth_manager`.
"""

from flask import request
from flask_restful import Resource
from managers import auth_manager
from managers.auth_manager import auth_required
from model import asset, attribute, notification_template
from model.permission import Permission

from shared.schema.attribute import AttributeType


class AssetGroups(Resource):
    """Resource for managing asset groups."""

    @auth_required("MY_ASSETS_ACCESS")
    def get(self):
        """Retrieve all asset groups for the authenticated user.

        Query Parameters:
            search (str): Optional search term to filter asset groups.

        Returns:
            list: JSON representation of asset groups.
        """
        search = None
        if request.args.get("search"):
            search = request.args["search"]
        return asset.AssetGroup.get_all_json(auth_manager.get_user_from_jwt(), search)

    @auth_required("MY_ASSETS_CONFIG")
    def post(self):
        """Create a new asset group.

        Request Body:
            JSON: Data for the new asset group.

        Returns:
            tuple: Empty string and status code.
        """
        return "", asset.AssetGroup.add(auth_manager.get_user_from_jwt(), request.json)


class AssetGroup(Resource):
    """Resource for managing a single asset group."""

    @auth_required("MY_ASSETS_CONFIG")
    def put(self, group_id):
        """Update an existing asset group.

        Args:
            group_id (str): ID of the asset group to update.

        Request Body:
            JSON: Updated data for the asset group.
        """
        asset.AssetGroup.update(auth_manager.get_user_from_jwt(), group_id, request.json)

    @auth_required("MY_ASSETS_CONFIG")
    def delete(self, group_id):
        """Delete an asset group.

        Args:
            group_id (str): ID of the asset group to delete.

        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        return asset.AssetGroup.delete(auth_manager.get_user_from_jwt(), group_id)


class NotificationTemplates(Resource):
    """Resource for managing notification templates."""

    @auth_required("MY_ASSETS_CONFIG")
    def get(self):
        """Retrieve all notification templates for the authenticated user.

        Query Parameters:
            search (str): Optional search term to filter templates.

        Returns:
            list: JSON representation of notification templates.
        """
        search = None
        if request.args.get("search"):
            search = request.args["search"]
        return notification_template.NotificationTemplate.get_all_json(auth_manager.get_user_from_jwt(), search)

    @auth_required("MY_ASSETS_CONFIG")
    def post(self):
        """Create a new notification template.

        Request Body:
            JSON: Data for the new notification template.

        Returns:
            tuple: Empty string and status code.
        """
        return "", notification_template.NotificationTemplate.add(auth_manager.get_user_from_jwt(), request.json)


class NotificationTemplate(Resource):
    """Resource for managing a single notification template."""

    @auth_required("MY_ASSETS_CONFIG")
    def put(self, template_id):
        """Update an existing notification template.

        Args:
            template_id (int): ID of the notification template to update.

        Request Body:
            JSON: Updated data for the notification template.
        """
        notification_template.NotificationTemplate.update(auth_manager.get_user_from_jwt(), template_id, request.json)

    @auth_required("MY_ASSETS_CONFIG")
    def delete(self, template_id):
        """Delete a notification template.

        Args:
            template_id (int): ID of the notification template to delete.

        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        return notification_template.NotificationTemplate.delete(auth_manager.get_user_from_jwt(), template_id)


class Assets(Resource):
    """Resource for managing assets within a group."""

    @auth_required("MY_ASSETS_ACCESS")
    def get(self, group_id):
        """Retrieve all assets in a group for the authenticated user.

        Args:
            group_id (str): ID of the asset group.

        Query Parameters:
            search (str): Optional search term to filter assets.
            sort (str): Optional sort order for assets.
            vulnerable (str): Optional filter for vulnerable assets.

        Returns:
            list: JSON representation of assets.
        """
        search = None
        sort = None
        vulnerable = None
        if request.args.get("search"):
            search = request.args["search"]
        if request.args.get("sort"):
            sort = request.args["sort"]
        if request.args.get("vulnerable"):
            vulnerable = request.args["vulnerable"]
        return asset.Asset.get_all_json(auth_manager.get_user_from_jwt(), group_id, search, sort, vulnerable)

    @auth_required("MY_ASSETS_CREATE")
    def post(self, group_id):
        """Create a new asset in a group.

        Args:
            group_id (str): ID of the asset group.

        Request Body:
            JSON: Data for the new asset.

        Returns:
            tuple: Empty string and status code.
        """
        return "", asset.Asset.add(auth_manager.get_user_from_jwt(), group_id, request.json)


class Asset(Resource):
    """Resource for managing a single asset."""

    @auth_required("MY_ASSETS_CREATE")
    def put(self, group_id, asset_id):
        """Update an existing asset.

        Args:
            group_id (str): ID of the asset group.
            asset_id (int): ID of the asset to update.

        Request Body:
            JSON: Updated data for the asset.
        """
        asset.Asset.update(auth_manager.get_user_from_jwt(), group_id, asset_id, request.json)

    @auth_required("MY_ASSETS_CREATE")
    def delete(self, group_id, asset_id):
        """Delete an asset.

        Args:
            group_id (str): ID of the asset group.
            asset_id (int): ID of the asset to delete.

        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        return asset.Asset.delete(auth_manager.get_user_from_jwt(), group_id, asset_id)


class AssetVulnerability(Resource):
    """Resource for managing vulnerabilities of an asset."""

    @auth_required("MY_ASSETS_CREATE")
    def put(self, group_id, asset_id, vulnerability_id):
        """Mark a vulnerability as solved for an asset.

        Args:
            group_id (str): ID of the asset group.
            asset_id (int): ID of the asset.
            vulnerability_id (int): ID of the vulnerability.

        Request Body:
            JSON: Data indicating whether the vulnerability is solved.

        Returns:
            bool: True if the operation was successful, False otherwise.
        """
        return asset.Asset.solve_vulnerability(auth_manager.get_user_from_jwt(), group_id, asset_id, vulnerability_id, request.json["solved"])


class GetAttributeCPE(Resource):
    """Resource for retrieving the CPE attribute."""

    @auth_required("MY_ASSETS_CREATE")
    def get(self):
        """Retrieve the CPE attribute.

        Returns:
            int: ID of the CPE attribute.
        """
        cpe = attribute.Attribute.find_by_type(AttributeType.CPE)
        return cpe.id


class AttributeCPEEnums(Resource):
    """Resource for managing CPE attribute enums."""

    @auth_required("MY_ASSETS_CREATE")
    def get(self):
        """Retrieve enums for the CPE attribute.

        Query Parameters:
            search (str): Optional search term to filter enums.
            offset (int): Offset for pagination (default: 0).
            limit (int): Limit for pagination (default: 10).

        Returns:
            list: JSON representation of CPE attribute enums.
        """
        cpe = attribute.Attribute.find_by_type(AttributeType.CPE)
        search = None
        offset = 0
        limit = 10
        if request.args.get("search"):
            search = request.args["search"]
        if request.args.get("offset"):
            offset = request.args["offset"]
        if request.args.get("limit"):
            limit = request.args["limit"]
        return attribute.AttributeEnum.get_for_attribute_json(cpe.id, search, offset, limit)


def initialize(api):
    """Initialize the API with the defined resources and permissions.

    Args:
        api (Api): Flask-RESTful API instance.
    """
    api.add_resource(AssetGroups, "/api/v1/my-assets/asset-groups")
    api.add_resource(AssetGroup, "/api/v1/my-assets/asset-groups/<string:group_id>")

    api.add_resource(NotificationTemplates, "/api/v1/my-assets/asset-notification-templates")
    api.add_resource(NotificationTemplate, "/api/v1/my-assets/asset-notification-templates/<int:template_id>")

    api.add_resource(Assets, "/api/v1/my-assets/asset-groups/<string:group_id>/assets")
    api.add_resource(Asset, "/api/v1/my-assets/asset-groups/<string:group_id>/assets/<int:asset_id>")

    api.add_resource(
        AssetVulnerability,
        "/api/v1/my-assets/asset-groups/<string:group_id>/assets/<int:asset_id>/vulnerabilities/<int:vulnerability_id>",
    )

    api.add_resource(GetAttributeCPE, "/api/v1/my-assets/attributes/cpe")
    api.add_resource(AttributeCPEEnums, "/api/v1/my-assets/attributes/cpe/enums")

    Permission.add("MY_ASSETS_CONFIG", "My Assets config", "Access to My Assets module configuration")
    Permission.add("MY_ASSETS_ACCESS", "My Assets access", "Access to My Assets module")
    Permission.add("MY_ASSETS_CREATE", "My Assets create", "Creation of products in My Assets module")
