"""This module is responsible for managing the Server-Sent Events (SSE) from the Core."""

import os
import requests
import sseclient
import threading
from config import Config
from managers import bots_manager
from shared.log_manager import logger


def initialize():
    """Start the SSE thread to listen to the Core's events."""

    class SSEThread(threading.Thread):

        @classmethod
        def run(cls):
            url = os.getenv("TARANIS_NG_CORE_SSE")
            while True:  # Keep the thread running
                try:
                    logger.info(f"SSE: Connecting to Core: {url}")
                    response = requests.get(f"{url}?api_key={Config.API_KEY}", stream=True)
                    client = sseclient.SSEClient(response)
                    for event in client.events():
                        logger.debug(f"SSE: Process event: {event.event}, data: {event.data}")
                        bots_manager.process_event(event.event, event.data)

                except requests.exceptions.ConnectionError as ex:
                    logger.exception(f"SSE: Could not connect to Core SSE: {ex}")
                    logger.info("SSE: Retrying connection in 30 seconds...")
                    threading.Event().wait(30)

                except Exception as ex:
                    logger.exception(f"SSE: Unexpected error in thread: {ex}")
                    logger.info("SSE: Retrying connection in 30 seconds...")
                    threading.Event().wait(30)

    sse_thread = SSEThread()
    sse_thread.start()
