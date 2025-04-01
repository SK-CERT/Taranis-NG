"""Bots API endpoints."""

from flask import request
from flask_restful import Resource, reqparse

from managers.log_manager import logger
from managers.sse_manager import sse_manager
from managers.auth_manager import api_key_required
from model import bot_preset, news_item, word_list


class BotPresetsForBots(Resource):
    """Bot presets for bots API endpoint."""

    @api_key_required("bots")
    def post(self, bots_node=None):
        """Add a new bot preset.

        Returns:
            (dict): The new bot preset
        """
        parser = reqparse.RequestParser()
        parser.add_argument("bot_type", location="args")
        parameters = parser.parse_args()

        bots_node.updateLastSeen()

        return bot_preset.BotPreset.get_all_for_bot_json(bots_node, parameters.bot_type)


class BotGroupAction(Resource):
    """Bot group action API endpoint."""

    @api_key_required("bots")
    def put(self, bots_node=None):
        """Group action for news items.

        Returns:
            response (dict): The response
            code (int): The response code
        """
        response, osint_source_ids, code = news_item.NewsItemAggregate.group_action(request.json, None)
        sse_manager.news_items_updated()
        if len(osint_source_ids) > 0:
            sse_manager.remote_access_news_items_updated(osint_source_ids)
        return response, code


class NewsItemData(Resource):
    """News item data API endpoint."""

    @api_key_required("bots")
    def get(self, bots_node=None):
        """Get all news items data.

        Returns:
            (dict): All news items data
        """
        try:
            limit = None
            if "limit" in request.args and request.args["limit"]:
                limit = request.args["limit"]
        except Exception as ex:
            msg = "Get NewsItemData failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, 400

        return news_item.NewsItemData.get_all_news_items_data(limit)


class UpdateNewsItemAttributes(Resource):
    """Update news item attributes API endpoint."""

    @api_key_required("bots")
    def put(self, news_item_data_id, bots_node=None):
        """Update news item attributes.

        Args:
            news_item_data_id (str): The news item data ID
        Returns:
            (dict): The updated news item attributes
        """
        news_item.NewsItemData.update_news_item_attributes(news_item_data_id, request.json)


class GetNewsItemsAggregate(Resource):
    """Get news items aggregate API endpoint."""

    @api_key_required("bots")
    def get(self, group_id, bots_node=None):
        """Get news items aggregate.

        Args:
            group_id (str): The group ID
        Returns:
            (dict): The news items aggregate
        """
        return news_item.NewsItemAggregate.get_news_items_aggregate(group_id, request.json)


class Categories(Resource):
    """Word list categories API endpoint."""

    @api_key_required("bots")
    def get(self, category_id, bots_node=None):
        """Get word list categories.

        Args:
            category_id (int): The category ID
        Returns:
            (dict): The word list categories
        """
        return word_list.WordListCategory.get_categories(category_id)

    @api_key_required("bots")
    def put(self, category_id, bots_node=None):
        """Update word list categories.

        Args:
            category_id (int): The category ID
        Returns:
            (dict): The updated word list categories
        """
        return word_list.WordList.add_word_list_category(category_id, request.json)


class Entries(Resource):
    """Word list entries API endpoint."""

    @api_key_required("bots")
    def delete(self, category_id, entry_name, bots_node=None):
        """Delete word list entries.

        Args:
            category_id (int): The category ID
            entry_name (str): The entry name
        Returns:
            (dict): The word list entries
        """
        return word_list.WordListEntry.delete_entries(category_id, entry_name)

    @api_key_required("bots")
    def put(self, category_id, entry_name, bots_node=None):
        """Update word list entries.

        Args:
            category_id (int): The category ID
            entry_name (str): The entry name
        Returns:
            (dict): The updated word list entries
        """
        return word_list.WordListEntry.update_word_list_entries(category_id, entry_name, request.json)


def initialize(api):
    """Initialize bots API endpoints.

    Args:
        api (object): The API object
    """
    api.add_resource(BotPresetsForBots, "/api/v1/bots/bots-presets")
    api.add_resource(NewsItemData, "/api/v1/bots/news-item-data")
    api.add_resource(UpdateNewsItemAttributes, "/api/v1/bots/news-item-data/<string:news_item_data_id>/attributes")
    api.add_resource(BotGroupAction, "/api/v1/bots/news-item-aggregates-group-action")
    api.add_resource(GetNewsItemsAggregate, "/api/v1/bots/news-item-aggregates-by-group/<string:group_id>")
    api.add_resource(Categories, "/api/v1/bots/word-list-categories/<int:category_id>")
    api.add_resource(Entries, "/api/v1/bots/word-list-categories/<int:category_id>/entries/<string:entry_name>")
