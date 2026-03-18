"""Remote API client for bots endpoints."""

from http import HTTPStatus

import requests


class BotsApi:
    """Client for bots endpoints."""

    def __init__(self, api_url: str, api_key: str) -> None:
        """Initialize client and set headers.

        Args:
            api_url: Base URL of the remote API.
            api_key: API key for Authorization header.
        """
        self.api_url = api_url
        self.api_url = self.api_url.removesuffix("/")
        self.api_key = api_key
        self.headers = {"Authorization": "ApiKey " + self.api_key}

    def get_bots_info(self) -> tuple[dict, HTTPStatus]:
        """Request list of bots.

        Returns:
            tuple[dict, HTTPStatus]: Parsed JSON response and HTTP status code.
        """
        response = requests.get(self.api_url + "/api/v1/bots", headers=self.headers, timeout=10)
        return response.json(), response.status_code
