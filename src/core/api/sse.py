"""SSE API endpoints."""

from flask_restful import Resource
import socket
import json
from flask import Response, stream_with_context
from flask import request
from managers import auth_manager, bots_manager
from managers.log_manager import logger


class TaranisSSE(Resource):
    """SSE API endpoint."""

    @stream_with_context
    def stream(self):
        """Stream data."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(60)
        except Exception as ex:
            logger.exception(f"Failed to create socket: {ex}")
            return

        try:
            sock.connect(("localhost", 5001))
            sock.settimeout(1)
        except Exception as ex:
            logger.exception(f"Failed to connect to server: {ex}")
            sock.close()
            return

        buffer = ""
        try:
            data = b""
            while True:
                try:
                    b = sock.recv(1)
                except socket.timeout:
                    yield ":\n\n"
                    continue

                if not b:
                    break
                data += b
                try:
                    char = data.decode("utf-8")
                    data = b""
                except UnicodeDecodeError:
                    yield ":\n\n"
                    continue

                buffer += char

                if char == "}":
                    try:
                        json_data = json.loads(buffer)
                    except json.JSONDecodeError:
                        continue

                    yield f"event: {json_data['event']}\ndata: {json.dumps(json_data['data'])}\n\n"
                    buffer = ""
        except Exception as ex:
            logger.exception(f"Error during data reception or processing: {ex}")
        finally:
            sock.close()

    def get(self):
        """Get Response."""
        try:
            jwt_token = request.args.get("jwt")
            api_key = request.args.get("api_key")

            if jwt_token is not None:
                if auth_manager.decode_user_from_jwt(jwt_token) is None:
                    msg = "SSE: decoding user from jwt failed."
                    logger.warning(msg)
                    return msg, 403
            elif api_key is not None:
                if bots_manager.verify_api_key(api_key) is False:
                    msg = "SSE: invalid API key."
                    logger.warning(msg)
                    return msg, 403
            else:
                msg = "SSE: missing authentication credentials."
                logger.warning(msg)
                return msg, 403

            return Response(self.stream(), mimetype="text/event-stream")
        except Exception as ex:
            msg = "SSE: Error in streaming response"
            logger.exception(msg, ex)
            return msg + " " + str(ex), 500


def initialize(api):
    """Initialize API endpoints."""
    api.add_resource(TaranisSSE, "/sse")
