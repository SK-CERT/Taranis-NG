"""Remote API client for collectors endpoints."""

from http import HTTPStatus

import requests


class CollectorsApi:
    """Client for collectors endpoints.

    Args:
        api_url: Base URL of the remote API.
        api_key: API key for Authorization header.
    """

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

    def get_collectors_info(self, collector_id: str) -> tuple[dict, HTTPStatus]:
        """Request collectors info for given id.

        Args:
            collector_id: Collector identifier.

        Returns:
            tuple[dict, HTTPStatus]: Parsed JSON response and HTTP status code.
        """
        response = requests.post(
            self.api_url + "/api/v1/collectors",
            headers=self.headers,
            json={
                "id": collector_id,
            },
            timeout=10,
        )
        return response.json(), response.status_code

    def refresh_collector(self, collector_type: str) -> HTTPStatus:
        """Trigger refresh for specified collector type and return status.

        Args:
            collector_type: Collector type to refresh.

        Returns:
            HTTPStatus: HTTP response status code.
        """
        response = requests.put(self.api_url + "/api/v1/collectors/" + collector_type, headers=self.headers, timeout=10)
        return response.status_code
