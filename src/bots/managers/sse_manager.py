"""This module is responsible for managing the Server-Sent Events (SSE) from the Core."""

import os
import threading
import time
from http import HTTPStatus

import requests
import sseclient
from config import Config
from managers import bots_manager

from shared.log_manager import logger


def initialize() -> None:
    """Start the SSE thread to listen to the Core's events."""

    class SSEThread(threading.Thread):
        @classmethod
        def run(cls) -> None:
            logger.debug("SSE: Awaiting initialization of CORE (timeout: 20s)")
            time.sleep(20)  # wait for the CORE
            url = os.getenv("TARANIS_NG_CORE_SSE")
            while True:  # Keep the thread running
                try:
                    logger.info(f"SSE: Connecting to Core: {url}")
                    response = requests.get(f"{url}?api_key={Config.API_KEY}", stream=True, timeout=10)
                    if response.status_code != HTTPStatus.OK:
                        response_text = ""
                        if response is not None and response.text:
                            response_text = " ".join(response.text.encode().decode("unicode_escape").strip().splitlines())[:200]
                        logger.error(f"SSE: Failed to connect to Core SSE, Code: {response.status_code}, response: {response_text}")
                        logger.debug("SSE: Retrying connection in 30 seconds...")
                        threading.Event().wait(30)
                        continue
                    client = sseclient.SSEClient(response)
                    for event in client.events():
                        logger.debug(f"SSE: Process event: {event.event}, data: {event.data}")
                        bots_manager.process_event(event.event, event.data)

                except requests.exceptions.ConnectionError as ex:
                    logger.exception(f"SSE: Could not connect to Core SSE: {ex}")
                    logger.debug("SSE: Retrying connection in 30 seconds...")
                    threading.Event().wait(30)

                except Exception as ex:
                    logger.exception(f"SSE: Unexpected error in thread: {ex}")
                    logger.debug("SSE: Retrying connection in 30 seconds...")
                    threading.Event().wait(30)

    sse_thread = SSEThread()
    sse_thread.start()
