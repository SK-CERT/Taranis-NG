"""Remote manager, Server-Sent Events (SSE) handling."""

import json
import threading
import time

import requests
import sseclient
from managers import sse_manager
from managers.log_manager import logger
from model.news_item import NewsItemAggregate
from model.remote import RemoteNode
from model.report_item import ReportItem
from remote.remote_api import RemoteApi

event_handlers = {}


class EventThread(threading.Thread):
    """Thread to handle Server-Sent Events (SSE) from a remote node."""

    app = None

    def __init__(self, remote_node, event_handler):
        """Initialize the EventThread.

        Args:
            remote_node (RemoteNode): The remote node to connect to.
            event_handler (threading.Event): The event handler to manage thread events.
        """
        threading.Thread.__init__(self)
        self.remote_node = remote_node
        self.event_handler = event_handler

    def run(self):
        """Run the thread to listen for SSE events and handle them accordingly."""
        attempt = 1
        retries = 3
        while not self.event_handler.is_set() and attempt <= retries:
            try:
                response = requests.get(self.remote_node.events_url + "?channel=remote&api_key=" + self.remote_node.api_key, stream=True)
                if response.status_code != 200:
                    response_text = ""
                    if response is not None and response.text:
                        response_text = " ".join(response.text.strip().splitlines())[:200]
                    logger.error(
                        f"SSE connection to '{self.remote_node.events_url}' failed, Code: {response.status_code}, Response: {response_text}",
                    )
                    return
                client = sseclient.SSEClient(response)
                for event in client.events():
                    try:
                        data = json.loads(event.data)
                        logger.debug(f"SSE event received: {event.event}, data: {data}")
                        if event.event == "remote_access_disconnect":
                            if self.remote_node.event_id in data:
                                with EventThread.app.app_context():
                                    self.remote_node.disconnect()
                                return

                        elif event.event == "remote_access_news_items_updated":
                            if self.remote_node.sync_news_items and self.remote_node.osint_source_group_id is not None:
                                if self.remote_node.event_id in data:
                                    data, status_code = RemoteApi(self.remote_node.remote_url, self.remote_node.api_key).get_news_items()
                                    if status_code == 200:
                                        with EventThread.app.app_context():
                                            # print("NEWS", data["news_items"], flush=True)
                                            NewsItemAggregate.add_remote_news_items(
                                                data["news_items"],
                                                self.remote_node,
                                                self.remote_node.osint_source_group_id,
                                            )

                                        RemoteApi(self.remote_node.remote_url, self.remote_node.api_key).confirm_news_items_sync(
                                            {"last_sync_time": data["last_sync_time"]},
                                        )

                                        with EventThread.app.app_context():
                                            sse_manager.sse_manager.news_items_updated()
                                    else:
                                        logger.error(f"Get remote news items failed. Code: {status_code}")

                        elif event.event == "remote_access_report_items_updated":
                            if self.remote_node.sync_report_items:
                                if self.remote_node.event_id in data:
                                    data, status_code = RemoteApi(self.remote_node.remote_url, self.remote_node.api_key).get_report_items()
                                    if status_code == 200:
                                        with EventThread.app.app_context():
                                            ReportItem.add_remote_report_items(data["report_items"], self.remote_node.name)

                                        RemoteApi(self.remote_node.remote_url, self.remote_node.api_key).confirm_report_items_sync(
                                            {"last_sync_time": data["last_sync_time"]},
                                        )

                                        with EventThread.app.app_context():
                                            sse_manager.sse_manager.report_items_updated()
                                    else:
                                        logger.error(f"Get remote report items failed. Code: {status_code}")

                    except Exception as ex:
                        logger.exception(f"SSE processing failed: {ex}")

            except Exception as ex:
                logger.warning(f"Waiting for connection to SSE: {ex}. Attempt {attempt} of {retries}.")

            time.sleep(5)
            attempt += 1

        logger.error("Could not connect to SSE.")


def connect_to_events(remote_node):
    """Connect to SSE events for a given remote node.

    Args:
        remote_node (RemoteNode): The remote node to connect to.
    """
    event_handler = threading.Event()
    event_thread = EventThread(remote_node, event_handler)
    event_handlers[remote_node.id] = event_handler
    event_thread.start()


def disconnect_from_events(remote_node):
    """Disconnect from SSE events for a given remote node.

    Args:
        remote_node (RemoteNode): The remote node to disconnect from.
    """
    if remote_node.id in event_handlers:
        event_handlers[remote_node.id].set()


def connect_to_node(node_id):
    """Connect to a remote node by its ID.

    Args:
        node_id (int): The ID of the remote node to connect to.

    Returns:
        tuple: A tuple containing the access information and status code.
    """
    remote_node = RemoteNode.find(node_id)
    access_info, status_code = RemoteApi(remote_node.remote_url, remote_node.api_key).connect()
    if status_code == 200:
        remote_node.connect(access_info)
        connect_to_events(remote_node)
    else:
        logger.error(f"Connect to remote node failed, Code: {status_code}. Response: {access_info}")
        remote_node.disconnect()
        disconnect_from_events(remote_node)

    return access_info, status_code


def disconnect_from_node(node_id):
    """Disconnect from a remote node by its ID.

    Args:
        node_id (int): The ID of the remote node to disconnect from.
    """
    remote_node = RemoteNode.find(node_id)
    RemoteApi(remote_node.remote_url, remote_node.api_key).disconnect()


def initialize(app):
    """Initialize the remote manager with the given application context.

    Args:
        app: The application context to use.
    """
    EventThread.app = app
    remote_nodes, count = RemoteNode.get(None)
    for remote_node in remote_nodes:
        if remote_node.enabled:
            connect_to_node(remote_node.id)
