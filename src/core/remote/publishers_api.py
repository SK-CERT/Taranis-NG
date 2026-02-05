"""Publishers API."""

from http import HTTPStatus

import requests


class PublishersApi:
    """Client for remote publishers endpoints."""

    def __init__(self, api_url: str, api_key: str) -> None:
        """Initialize the PublishersApi instance.

        Parameters:
            api_url (str): The base URL of the remote API.
            api_key (str): The API key for authentication.
        """
        self.api_url = api_url
        self.api_url = self.api_url.removesuffix("/")
        self.api_key = api_key
        self.headers = {"Authorization": "Bearer " + self.api_key}

    def get_publishers_info(self) -> tuple[dict, HTTPStatus]:
        """Return publishers JSON and HTTP status.

        Returns:
            tuple: A tuple containing the response JSON and status code.
        """
        response = requests.get(self.api_url + "/api/v1/publishers", headers=self.headers, timeout=10)
        return response.json(), response.status_code

    def publish(self, data: dict) -> tuple[dict, HTTPStatus]:
        """Publish and return JSON and HTTP status.

        Arg:
            data (dict): Data for presenter generation.

        Returns:
            tuple: A tuple containing the response JSON and status code.
        """
        response = requests.post(self.api_url + "/api/v1/publishers", json=data, headers=self.headers, timeout=60)
        return response.json(), response.status_code
