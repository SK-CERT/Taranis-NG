"""Remote manager, Server-Sent Events (SSE) handling."""

from __future__ import annotations

import json
import threading
import time
from http import HTTPStatus
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfoNotFoundError

import requests
import sseclient
from managers import sse_manager
from managers.db_manager import db
from managers.log_manager import logger
from model.news_item import NewsItemAggregate
from model.remote import RemoteNode
from model.report_item import ReportItem
from remote.remote_api import RemoteApi

if TYPE_CHECKING:
    from flask import Flask


event_handlers: dict[int, threading.Event] = {}
remote_clients: dict[int, RemoteApi] = {}


def _clear_connection(remote_node: RemoteNode) -> None:
    """Clear the peer's listener, client and persisted connection state.

    Args:
        remote_node: Remote node whose local connection state must be cleared.

    Returns:
        None. Failed transactions are rolled back and cleanup failures are logged.
    """
    disconnect_from_events(remote_node)
    remote_clients.pop(remote_node.id, None)
    db.session.rollback()
    try:
        remote_node.disconnect()
    except Exception:
        db.session.rollback()
        logger.exception(f"Could not clear remote connection state for '{remote_node.name}'")


class EventThread(threading.Thread):
    """Consume SSE events with the same client that negotiated the connection."""

    app: Flask | None = None

    def __init__(self, remote_node: RemoteNode, event_handler: threading.Event, api: RemoteApi | None = None) -> None:
        """Configure an SSE listener with its negotiated remote client.

        Args:
            remote_node: Remote node providing the event stream and shared content.
            event_handler: Stop event used to terminate this listener.
            api: Negotiated client to retain for synchronization, or None to construct one
                from the remote node's current settings.
        """
        super().__init__()
        self.remote_node = remote_node
        self.event_handler = event_handler
        self.api = api or RemoteApi(
            remote_node.remote_url,
            remote_node.api_key,
            legacy_timezone=getattr(remote_node, "legacy_timezone", None) or "UTC",
            version=getattr(remote_node, "api_version", None),
        )

    def _sync(self, *, news: bool) -> bool:
        """Import a batch and acknowledge it only after a successful import.

        Args:
            news: Whether to synchronize news items instead of report items.

        Returns:
            True if retrieval, import, notification and acknowledgment succeed; False if
            an application context is unavailable or any stage fails. Failed imports are
            rolled back and their synchronization cursors are not acknowledged.
        """
        if self.app is None:
            logger.error("Remote event application context is not initialized")
            return False
        data, status = self.api.get_news_items() if news else self.api.get_report_items()
        if status != HTTPStatus.OK:
            logger.error(f"Get remote {'news' if news else 'report'} items failed. Code: {status}")
            return False
        try:
            with self.app.app_context():
                try:
                    if news:
                        NewsItemAggregate.add_remote_news_items(
                            data["news_items"],
                            self.remote_node,
                            self.remote_node.osint_source_group_id,
                            api_version=self.api.version,
                        )
                    else:
                        ReportItem.add_remote_report_items(data["report_items"], self.remote_node.name)
                except Exception:
                    db.session.rollback()
                    raise
                if news:
                    sse_manager.sse_manager.news_items_updated()
                else:
                    sse_manager.sse_manager.report_items_updated()
        except Exception:
            logger.exception(f"Import remote {'news' if news else 'report'} items failed for '{self.remote_node.name}'")
            return False
        confirm = self.api.confirm_news_items_sync if news else self.api.confirm_report_items_sync
        _response, acknowledgment_status = confirm({"last_sync_time": data["last_sync_time"]})
        if not HTTPStatus.OK <= acknowledgment_status < HTTPStatus.MULTIPLE_CHOICES:
            logger.error(f"Confirm remote {'news' if news else 'report'} synchronization failed. Code: {acknowledgment_status}")
            return False
        return True

    def run(self) -> None:
        """Listen for remote SSE events and dispatch synchronization requests.

        Returns:
            None. The listener exits when stopped, remotely disconnected, denied access,
            or after its connection retries are exhausted. Peer and batch errors are logged.
        """
        if self.app is None:
            logger.error("Remote event application context is not initialized")
            return
        attempt = 1
        retries = 3
        while not self.event_handler.is_set() and attempt <= retries:
            try:
                response = requests.get(
                    self.remote_node.events_url + "?channel=remote",
                    headers={"Authorization": f"ApiKey {self.remote_node.api_key}"},
                    stream=True,
                    timeout=30,
                )
                if response.status_code != HTTPStatus.OK:
                    response_text = " ".join(response.text.strip().splitlines())[:200] if response.text else ""
                    logger.error(
                        f"SSE connection to '{self.remote_node.events_url}' failed, Code: {response.status_code}, Response: {response_text}",
                    )
                    return
                client = sseclient.SSEClient(response)
                for event in client.events():
                    if self.event_handler.is_set():
                        return
                    try:
                        data = json.loads(event.data)
                        logger.debug(f"SSE event received: {event.event}, data: {data}")
                        if self.remote_node.event_id not in data:
                            continue
                        if event.event == "remote_access_disconnect":
                            with self.app.app_context():
                                _clear_connection(self.remote_node)
                            return
                        if (
                            event.event == "remote_access_news_items_updated"
                            and self.remote_node.sync_news_items
                            and self.remote_node.osint_source_group_id is not None
                        ):
                            self._sync(news=True)
                        elif event.event == "remote_access_report_items_updated" and self.remote_node.sync_report_items:
                            self._sync(news=False)
                    except Exception as ex:
                        logger.exception("SSE processing failed: {ex}")
            except Exception as ex:
                logger.warning(f"Waiting for connection to SSE: {ex}. Attempt {attempt} of {retries}.")
            time.sleep(5)
            attempt += 1
        logger.error("Could not connect to SSE.")


