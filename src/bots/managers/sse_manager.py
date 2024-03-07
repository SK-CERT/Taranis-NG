"""This module is responsible for managing the Server-Sent Events (SSE) from the Core."""
import os
import requests
import sseclient
import threading

from managers import bots_manager


api_key = os.getenv("API_KEY")
if not api_key:
    with open(os.getenv("API_KEY_FILE"), "r") as file:
        api_key = file.read()


def initialize():
    """Start the SSE thread to listen to the Core's events."""

    class SSEThread(threading.Thread):
        @classmethod
        def run(cls):
            try:
                response = requests.get(f"{os.getenv('TARANIS_NG_CORE_SSE')}?api_key={api_key}", stream=True)
                client = sseclient.SSEClient(response)
                for event in client.events():
                    bots_manager.process_event(event.event, event.data)

            except requests.exceptions.ConnectionError:
                print("Could not connect to Core SSE")

    sse_thread = SSEThread()
    sse_thread.start()
