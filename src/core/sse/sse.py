import socket
import json
from managers.log_manager import logger


class SSE:
    def __init__(self):
        pass

    def publish(self, data, event, channel=None):
        message = self.format_sse(data, event)
        logger.debug(f"SSE publish event: {event}, data: {data}")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 5000))
                sock.sendall(message.encode('utf-8'))
        except Exception as error:
            logger.exception(f"Error sending SSE publish data: {error}")

    @staticmethod
    def format_sse(data, event=None) -> str:
        return json.dumps({"event": event, "data": data})