def connect_to_events(remote_node: RemoteNode, api: RemoteApi | None = None) -> None:
    """Start an SSE listener using the peer's negotiated API instance.

    Args:
        remote_node: Remote node whose events should be consumed.
        api: Negotiated client to reuse, or None to construct one from the node settings.

    Returns:
        None. Any previous local listener is signaled to stop before its replacement starts.
    """
    disconnect_from_events(remote_node)
    event_handler = threading.Event()
    event_thread = EventThread(remote_node, event_handler, api)
    event_handlers[remote_node.id] = event_handler
    event_thread.start()


def disconnect_from_events(remote_node: RemoteNode) -> None:
    """Signal the remote node's current local listener to stop.

    Args:
        remote_node: Remote node whose listener should be stopped.

    Returns:
        None. The listener's stop event is also removed from the local registry.
    """
    event_handler = event_handlers.pop(remote_node.id, None)
    if event_handler is not None:
        event_handler.set()


def connect_to_node(node_id: int) -> tuple[dict, int]:
    """Connect to a remote node by its ID.

    Args:
        node_id: Database ID of the remote node to connect to.

    Returns:
        A tuple containing connection metadata or an error object and its HTTP status.
        Success starts an SSE listener using the negotiated protocol. Failure clears
        local connection state and does not propagate peer parsing errors to startup.
    """
    remote_node = RemoteNode.find(node_id)
    if remote_node is None:
        return {"error": "Remote node not found"}, HTTPStatus.NOT_FOUND
    try:
        api = RemoteApi(
            remote_node.remote_url,
            remote_node.api_key,
            legacy_timezone=getattr(remote_node, "legacy_timezone", None) or "UTC",
        )
    except (ValueError, TypeError, ZoneInfoNotFoundError):
        _clear_connection(remote_node)
        return {"error": "Invalid remote node legacy timezone"}, HTTPStatus.BAD_REQUEST
    try:
        access_info, status = api.connect()
        if status != HTTPStatus.OK:
            logger.error(f"Connect to remote node failed, Code: {status}. Response: {access_info}")
            if api.connection_accepted:
                api.disconnect()
            _clear_connection(remote_node)
            return access_info, status
        remote_node.connect(access_info, api_version=api.version)
        remote_node.api_version = api.version
        remote_clients[remote_node.id] = api
        logger.info(f"Connected to remote node '{remote_node.name}' using API v{api.version}")
        connect_to_events(remote_node, api)
        return access_info, status
    except Exception:
        logger.exception(f"Connect to remote node '{remote_node.name}' failed")
        db.session.rollback()
        api.disconnect()
        _clear_connection(remote_node)
        return {"error": "Remote connection response could not be applied"}, HTTPStatus.BAD_GATEWAY


def disconnect_from_node(node_id: int) -> None:
    """Disconnect a remote peer and clear its local connection state.

    Args:
        node_id: Database ID of the remote node to disconnect from.

    Returns:
        None. The retained protocol is used when available; unknown peers are handled
        through the client's disconnect-only discovery. Local cleanup runs even if the
        remote request or its settings fail.
    """
    remote_node = RemoteNode.find(node_id)
    if remote_node is None:
        return
    try:
        api = remote_clients.get(node_id) or RemoteApi(
            remote_node.remote_url,
            remote_node.api_key,
            legacy_timezone=getattr(remote_node, "legacy_timezone", None) or "UTC",
            version=getattr(remote_node, "api_version", None),
        )
        _response, status = api.disconnect()
        if not HTTPStatus.OK <= status < HTTPStatus.MULTIPLE_CHOICES:
            logger.error(f"Disconnect from remote node failed. Code: {status}")
    except (ValueError, TypeError, ZoneInfoNotFoundError):
        logger.exception(f"Invalid remote node connection settings for '{remote_node.name}'")
    finally:
        _clear_connection(remote_node)


def initialize(app: Flask) -> None:
    """Initialize remote event handling and connect enabled peers independently.

    Args:
        app: Flask application providing contexts for background synchronization.

    Returns:
        None. A failure connecting to one peer is logged and does not stop startup or
        prevent connection attempts for the remaining peers.
    """
    EventThread.app = app
    remote_nodes, _count = RemoteNode.get(None)
    for remote_node in remote_nodes:
        if remote_node.enabled:
            try:
                connect_to_node(remote_node.id)
            except Exception:
                logger.exception(f"Initialize remote node '{remote_node.name}' failed")
                _clear_connection(remote_node)
