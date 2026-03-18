"""Remote node API."""

from http import HTTPStatus

import requests
from managers.log_manager import logger


class RemoteApi:
    """Class for interacting with the remote API."""

    def __init__(self, api_url: str, api_key: str) -> None:
        """Initialize the RemoteApi instance.

        Parameters:
            api_url (str): The base URL of the remote API.
            api_key (str): The API key for authentication.
        """
        self.api_url = api_url
        self.api_url = self.api_url.removesuffix("/")
        self.api_key = api_key
        self.headers = {"Authorization": "ApiKey " + self.api_key}

    def connect(self) -> tuple[dict, HTTPStatus]:
        """Connect to the remote node.

        Returns:
            tuple: A tuple containing the response JSON and status code.
        """
        try:
            response = requests.get(self.api_url + "/api/v1/remote/connect", headers=self.headers, timeout=10)
            return response.json(), response.status_code
        except Exception as ex:
            msg = "Connect to the remote node failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, HTTPStatus.SERVICE_UNAVAILABLE

    def disconnect(self) -> tuple[dict, HTTPStatus]:
        """Disconnect from the remote node.

        Returns:
            tuple: A tuple containing an empty dictionary and status code.
        """
        try:
            response = requests.get(self.api_url + "/api/v1/remote/disconnect", headers=self.headers, timeout=10)
            return response.json(), response.status_code
        except Exception as ex:
            msg = "Disconnect from the remote node failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, HTTPStatus.SERVICE_UNAVAILABLE

    def get_news_items(self) -> tuple[dict, HTTPStatus]:
        """Retrieve news items from the remote node.

        Returns:
            tuple: A tuple containing the response JSON and status code.
        """
        try:
            response = requests.get(self.api_url + "/api/v1/remote/sync-news-items", headers=self.headers, timeout=30)
            return response.json(), response.status_code
        except Exception as ex:
            msg = "Retrieve news items from the remote node failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, HTTPStatus.SERVICE_UNAVAILABLE

    def confirm_news_items_sync(self, data: dict) -> tuple[dict, HTTPStatus]:
        """Confirm the synchronization of news items.

        Parameters:
            data (dict): The data to confirm synchronization.

        Returns:
            int: The status code of the response.
        """
        try:
            response = requests.put(self.api_url + "/api/v1/remote/sync-news-items", headers=self.headers, json=data, timeout=30)
            return {}, response.status_code
        except Exception as ex:
            msg = "Confirm the synchronization of news items failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, HTTPStatus.SERVICE_UNAVAILABLE

    def get_report_items(self) -> tuple[dict, HTTPStatus]:
        """Retrieve report items from the remote node.

        Returns:
            tuple: A tuple containing the response JSON and status code.
        """
        try:
            response = requests.get(self.api_url + "/api/v1/remote/sync-report-items", headers=self.headers, timeout=30)
            return response.json(), response.status_code
        except Exception as ex:
            msg = "Retrieve report items from the remote node failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, HTTPStatus.SERVICE_UNAVAILABLE

    def confirm_report_items_sync(self, data: dict) -> tuple[dict, HTTPStatus]:
        """Confirm the synchronization of report items.

        Parameters:
            data (dict): The data to confirm synchronization.

        Returns:
            int: The status code of the response.
        """
        try:
            response = requests.put(self.api_url + "/api/v1/remote/sync-report-items", headers=self.headers, json=data, timeout=30)
            return {}, response.status_code
        except Exception as ex:
            msg = "Confirm the synchronization of report items failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, HTTPStatus.SERVICE_UNAVAILABLE
