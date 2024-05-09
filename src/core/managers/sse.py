import socket
import json


class SSE:
    def __init__(self):
        pass

    def publish(self, data, event, channel=None):
        message = self.format_sse(data, event)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 5000))
                sock.sendall(message.encode('utf-8'))
        except Exception as e:
            print(f"Error sending data: {e}")

    @staticmethod
    def format_sse(data, event=None) -> str:
        return json.dumps({"event": event, "data": data})
