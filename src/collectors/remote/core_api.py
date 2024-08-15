"""This module provides methods for interacting with the Taranis-NG API."""

import logging
import os
import requests
import urllib
from config import Config

logger = logging.getLogger("gunicorn.error")
logger.level = logging.INFO

# increase logging level
if "DEBUG" in os.environ and os.environ.get("DEBUG").lower() == "true":
    logger.setLevel(logging.DEBUG)


class CoreApi:
    """
    The CoreApi class provides methods for interacting with the Taranis-NG API.

    Attributes:
        api_url (str): The URL of the Taranis-NG API.
        headers (dict): The headers to be included in API requests.

    Methods:
        get_osint_sources(collector_type): Retrieves the OSINT sources for a given collector type.
        update_collector_status(): Updates the status of the collector.
        add_news_items(news_items): Adds news items to the collector.
    """

    api_url = os.getenv("TARANIS_NG_CORE_URL")
    if api_url.endswith("/"):
        api_url = api_url[:-1]
    headers = {"Authorization": f"Bearer {Config.API_KEY}"}

    @classmethod
    def get_osint_sources(cls, collector_type):
        """
        Retrieve the OSINT sources for a given collector type.

        Args:
            collector_type (str): The type of collector.

        Returns:
            tuple: A tuple containing the JSON response and the HTTP status code.
                    If an error occurs, returns None and 400 status code.
        """
        id = ""
        config_file = os.getenv("COLLECTOR_CONFIG_FILE")
        try:
            with open(config_file, "r") as file:
                id = file.read().strip()
        except Exception as ex:
            logger.debug(ex)
            return "Cannot read collector config file.", 0

        try:
            response = requests.get(
                cls.api_url
                + "/api/v1/collectors/"
                + urllib.parse.quote(id)
                + "/osint-sources?api_key="
                + urllib.parse.quote(Config.API_KEY)
                + "&collector_type="
                + urllib.parse.quote(collector_type),
                headers=cls.headers,
            )
            return response.json(), response.status_code
        except Exception as ex:
            logger.debug(ex)
            return None, 400

    @classmethod
    def update_collector_status(cls):
        """Update the status of the collector.

        This method retrieves the collector ID from the environment variable COLLECTOR_CONFIG_FILE,
        reads the collector config file, and sends a GET request to the API endpoint to update the
        collector status.

        Returns:
            tuple: A tuple containing the JSON response and the HTTP status code.
        """
        id = ""
        config_file = os.getenv("COLLECTOR_CONFIG_FILE")
        try:
            with open(config_file, "r") as file:
                id = file.read().strip()
        except Exception as ex:
            logger.debug(ex)
            return "Cannot read collector config file.", 0

        try:
            response = requests.get(cls.api_url + "/api/v1/collectors/" + urllib.parse.quote(id), headers=cls.headers)
            return response.json(), response.status_code
        except Exception as ex:
            logger.debug(ex)
            return ex, 400

    @classmethod
    def update_collector_last_attepmt(cls, source_id):
        """Update collector's "last attempted" record with current datetime.

        Returns:
            tuple: A tuple containing the JSON response and the HTTP status code.
        """
        try:
            response = requests.get(cls.api_url + "/api/v1/collectors/osint-sources/" + urllib.parse.quote(source_id) + "/attempt", headers=cls.headers)
            return response.json(), response.status_code
        except Exception as ex:
            logger.debug(ex)
            return ex, 400

    @classmethod
    def add_news_items(cls, news_items):
        """Add news items to the collector.

        This method sends a POST request to the API endpoint for adding news items to the collector.

        Arguments:
            news_items (list): A list of news items to be added.

        Returns:
            int: The HTTP status code of the response.

        Raises:
            Exception: If an error occurs during the request.
        """
        try:
            response = requests.post(cls.api_url + "/api/v1/collectors/news-items", json=news_items, headers=cls.headers)
            return response.status_code
        except Exception as ex:
            logger.debug(ex)
            return None, 400
