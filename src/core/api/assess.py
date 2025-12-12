"""API endpoints for the Assess module."""

import io
from http import HTTPStatus

from flask import request, send_file
from flask_restful import Resource
from managers import auth_manager, log_manager
from managers.auth_manager import ACLCheck, auth_required
from managers.log_manager import logger
from managers.sse_manager import sse_manager
from model import news_item, osint_source
from model.permission import Permission


class OSINTSourceGroupsAssess(Resource):
    """OSINT source groups for Assess API endpoint."""

    @auth_required("ASSESS_ACCESS")
    def get(self) -> dict:
        """Get all OSINT source groups for Assess."""
        return osint_source.OSINTSourceGroup.get_all_json(None, auth_manager.get_user_from_jwt(), acl_check=True)


class ManualOSINTSources(Resource):
    """Manual OSINT sources for Assess API endpoint."""

    @auth_required(["ASSESS_ACCESS"])
    def get(self) -> dict:
        """Get all manual OSINT sources for Assess."""
        return osint_source.OSINTSource.get_all_manual_json(auth_manager.get_user_from_jwt())


class AddNewsItem(Resource):
    """Add news item API endpoint."""

    @auth_required("ASSESS_CREATE")
    def post(self) -> None:
        """Add a news item."""
        osint_source_ids = news_item.NewsItemAggregate.add_news_item(request.json)
        sse_manager.news_items_updated()
        sse_manager.remote_access_news_items_updated(osint_source_ids)


class NewsItemsByGroup(Resource):
    """News items by group API endpoint."""

    @auth_required("ASSESS_ACCESS")
    def get(self, group_id: str) -> dict:
        """Get news items by group.

        Args:
            group_id (str): The group ID (or 'all' for all groups)

        Returns:
            (dict): The news items by group
        """
        user = auth_manager.get_user_from_jwt()

        # Apply ACL check only for specific groups, not for 'all'
        # Check if user has access to this specific group
        if group_id != "all" and not auth_manager.check_acl(group_id, ACLCheck.OSINT_SOURCE_GROUP_ACCESS, user):
            return {"error": "Access denied"}, HTTPStatus.FORBIDDEN

        try:
            filters = {}
            if request.args.get("search"):
                filters["search"] = request.args["search"]
            if request.args.get("read"):
                filters["read"] = request.args["read"]
            if request.args.get("important"):
                filters["important"] = request.args["important"]
            if request.args.get("relevant"):
                filters["relevant"] = request.args["relevant"]
            if request.args.get("range"):
                filters["range"] = request.args["range"]
            if request.args.get("sort"):
                filters["sort"] = request.args["sort"]

            offset = int(request.args.get("offset", 0))
            limit = min(int(request.args.get("limit", 50)), HTTPStatus.OK)
        except Exception as ex:
            msg = "Get NewsItemsByGroup failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, HTTPStatus.INTERNAL_SERVER_ERROR

        return news_item.NewsItemAggregate.get_by_group_json(group_id, filters, offset, limit, user)


class NewsItem(Resource):
    """News item API endpoint."""

    @auth_required("ASSESS_ACCESS", ACLCheck.NEWS_ITEM_ACCESS)
    def get(self, item_id: str) -> dict:
        """Get a news item.

        Args:
            item_id (str): The news item ID
        Returns:
            (dict): The news item
        """
        return news_item.NewsItem.get_detail_json(item_id)

    @auth_required("ASSESS_UPDATE", ACLCheck.NEWS_ITEM_MODIFY)
    def put(self, item_id: str) -> tuple[dict, int]:
        """Update a news item.

        Args:
            item_id (str): The news item ID
        Returns:
            (dict): The response
            (int): The response code
        """
        user = auth_manager.get_user_from_jwt()
        response, osint_source_ids, code = news_item.NewsItem.update(item_id, request.json, user.id)
        sse_manager.news_items_updated()
        if osint_source_ids:
            sse_manager.remote_access_news_items_updated(osint_source_ids)
        return response, code

    @auth_required("ASSESS_DELETE", ACLCheck.NEWS_ITEM_MODIFY)
    def delete(self, item_id: str) -> tuple[dict, int]:
        """Delete a news item.

        Args:
            item_id (str): The news item ID
        Returns:
            (dict): The response
            (int): The response code
        """
        response, code = news_item.NewsItem.delete(item_id)
        sse_manager.news_items_updated()
        return response, code


