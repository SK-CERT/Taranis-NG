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

    def refresh_collector(self, collector_type: str, *, collect_now: bool = True) -> HTTPStatus:
        """Trigger refresh for specified collector type and return status.

        Args:
            collector_type: Collector type to refresh.
            collect_now: Whether the node should also collect every source of the type straight
                away. The flag is only sent when False, so an older node - which would treat it as
                part of the path - keeps behaving as it always has.

        Returns:
            HTTPStatus: HTTP response status code.
        """
        url = self.api_url + "/api/v1/collectors/" + collector_type
        params = None if collect_now else {"collect_now": "false"}
        response = requests.put(url, headers=self.headers, params=params, timeout=10)
        return response.status_code

    def collect_source(self, collector_type: str, source_id: str) -> tuple[dict, HTTPStatus]:
        """Ask the node to collect one OSINT source now.

        Args:
            collector_type: Collector type owning the source.
            source_id: Id of the source to collect.

        Returns:
            tuple[dict, HTTPStatus]: The node's answer and its status code. 202 means a run
                started, 409 means one was already in progress.
        """
        url = f"{self.api_url}/api/v1/collectors/{collector_type}/osint-sources/{source_id}/collect"
        response = requests.post(url, headers=self.headers, timeout=10)
        try:
            body = response.json()
        except ValueError:
            body = {}
        return body, response.status_code
