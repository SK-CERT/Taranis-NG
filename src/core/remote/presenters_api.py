"""Presenters API."""

from http import HTTPStatus

import requests


class PresentersApi:
    """Client for remote presenters endpoints."""

    def __init__(self, api_url: str, api_key: str) -> None:
        """Initialize the PresentersApi instance.

        Parameters:
            api_url (str): The base URL of the remote API.
            api_key (str): The API key for authentication.
        """
        self.api_url = api_url
        self.api_url = self.api_url.removesuffix("/")
        self.api_key = api_key
        self.headers = {"Authorization": "Bearer " + self.api_key}

    def get_presenters_info(self) -> tuple[dict, HTTPStatus]:
        """Return presenters JSON and HTTP status.

        Returns:
            tuple: A tuple containing the response JSON and status code.
        """
        response = requests.get(self.api_url + "/api/v1/presenters", headers=self.headers, timeout=10)
        return response.json(), response.status_code

    def generate(self, data: dict) -> tuple[dict, HTTPStatus]:
        """Create a presenter remotely and return JSON and HTTP status.

        Arg:
            data (dict): Data for presenter generation.

        Returns:
            tuple: A tuple containing the response JSON and status code.
        """
        response = requests.post(self.api_url + "/api/v1/presenters", json=data, headers=self.headers, timeout=30)
        return response.json(), response.status_code
