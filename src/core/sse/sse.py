"""Server-Sent Events (SSE) class for publishing events."""

import socket
import json
from managers.log_manager import logger


class SSE:
    """Server-Sent Events (SSE) class for publishing events."""

    log_prefix = "SSE"

    def publish(self, data, event, channel=None):
        """Publish data to the SSE channel.

        Args:
            data (dict): The data to be published.
            event (str): The event name.
            channel (str, optional): The channel name. Defaults to None.
        """
        message = self.format_sse(data, event)
        logger.debug(f"publish event: {event}, data: {data}")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(("localhost", 5000))
                sock.sendall(message.encode("utf-8"))
        except Exception as error:
            logger.exception(f"Error sending SSE publish data: {error}")

    @staticmethod
    def format_sse(data, event=None) -> str:
        """Format the data for SSE.

        Args:
            data (dict): The data to be formatted.
            event (str, optional): The event name. Defaults to None.
        Returns:
            str: The formatted SSE message.
        """
        return json.dumps({"event": event, "data": data})
