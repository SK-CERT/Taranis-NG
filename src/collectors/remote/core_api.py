"""This module provides methods for interacting with the Taranis-NG API."""

import os
import requests
import urllib
from config import Config
from shared.log_manager import logger


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
        update_collector_last_attempt(source_id): Updates the last attempt time for a given source.
    """

    api_url = os.getenv("TARANIS_NG_CORE_URL")
    if api_url.endswith("/"):
        api_url = api_url[:-1]
    headers = {"Authorization": f"Bearer {Config.API_KEY}"}

    def read_collector_config_id():
        """
        Read the collector configuration ID from the configuration file.

        Returns:
            dict: A dictionary containing the collector ID or an error message.
        """
        config_file = os.getenv("COLLECTOR_CONFIG_FILE")
        try:
            with open(config_file, "r") as file:
                return {"id": file.read().strip()}
        except Exception as ex:
            msg = "Cannot read collector config file. Try re-saving the Collector in the application"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}

    @classmethod
    def get_osint_sources(cls, collector_type):
        """
        Retrieve the OSINT sources for a given collector type.

        Args:
            collector_type (str): The type of collector.

        Returns:
            tuple: A tuple containing the JSON response and the HTTP status code.
        """
        result = cls.read_collector_config_id()
        if "error" in result:
            return result, 500
        else:
            id = result["id"]

        try:
            response = requests.get(
                f"{cls.api_url}/api/v1/collectors/{urllib.parse.quote(id)}/osint-sources?api_key={urllib.parse.quote(Config.API_KEY)}"
                f"&collector_type={urllib.parse.quote(collector_type)}",
                headers=cls.headers,
            )
            return response.json(), response.status_code
        except Exception as ex:
            msg = "Get OSINT sources failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, 503

    @classmethod
    def update_collector_status(cls):
        """Update the status of the collector.

        This method retrieves the collector ID from the environment variable COLLECTOR_CONFIG_FILE,
        reads the collector config file, and sends a GET request to the API endpoint to update the
        collector status.

        Returns:
            tuple: A tuple containing the JSON response and the HTTP status code.
        """
        result = cls.read_collector_config_id()
        if "error" in result:
            return result, 500
        else:
            id = result["id"]

        try:
            response = requests.get(f"{cls.api_url}/api/v1/collectors/{urllib.parse.quote(id)}", headers=cls.headers)
            return response.json(), response.status_code
        except Exception as ex:
            msg = "Update collector status failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, 503

    @classmethod
    def update_collector_last_attempt(cls, source_id):
        """Update collector's "last attempted" record with current datetime.

        Args:
            source_id (str): The ID of the source.

        Returns:
            tuple: A tuple containing the JSON response and the HTTP status code.
        """
        try:
            response = requests.get(
                f"{cls.api_url}/api/v1/collectors/osint-sources/{urllib.parse.quote(source_id)}/attempt", headers=cls.headers
            )
            return response.json(), response.status_code
        except Exception as ex:
            msg = "Update collector last attemt failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, 503

    @classmethod
    def update_collector_last_error_message(cls, source_id, error_message):
        """Update collector's "last error message" record with current one.

        Args:
            source_id (str): The ID of the source.
            error_message (str): The error message to update.

        Returns:
            tuple: A tuple containing the JSON response and the HTTP status code.
        """
        try:
            encoded_message = f"?message={urllib.parse.quote(error_message)}" if error_message else ""
            url = f"{cls.api_url}/api/v1/collectors/osint-sources/{urllib.parse.quote(source_id)}/error_message{encoded_message}"
            response = requests.get(url, headers=cls.headers)
            return response.json(), response.status_code
        except Exception as ex:
            msg = "Update collector last error message failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, 503

    @classmethod
    def add_news_items(cls, news_items):
        """Add news items to the collector.

        This method sends a POST request to the API endpoint for adding news items to the collector.

        Args:
            news_items (list): A list of news items to be added.

        Returns:
            int: The HTTP status code of the response.

        Raises:
            Exception: If an error occurs during the request.
        """
        try:
            response = requests.post(f"{cls.api_url}/api/v1/collectors/news-items", json=news_items, headers=cls.headers)
            return response.status_code
        except Exception as ex:
            msg = "Add news items failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, 503
