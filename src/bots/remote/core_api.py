"""This module provides a class to interact with the Taranis-NG Core API."""

import os
import urllib
from http import HTTPStatus

import requests
from config import Config
from shared.log_manager import logger


class CoreApi:
    """A class that provides methods to interact with the Taranis-NG Core API."""

    api_url = os.getenv("TARANIS_NG_CORE_URL")
    api_url = api_url.removesuffix("/")
    headers = {"Authorization": f"ApiKey {Config.API_KEY}"}  # noqa: RUF012

    @classmethod
    def get_bots_presets(cls, bot_type: str) -> tuple[dict, HTTPStatus]:
        """Get the presets for a specific bot type.

        This method sends a POST request to the API endpoint to retrieve the presets
        for the specified bot type.

        Arguments:
            bot_type (str): The type of bot for which to retrieve the presets.

        Returns:
            tuple: A tuple containing the JSON response and the HTTP status code.
                The JSON response contains the presets for the specified bot type.
                The HTTP status code indicates the success or failure of the request.
        """
        try:
            response = requests.post(
                f"{cls.api_url}/api/v1/bots/bots-presets?bot_type={urllib.parse.quote(bot_type)}",
                headers=cls.headers,
                timeout=10,
            )
            return response.json(), response.status_code
        except Exception as ex:
            msg = "Get bots presets failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, HTTPStatus.SERVICE_UNAVAILABLE

    @classmethod
    def get_news_items_data(cls, limit: int) -> tuple[dict, HTTPStatus]:
        """Get news items data.

        This method retrieves news items data from the API.

        Arguments:
            limit (int): The maximum number of news items to retrieve.

        Returns:
            tuple: A tuple containing the JSON response and the HTTP status code.
                   If an exception occurs, None is returned along with a status code of 400.
        """
        try:
            response = requests.get(cls.api_url + "/api/v1/bots/news-item-data?limit=" + limit, headers=cls.headers, timeout=30)
            return response.json(), response.status_code
        except Exception as ex:
            msg = "Get news items data failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, HTTPStatus.SERVICE_UNAVAILABLE

    @classmethod
    def update_news_item_attributes(cls, news_item_data_id: int, attributes: dict) -> tuple[dict, HTTPStatus]:
        """Update the attributes of a news item.

        Arguments:
            news_item_data_id (int): The ID of the news item.
            attributes (dict): The attributes to update.

        Returns:
            int: The status code of the API response.
        """
        try:
            response = requests.put(
                cls.api_url + "/api/v1/bots/news-item-data/" + news_item_data_id + "/attributes",
                json=attributes,
                headers=cls.headers,
                timeout=30,
            )
            return {}, response.status_code
        except Exception as ex:
            msg = "Update the attributes of a news item failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, HTTPStatus.SERVICE_UNAVAILABLE

    @classmethod
    def delete_word_list_category_entries(cls, category_id: int, name: str) -> tuple[dict, HTTPStatus]:
        """Delete entries from a word list category.

        This method sends a DELETE request to the API to delete entries from a word list category.

        Arguments:
            category_id (int): The ID of the word list category.
            name (str): The name of the entry to be deleted.

        Returns:
            int: The status code of the response, or None if an exception occurred.
        """
        try:
            response = requests.delete(
                cls.api_url + "/api/v1/bots/word-list-categories/" + category_id + "/entries/" + name,
                headers=cls.headers,
                timeout=10,
            )
            return {}, response.status_code
        except Exception as ex:
            msg = "Delete entries from a word list category failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, HTTPStatus.SERVICE_UNAVAILABLE

    @classmethod
    def update_word_list_category_entries(cls, category_id: int, name: str, entries: dict) -> tuple[dict, HTTPStatus]:
        """Update the entries of a word list category.

        Arguments:
            category_id (str): The ID of the word list category.
            name (str): The name of the entry.
            entries (dict): The list of entries to update.

        Returns:
            int: The status code of the API response.
        """
        try:
            response = requests.put(
                cls.api_url + "/api/v1/bots/word-list-categories/" + category_id + "/entries/" + name,
                json=entries,
                headers=cls.headers,
                timeout=10,
            )
            return {}, response.status_code
        except Exception as ex:
            msg = "Update the entries of a word list category failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, HTTPStatus.SERVICE_UNAVAILABLE

    @classmethod
    def get_categories(cls, category_id: int) -> tuple[dict, HTTPStatus]:
        """Get the categories for a specific bot.

        Arguments:
            category_id (int): The ID of the bot.

        Returns:
            dict: The categories for the bot.

        Raises:
            None

        """
        try:
            response = requests.get(cls.api_url + "/api/v1/bots/word-list-categories/" + category_id, headers=cls.headers, timeout=10)
            return response.json(), response.status_code
        except Exception as ex:
            msg = "Get the categories for a bot failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, HTTPStatus.SERVICE_UNAVAILABLE

    @classmethod
    def add_word_list_category(cls, category_id: int, category: dict) -> tuple[dict, HTTPStatus]:
        """Add a word list category.

        This method sends a PUT request to the API endpoint to add a word list category.

        Arguments:
            category_id (int): The ID of the category.
            category (dict): The category data to be added.

        Returns:
            int: The status code of the response.

        Raises:
            None

        """
        try:
            response = requests.put(
                cls.api_url + "/api/v1/bots/word-list-categories/" + category_id,
                json=category,
                headers=cls.headers,
                timeout=10,
            )
            return {}, response.status_code
        except Exception as ex:
            msg = "Add a word list category failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, HTTPStatus.SERVICE_UNAVAILABLE

    @classmethod
    def get_news_items_aggregate(cls, source_group: str, limit: int) -> tuple[dict, HTTPStatus]:
        """Get news items aggregate by source group.

        This method retrieves news item aggregates based on the specified source group and limit.

        Arguments:
            source_group (str): The source group to filter the news item aggregates.
            limit (int): The maximum number of news item aggregates to retrieve.

        Returns:
            dict: A dictionary containing the news item aggregates.

        Raises:
            None

        """
        try:
            response = requests.get(
                cls.api_url + "/api/v1/bots/news-item-aggregates-by-group/" + source_group,
                json={"limit": limit},
                headers=cls.headers,
                timeout=30,
            )
            return response.json(), response.status_code
        except Exception as ex:
            msg = "Get news items aggregate by source group failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, HTTPStatus.SERVICE_UNAVAILABLE

    @classmethod
    def news_items_grouping(cls, data: dict) -> tuple[dict, HTTPStatus]:
        """Group news items based on certain criteria.

        This method sends a PUT request to the API endpoint '/api/v1/bots/news-item-aggregates-group-action'
        with the provided data to group news items based on certain criteria.

        Arguments:
            data (dict): The data to be sent in the request body.

        Returns:
            int: The status code of the response if the request is successful.
            None: If an exception occurs during the request.

        """
        try:
            response = requests.put(
                cls.api_url + "/api/v1/bots/news-item-aggregates-group-action",
                json=data,
                headers=cls.headers,
                timeout=30,
            )
            return {}, response.status_code
        except Exception as ex:
            msg = "Group news items failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, HTTPStatus.SERVICE_UNAVAILABLE
