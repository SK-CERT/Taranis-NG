"""Remote synchronization client with explicit protocol negotiation."""

from http import HTTPStatus
from zoneinfo import ZoneInfo

import requests
from managers.log_manager import logger
from marshmallow import ValidationError
from shared.remote_protocol import (
    format_remote_timestamp,
    normalize_legacy_news_items,
    parse_remote_timestamp,
    validate_remote_news_items,
)

V2_API_VERSION = 2


class RemoteApi:
    """Class for interacting with the remote API."""

    def __init__(self, api_url: str, api_key: str, *, legacy_timezone: str = "UTC", version: int | None = None) -> None:
        """Configure a remote peer and its timestamp boundary.

        Args:
            api_url: Base URL of the remote core service.
            api_key: API key used to authenticate remote requests.
            legacy_timezone: IANA timezone for v1 timestamps that lack an offset.
            version: Previously negotiated version to reuse, or None to prefer v2 and
                discover whether the peer requires v1.
        """
        if version not in (None, 1, 2):
            msg = "Unsupported remote API version"
            raise ValueError(msg)
        ZoneInfo(legacy_timezone)
        self.api_url = api_url.removesuffix("/")
        self.api_key = api_key
        self.headers = {"Authorization": "ApiKey " + api_key}
        self.legacy_timezone = legacy_timezone
        self.version = version or V2_API_VERSION
        self._negotiate = version is None
        self.connection_accepted = False

    def _url(self, path: str) -> str:
        """Build a remote endpoint URL using the selected protocol version.

        Args:
            path: Endpoint path beneath /api/v{version}/remote/.

        Returns:
            The complete URL for the selected version and endpoint.
        """
        return f"{self.api_url}/api/v{self.version}/remote/{path}"

    @staticmethod
    def _decode(response: requests.Response) -> tuple[dict, int]:
        """Decode a response while retaining upstream error statuses.

        Args:
            response: HTTP response from the remote core service.

        Returns:
            A tuple containing a JSON object and the response status code. Non-object or
            non-JSON error responses are replaced with a generic error object.

        Raises:
            ValueError: If a successful response is not a JSON object.
        """
        try:
            data = response.json()
        except ValueError:
            if not HTTPStatus.OK <= response.status_code < HTTPStatus.MULTIPLE_CHOICES:
                return {"error": "Remote API request failed"}, response.status_code
            raise
        if not isinstance(data, dict):
            if not HTTPStatus.OK <= response.status_code < HTTPStatus.MULTIPLE_CHOICES:
                return {"error": "Remote API request failed"}, response.status_code
            msg = "Remote API response must be an object"
            raise ValueError(msg)
        return data, response.status_code

    @staticmethod
    def _failure(operation: str, error: Exception) -> tuple[dict, HTTPStatus]:
        """Convert a transport or response-validation failure into an API result.

        Args:
            operation: Description of the remote operation being attempted.
            error: Transport, parsing or validation exception to log.

        Returns:
            An error object and HTTP 503 for transport failures, or HTTP 502 for invalid responses.
        """
        logger.exception(f"Remote {operation} failed: {error}")
        code = (
            HTTPStatus.SERVICE_UNAVAILABLE
            if isinstance(error, requests.RequestException) and not isinstance(error, ValueError)
            else HTTPStatus.BAD_GATEWAY
        )
        return {"error": f"Remote {operation} failed"}, code

    def _validate_connect(self, data: dict) -> None:
        """Validate connection metadata before starting the local event listener.

        Args:
            data: Connection response containing an event ID and both synchronization cursors.

        Returns:
            None when the metadata is valid for the selected protocol version.

        Raises:
            ValueError: If the event ID is absent or empty.
            KeyError: If a required synchronization cursor is absent.
            ValidationError: If a cursor violates the selected version's timestamp contract.
        """
        if not isinstance(data.get("event_id"), str) or not data["event_id"]:
            msg = "Remote connect response is missing its event ID"
            raise ValueError(msg)
        for field in ("last_synced_news_items", "last_synced_report_items"):
            parse_remote_timestamp(data[field], version=self.version, legacy_timezone=self.legacy_timezone)

    def _prepare_sync(self, data: dict, kind: str) -> dict:
        """Validate synchronization metadata and adapt legacy news timestamps.

        Args:
            data: Response object containing last_sync_time and a list of items.
            kind: Item collection key: news_items or report_items.

        Returns:
            The validated response, with v1 news collection times normalized to UTC.
            Publication text without a known offset and arbitrary report attributes are preserved.

        Raises:
            KeyError: If a required response field is missing.
            TypeError: If the item collection is not a list of objects.
            ValidationError: If timestamp metadata violates the selected protocol version.
        """
        parse_remote_timestamp(data["last_sync_time"], version=self.version, legacy_timezone=self.legacy_timezone)
        if not isinstance(data[kind], list) or any(not isinstance(item, dict) for item in data[kind]):
            msg = "Remote sync items must be a list of objects"
            raise TypeError(msg)
        if kind == "news_items":
            if self.version == 1:
                return {**data, kind: normalize_legacy_news_items(data[kind], self.legacy_timezone)}
            validate_remote_news_items(data[kind])
        return data

    def connect(self) -> tuple[dict, int]:
        """Connect to the remote node and select its protocol version.

        Returns:
            A tuple containing connection metadata or an error object and its HTTP status.
            An unknown peer is tried with v2 first and v1 only after HTTP 404 or 405.
            The selected version is retained for subsequent synchronization requests.
        """
        self.connection_accepted = False
        try:
            response = requests.get(self._url("connect"), headers=self.headers, timeout=30)
            if (
                self._negotiate
                and self.version == V2_API_VERSION
                and response.status_code in (HTTPStatus.NOT_FOUND, HTTPStatus.METHOD_NOT_ALLOWED)
            ):
                self.version = 1
                response = requests.get(self._url("connect"), headers=self.headers, timeout=30)
            self.connection_accepted = response.status_code == HTTPStatus.OK
            data, status = self._decode(response)
            if status == HTTPStatus.OK:
                self._validate_connect(data)
            return data, status
        except (requests.RequestException, ValueError, TypeError, KeyError, ValidationError) as error:
            return self._failure("connection", error)

    def disconnect(self) -> tuple[dict, int]:
        """Disconnect from the remote node using its known protocol.

        Returns:
            A tuple containing the response object and HTTP status. When no connection
            version is known, v2 is tried first and v1 only after HTTP 404 or 405, without
            opening a new connection. A known connection's protocol is never changed.
        """
        try:
            response = requests.get(self._url("disconnect"), headers=self.headers, timeout=30)
            # Another worker may have negotiated the connection. Avoid opening a new
            # session just to discover its protocol when cleaning up that peer.
            if (
                self._negotiate
                and not self.connection_accepted
                and self.version == V2_API_VERSION
                and response.status_code in (HTTPStatus.NOT_FOUND, HTTPStatus.METHOD_NOT_ALLOWED)
            ):
                self.version = 1
                response = requests.get(self._url("disconnect"), headers=self.headers, timeout=30)
            if response.status_code == HTTPStatus.NO_CONTENT:
                return {}, response.status_code
            return self._decode(response)
        except (requests.RequestException, ValueError, TypeError, ValidationError) as error:
            return self._failure("disconnection", error)

    def _get_sync(self, kind: str) -> tuple[dict, int]:
        """Retrieve and validate a batch before it can be imported or acknowledged.

        Args:
            kind: Item collection to request: news_items or report_items.

        Returns:
            A tuple containing the validated response or an error object and its HTTP status.
            The returned cursor retains the provider's representation until acknowledgment.
        """
        path = "sync-news-items" if kind == "news_items" else "sync-report-items"
        try:
            response = requests.get(self._url(path), headers=self.headers, timeout=30)
            data, status = self._decode(response)
            if status != HTTPStatus.OK:
                return data, status
            # Keep the original cursor until the legacy PUT adapter encodes it.
            return self._prepare_sync(data, kind), status
        except (requests.RequestException, ValueError, TypeError, KeyError, ValidationError) as error:
            return self._failure("synchronization response", error)

    def get_news_items(self) -> tuple[dict, int]:
        """Retrieve news items using the selected remote protocol.

        Returns:
            A tuple containing news_items and last_sync_time, or an error object, followed
            by the HTTP status. Legacy collection timestamps are normalized to UTC.
        """
        return self._get_sync("news_items")

    def get_report_items(self) -> tuple[dict, int]:
        """Retrieve reports using the selected remote protocol.

        Returns:
            A tuple containing report_items and last_sync_time, or an error object, followed
            by the HTTP status. Arbitrary report attribute values remain unchanged.
        """
        return self._get_sync("report_items")

    def _confirm_sync(self, path: str, data: dict) -> tuple[dict, int]:
        """Acknowledge a successfully imported batch using a compatible cursor.

        Args:
            path: Synchronization endpoint path to acknowledge.
            data: Acknowledgment object containing the provider's last_sync_time cursor.

        Returns:
            A response object and HTTP status. V1 cursors are encoded in the configured
            legacy timezone with six fractional digits and no offset for old strict parsers;
            v2 preserves the returned cursor. Failed acknowledgments retain their error status.
        """
        try:
            if self.version == 1:
                cursor = parse_remote_timestamp(data["last_sync_time"], version=1, legacy_timezone=self.legacy_timezone)
                data = {
                    **data,
                    "last_sync_time": format_remote_timestamp(cursor, version=1, cursor=True, legacy_timezone=self.legacy_timezone),
                }
            response = requests.put(self._url(path), headers=self.headers, json=data, timeout=30)
            return {}, response.status_code
        except (requests.RequestException, ValueError, TypeError, KeyError, ValidationError) as error:
            return self._failure("synchronization acknowledgment", error)

    def confirm_news_items_sync(self, data: dict) -> tuple[dict, int]:
        """Confirm successful synchronization of a news batch.

        Args:
            data: Object containing the last_sync_time cursor returned with the imported batch.

        Returns:
            A tuple containing an empty object or error object and the acknowledgment HTTP status.
        """
        return self._confirm_sync("sync-news-items", data)

    def confirm_report_items_sync(self, data: dict) -> tuple[dict, int]:
        """Confirm successful synchronization of a report batch.

        Args:
            data: Object containing the last_sync_time cursor returned with the imported batch.

        Returns:
            A tuple containing an empty object or error object and the acknowledgment HTTP status.
        """
        return self._confirm_sync("sync-report-items", data)
