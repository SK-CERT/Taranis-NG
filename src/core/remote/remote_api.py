"""Remote node API."""

import requests
from managers.log_manager import logger


class RemoteApi:
    """Class for interacting with the remote API."""

    def __init__(self, api_url, api_key):
        """Initialize the RemoteApi instance.

        Parameters:
            api_url (str): The base URL of the remote API.
            api_key (str): The API key for authentication.
        """
        self.api_url = api_url
        if self.api_url.endswith("/"):
            self.api_url = self.api_url[:-1]
        self.api_key = api_key
        self.headers = {"Authorization": "Bearer " + self.api_key}

    def connect(self):
        """Connect to the remote node.

        Returns:
            tuple: A tuple containing the response JSON and status code.
        """
        try:
            response = requests.get(self.api_url + "/api/v1/remote/connect", headers=self.headers)
            return response.json(), response.status_code
        except Exception as ex:
            msg = "Connect to the remote node failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, 503

    def disconnect(self):
        """Disconnect from the remote node.

        Returns:
            tuple: A tuple containing an empty dictionary and status code.
        """
        try:
            requests.get(self.api_url + "/api/v1/remote/disconnect", headers=self.headers)
        except Exception as ex:
            msg = "Disconnect from the remote node failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, 503

    def get_news_items(self):
        """Retrieve news items from the remote node.

        Returns:
            tuple: A tuple containing the response JSON and status code.
        """
        try:
            response = requests.get(self.api_url + "/api/v1/remote/sync-news-items", headers=self.headers)
            return response.json(), response.status_code
        except Exception as ex:
            msg = "Retrieve news items from the remote node failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, 503

    def confirm_news_items_sync(self, data):
        """Confirm the synchronization of news items.

        Parameters:
            data (dict): The data to confirm synchronization.

        Returns:
            int: The status code of the response.
        """
        try:
            response = requests.put(self.api_url + "/api/v1/remote/sync-news-items", headers=self.headers, json=data)
            return response.status_code
        except Exception as ex:
            msg = "Confirm the synchronization of news items failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, 503

    def get_report_items(self):
        """Retrieve report items from the remote node.

        Returns:
            tuple: A tuple containing the response JSON and status code.
        """
        try:
            response = requests.get(self.api_url + "/api/v1/remote/sync-report-items", headers=self.headers)
            return response.json(), response.status_code
        except Exception as ex:
            msg = "Retrieve report items from the remote node failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, 503

    def confirm_report_items_sync(self, data):
        """Confirm the synchronization of report items.

        Parameters:
            data (dict): The data to confirm synchronization.

        Returns:
            int: The status code of the response.
        """
        try:
            response = requests.put(self.api_url + "/api/v1/remote/sync-report-items", headers=self.headers, json=data)
            return response.status_code
        except Exception as ex:
            msg = "Confirm the synchronization of report items failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, 503
