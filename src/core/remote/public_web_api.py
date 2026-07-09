"""Public-web node management API client.

Core uses this to reach a public-web node's management endpoints — a health probe
and a cache-reset push (sent when a web's configuration changes so edits are
visible immediately). Mirrors the other ``*Api`` node clients; authenticates with
the shared node ApiKey. All calls are best-effort: an unreachable node returns a
non-OK status rather than raising into the caller.
"""

from http import HTTPStatus

import requests
from managers.log_manager import logger

_TIMEOUT = 5


class PublicWebApi:
    """Client for a public-web node's management endpoints."""

    def __init__(self, api_url: str, api_key: str) -> None:
        """Initialize with the node's base URL and ApiKey."""
        self.api_url = (api_url or "").removesuffix("/")
        self.api_key = api_key
        self.headers = {"Authorization": "ApiKey " + (api_key or "")}

    def isalive(self) -> tuple[dict, HTTPStatus]:
        """Return whether the node's management API is reachable."""
        try:
            response = requests.get(self.api_url + "/management/isalive", headers=self.headers, timeout=_TIMEOUT)
            return (response.json() if response.content else {}), HTTPStatus(response.status_code)
        except requests.RequestException as exc:
            logger.debug(f"Public-web node isalive failed for '{self.api_url}': {exc}")
            return {"error": str(exc)}, HTTPStatus.SERVICE_UNAVAILABLE

    def reset_cache(self) -> tuple[dict, HTTPStatus]:
        """Ask the node to clear its cache (called after a config change)."""
        try:
            response = requests.post(self.api_url + "/management/reset-cache", headers=self.headers, timeout=_TIMEOUT)
            return (response.json() if response.content else {}), HTTPStatus(response.status_code)
        except requests.RequestException as exc:
            logger.debug(f"Public-web node reset-cache failed for '{self.api_url}': {exc}")
            return {"error": str(exc)}, HTTPStatus.SERVICE_UNAVAILABLE

    def test_email(self, payload: dict) -> tuple[dict, HTTPStatus]:
        """Ask the node to send a test e-mail with the provided SMTP settings."""
        try:
            response = requests.post(
                self.api_url + "/management/test-email",
                json=payload,
                headers=self.headers,
                timeout=_TIMEOUT,
            )
            return (response.json() if response.content else {}), HTTPStatus(response.status_code)
        except requests.RequestException as exc:
            logger.debug(f"Public-web node test-email failed for '{self.api_url}': {exc}")
            return {"error": str(exc)}, HTTPStatus.SERVICE_UNAVAILABLE