class NewsItemAggregate(Resource):
    """News item aggregate API endpoint."""

    @auth_required("ASSESS_UPDATE")
    def put(self, aggregate_id: str) -> tuple[dict, int]:
        """Update a news item aggregate.

        Args:
            aggregate_id (str): The aggregate ID
        Returns:
            (dict): The response
            (int): The response code
        """
        user = auth_manager.get_user_from_jwt()
        response, osint_source_ids, code = news_item.NewsItemAggregate.update(aggregate_id, request.json, user)
        sse_manager.news_items_updated()
        if osint_source_ids:
            sse_manager.remote_access_news_items_updated(osint_source_ids)
        return response, code

    @auth_required("ASSESS_DELETE")
    def delete(self, aggregate_id: str) -> tuple[dict, int]:
        """Delete a news item aggregate.

        Args:
            aggregate_id (str): The aggregate ID
        Returns:
            (dict): The response
            (int): The response code
        """
        user = auth_manager.get_user_from_jwt()
        response, code = news_item.NewsItemAggregate.delete(aggregate_id, user)
        sse_manager.news_items_updated()
        return response, code


class GroupAction(Resource):
    """Group action API endpoint."""

    @auth_required("ASSESS_UPDATE")
    def put(self) -> tuple[dict, int]:
        """Group action.

        Returns:
            (dict): The response
            (int): The response code
        """
        user = auth_manager.get_user_from_jwt()
        action = request.json.get("action")
        osint_source_ids = set()

        if action == "DELETE":
            response, code = news_item.NewsItemAggregate.group_action_delete(request.json, user)
        else:
            response, osint_source_ids, code = news_item.NewsItemAggregate.group_action(request.json, user)

        sse_manager.news_items_updated()
        if osint_source_ids:
            sse_manager.remote_access_news_items_updated(osint_source_ids)
        return response, code


class DownloadAttachment(Resource):
    """Download attachment API endpoint."""

    def get(self, item_data_id: str, attribute_id: str) -> None:
        """Download attachment.

        Args:
            item_data_id (str): The item data ID
            attribute_id (str): The attribute ID

        Returns:
            (file): The file
        """
        if "jwt" in request.args:
            user = auth_manager.decode_user_from_jwt(request.args["jwt"])
            if user is not None:
                permissions = user.get_permissions()
                if "ASSESS_ACCESS" in permissions:
                    attribute_mapping = news_item.NewsItemDataNewsItemAttribute.find(attribute_id)
                    need_check = False
                    if attribute_mapping is not None:
                        need_check = True
                    attribute = news_item.NewsItemAttribute.find(attribute_id)
                    if (
                        need_check
                        and item_data_id == attribute_mapping.news_item_data_id
                        and news_item.NewsItemData.allowed_with_acl(
                            attribute_mapping.news_item_data_id,
                            user,
                            see=False,
                            modify=True,
                            delete=False,
                        )
                    ):
                        log_manager.store_user_activity(user, "ASSESS_ACCESS", str({"file": attribute.value}))
                        return send_file(
                            io.BytesIO(attribute.binary_data),
                            download_name=attribute.value,
                            mimetype=attribute.binary_mime_type,
                            as_attachment=True,
                        )
                    log_manager.store_auth_error_activity("Unauthorized access attempt to News Item Data")
                    return None
                log_manager.store_auth_error_activity("Insufficient permissions")
                return None
            log_manager.store_auth_error_activity("Invalid JWT")
            return None
        log_manager.store_auth_error_activity("Missing JWT")
        return None


def initialize(api: object) -> None:
    """Initialize Assess API endpoints."""
    api.add_resource(OSINTSourceGroupsAssess, "/api/v1/assess/osint-source-groups")
    api.add_resource(ManualOSINTSources, "/api/v1/assess/manual-osint-sources")
    api.add_resource(AddNewsItem, "/api/v1/assess/news-items")
    api.add_resource(NewsItemsByGroup, "/api/v1/assess/news-item-aggregates-by-group/<string:group_id>")
    api.add_resource(NewsItem, "/api/v1/assess/news-items/<int:item_id>")
    api.add_resource(NewsItemAggregate, "/api/v1/assess/news-item-aggregates/<int:aggregate_id>")
    api.add_resource(GroupAction, "/api/v1/assess/news-item-aggregates-group-action")
    api.add_resource(DownloadAttachment, "/api/v1/assess/news-item-data/<string:item_data_id>/attributes/<int:attribute_id>/file")

    Permission.add("ASSESS_ACCESS", "Assess access", "Access to Assess module")
    Permission.add("ASSESS_CREATE", "Assess create", "Create news item")
    Permission.add("ASSESS_UPDATE", "Assess update", "Update news item")
    Permission.add("ASSESS_DELETE", "Assess delete", "Delete news item")
