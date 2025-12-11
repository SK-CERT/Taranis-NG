"""Bots API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from http import HTTPStatus

    from flask_restful import Api
    from model.bots_node import BotsNode

from flask import request
from flask_restful import Resource, reqparse
from managers.auth_manager import api_key_required
from managers.log_manager import logger
from managers.sse_manager import sse_manager
from model import bot_preset, news_item, word_list


class BotPresetsForBotsResource(Resource):
    """Bot presets for bots API endpoint."""

    @api_key_required("bots")
    def post(self, bots_node: BotsNode = None) -> dict:
        """Add a new bot preset.

        Args:
            bots_node (BotsNode): The bots node

        Returns:
            (dict): The new bot preset
        """
        parser = reqparse.RequestParser()
        parser.add_argument("bot_type", location="args")
        parameters = parser.parse_args()

        bots_node.updateLastSeen()

        return bot_preset.BotPreset.get_all_for_bot_json(bots_node, parameters.bot_type)


class GroupActionResource(Resource):
    """Bot group action API endpoint."""

    @api_key_required("bots")
    def put(self, bots_node: BotsNode = None) -> tuple[str, HTTPStatus]:  # noqa: ARG002
        """Group action for news items.

        Args:
            bots_node (BotsNode): The bots node

        Returns:
            response (dict): The response
            code (HTTPStatus): The response code
        """
        response, osint_source_ids, code = news_item.NewsItemAggregate.group_action(request.json, None)
        sse_manager.news_items_updated()
        if osint_source_ids:
            sse_manager.remote_access_news_items_updated(osint_source_ids)
        return response, code


class NewsItemDataResource(Resource):
    """News item data API endpoint."""

    @api_key_required("bots")
    def get(self, bots_node: BotsNode = None) -> dict:  # noqa: ARG002
        """Get all news items data.

        Args:
            bots_node (BotsNode): The bots node

        Returns:
            (dict): All news items data
        """
        try:
            limit = None
            if request.args.get("limit"):
                limit = request.args["limit"]
        except Exception as ex:
            msg = "Get NewsItemData failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, 400

        return news_item.NewsItemData.get_all_news_items_data(limit)


class NewsItemAttributesResource(Resource):
    """Update news item attributes API endpoint."""

    @api_key_required("bots")
    def put(self, news_item_data_id: int, bots_node: BotsNode = None) -> None:  # noqa: ARG002
        """Update news item attributes.

        Args:
            news_item_data_id (str): The news item data ID
            bots_node (BotsNode): The bots node

        Returns:
            (dict): The updated news item attributes
        """
        news_item.NewsItemData.update_news_item_attributes(news_item_data_id, request.json)


class NewsItemAggregatesResource(Resource):
    """Get news items aggregate API endpoint."""

    @api_key_required("bots")
    def get(self, group_id: int, bots_node: BotsNode = None) -> dict:  # noqa: ARG002
        """Get news items aggregate.

        Args:
            group_id (int): The group ID
            bots_node (BotsNode): The bots node

        Returns:
            (dict): The news items aggregate
        """
        return news_item.NewsItemAggregate.get_news_items_aggregate(group_id, request.json)


class CategoriesResource(Resource):
    """Word list categories API endpoint."""

    @api_key_required("bots")
    def get(self, category_id: int, bots_node: BotsNode = None) -> dict:  # noqa: ARG002
        """Get word list categories.

        Args:
            category_id (int): The category ID
            bots_node (BotsNode): The bots node

        Returns:
            (dict): The word list categories
        """
        return word_list.WordListCategory.get_categories(category_id)

    @api_key_required("bots")
    def put(self, category_id: int, bots_node: BotsNode = None) -> None:  # noqa: ARG002
        """Update word list categories.

        Args:
            category_id (int): The category ID
            bots_node (BotsNode): The bots node
        """
        word_list.WordList.add_word_list_category(category_id, request.json)


class EntriesResource(Resource):
    """Word list entries API endpoint."""

    @api_key_required("bots")
    def delete(self, category_id: int, entry_name: str, bots_node: BotsNode = None) -> None:  # noqa: ARG002
        """Delete word list entries.

        Args:
            category_id (int): The category ID
            entry_name (str): The entry name
            bots_node (BotsNode): The bots node
        """
        word_list.WordListEntry.delete_entries(category_id, entry_name)

    @api_key_required("bots")
    def put(self, category_id: int, entry_name: str, bots_node: BotsNode = None) -> None:  # noqa: ARG002
        """Update word list entries.

        Args:
            category_id (int): The category ID
            entry_name (str): The entry name
            bots_node (BotsNode): The bots node
        """
        word_list.WordListEntry.update_word_list_entries(category_id, entry_name, request.json)


def initialize(api: Api) -> None:
    """Initialize bots API endpoints.

    Args:
        api (object): The API object
    """
    api.add_resource(BotPresetsForBotsResource, "/api/v1/bots/bots-presets")
    api.add_resource(NewsItemDataResource, "/api/v1/bots/news-item-data")
    api.add_resource(NewsItemAttributesResource, "/api/v1/bots/news-item-data/<string:news_item_data_id>/attributes")
    api.add_resource(GroupActionResource, "/api/v1/bots/news-item-aggregates-group-action")
    api.add_resource(NewsItemAggregatesResource, "/api/v1/bots/news-item-aggregates-by-group/<string:group_id>")
    api.add_resource(CategoriesResource, "/api/v1/bots/word-list-categories/<int:category_id>")
    api.add_resource(EntriesResource, "/api/v1/bots/word-list-categories/<int:category_id>/entries/<string:entry_name>")
