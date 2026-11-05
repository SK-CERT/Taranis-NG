"""Remote synchronization APIs: legacy v1 wall clocks and explicit UTC in v2."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from flask import request
from flask_restful import Resource
from managers.auth_manager import api_key_required
from marshmallow import ValidationError
from model import news_item, report_item
from shared.remote_protocol import format_remote_timestamp, legacy_news_items

if TYPE_CHECKING:
    from flask_restful import Api
    from model.osint_source import OSINTSource
    from model.remote import RemoteAccess
    from model.report_item_type import ReportItemType


class _RemoteResource(Resource):
    """Bind one response contract to each separately registered API version."""

    def __init__(self, api_version: int = 1) -> None:
        """Bind a resource to one remote API version.

        Args:
            api_version: Version registered for this endpoint: legacy v1 or UTC v2.
        """
        self.api_version = api_version


def _sync_payload() -> dict:
    """Read the synchronization acknowledgment from the request.

    Returns:
        The request object containing a string last_sync_time cursor.

    Raises:
        ValidationError: If the request is not an object or its cursor is missing or invalid.
    """
    data = request.get_json()
    if not isinstance(data, dict) or not isinstance(data.get("last_sync_time"), str):
        raise ValidationError({"last_sync_time": ["A timestamp string is required."]})
    return data


class RemoteConnect(_RemoteResource):
    """Connect a remote without changing the original connection response keys."""

    @api_key_required("remote")
    def get(self, remote_node: RemoteAccess) -> dict | tuple:
        """Connect the authenticated remote and return its synchronization state.

        Args:
            remote_node: Remote access configuration.

        Returns:
            Connection metadata with event_id, availability flags and synchronization cursors,
            or an error response with its HTTP status. V1 cursors use the configured legacy
            timezone and no offset; v2 cursors use ISO 8601 UTC.
        """
        response = remote_node.connect()
        if not isinstance(response, dict):
            return response
        response = response.copy()
        for key in ("last_synced_news_items", "last_synced_report_items"):
            if key in response:
                response[key] = format_remote_timestamp(
                    response[key],
                    version=self.api_version,
                    legacy_timezone=remote_node.legacy_timezone,
                    cursor=True,
                )
        return response


class RemoteDisconnect(_RemoteResource):
    """Resource for handling remote disconnection.

    Methods:
        get(remote_node): Disconnects from the remote node.
    """

    @api_key_required("remote")
    def get(self, remote_node: RemoteAccess) -> dict:
        """Disconnect from the remote node.

        Args:
            remote_node: Remote access configuration.

        Returns:
            An empty object after the remote access is marked disconnected.
        """
        return remote_node.disconnect()


class RemoteSyncNewsItems(_RemoteResource):
    """Resource for syncing news items with the remote node.

    Methods:
        get(remote_node): Retrieves news items for synchronization.
        put(remote_node): Updates the news items synchronization status.
    """

    @api_key_required("remote")
    def get(self, remote_node: RemoteAccess) -> dict:
        """Retrieve news items available to the authenticated remote.

        Args:
            remote_node: Remote access configuration defining the shared sources and last cursor.

        Returns:
            An object containing news_items and last_sync_time. V1 timestamp metadata uses
            legacy wall-clock formats; v2 uses explicit UTC timestamps. Source-owned text
            and arbitrary news attributes retain their existing meaning.
        """
        items, last_sync_time = news_item.NewsItemData.get_for_sync(
            remote_node.last_synced_news_items,
            cast("list[OSINTSource]", remote_node.osint_sources),
        )
        if self.api_version == 1:
            items = legacy_news_items(items, legacy_timezone=remote_node.legacy_timezone)
        return {
            "last_sync_time": format_remote_timestamp(
                last_sync_time,
                version=self.api_version,
                legacy_timezone=remote_node.legacy_timezone,
                cursor=True,
            ),
            "news_items": items,
        }

    @api_key_required("remote")
    def put(self, remote_node: RemoteAccess) -> None:
        """Confirm successful news synchronization.

        Args:
            remote_node: Remote access configuration whose last synchronization cursor is updated.

        Returns:
            None. The cursor is persisted after parsing according to the endpoint version.

        Raises:
            ValidationError: If the request cursor is invalid or a v2 cursor has no offset.
        """
        remote_node.update_news_items_sync(_sync_payload(), api_version=self.api_version)


class RemoteSyncReportItems(_RemoteResource):
    """Resource for syncing report items with the remote node.

    Methods:
        get(remote_node): Retrieves report items for synchronization.
        put(remote_node): Updates the report items synchronization status.
    """

    @api_key_required("remote")
    def get(self, remote_node: RemoteAccess) -> dict:
        """Retrieve report items for synchronization.

        Args:
            remote_node: Remote access configuration defining the shared report types and last cursor.

        Returns:
            An object containing report_items and last_sync_time. The report structure is
            unchanged between versions; v1 returns a legacy wall-clock cursor and v2 a UTC cursor.
        """
        items, last_sync_time = report_item.ReportItem.get_for_sync(
            remote_node.last_synced_report_items,
            cast("list[ReportItemType]", remote_node.report_item_types),
        )
        return {
            "last_sync_time": format_remote_timestamp(
                last_sync_time,
                version=self.api_version,
                legacy_timezone=remote_node.legacy_timezone,
                cursor=True,
            ),
            "report_items": items,
        }

    @api_key_required("remote")
    def put(self, remote_node: RemoteAccess) -> None:
        """Confirm successful report synchronization.

        Args:
            remote_node: Remote access configuration whose last synchronization cursor is updated.

        Returns:
            None. The cursor is persisted after parsing according to the endpoint version.

        Raises:
            ValidationError: If the request cursor is invalid or a v2 cursor has no offset.
        """
        remote_node.update_report_items_sync(_sync_payload(), api_version=self.api_version)


def initialize(api: Api) -> None:
    """Register the remote synchronization resources for v1 and v2.

    Args:
        api: Flask-RESTful API receiving both versions of the authenticated resources.

    Returns:
        None. Resources are registered under /api/v1/remote and /api/v2/remote.
    """
    resources = (
        (RemoteConnect, "connect"),
        (RemoteDisconnect, "disconnect"),
        (RemoteSyncNewsItems, "sync-news-items"),
        (RemoteSyncReportItems, "sync-report-items"),
    )
    for version in (1, 2):
        for resource, path in resources:
            endpoint = resource.__name__.lower() + ("" if version == 1 else "_v2")
            api.add_resource(
                resource,
                f"/api/v{version}/remote/{path}",
                endpoint=endpoint,
                resource_class_kwargs={"api_version": version},
            )
