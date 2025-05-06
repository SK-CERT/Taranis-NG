"""SSE API endpoints."""

from flask_restful import Resource
import socket
import json
from flask import Response, stream_with_context
from flask import request
from managers import auth_manager
from model.bots_node import BotsNode
from model.remote import RemoteAccess
from managers.log_manager import logger


class TaranisSSE(Resource):
    """SSE API endpoint."""

    sse_logger = logger
    sse_logger.log_prefix = "SSE"

    @stream_with_context
    def stream(self):
        """Stream data."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(60)
        except Exception as ex:
            self.sse_logger.exception(f"Failed to create socket: {ex}")
            return

        try:
            sock.connect(("localhost", 5001))
            sock.settimeout(1)
        except Exception as ex:
            self.sse_logger.exception(f"Failed to connect to server: {ex}")
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
            self.sse_logger.exception(f"Error during data reception or processing: {ex}")
        finally:
            sock.close()

    def get(self):
        """Get Response."""
        try:
            jwt_token = request.args.get("jwt")
            api_key = request.args.get("api_key")

            auth_type = ""
            if jwt_token is not None:
                auth_type = "JWT"
                if auth_manager.decode_user_from_jwt(jwt_token) is None:
                    msg = "decoding user from jwt failed."
                    self.sse_logger.warning(msg)
                    return msg, 403
            elif api_key is not None:
                auth_type = "API key"
                api_type = request.args.get("channel")
                if api_type == "remote":
                    auth_type += ", Remote"
                    master_class = RemoteAccess
                else:
                    auth_type += ", Bots"
                    master_class = BotsNode
                validated_object = master_class.get_by_api_key(api_key)
                if not validated_object:
                    msg = f"invalid {auth_type}: '{api_key}'"
                    self.sse_logger.warning(msg)
                    return msg, 403

            else:
                msg = "missing authentication credentials."
                self.sse_logger.warning(msg)
                return msg, 403

            self.sse_logger.info(f"streaming response {request.remote_addr} ({auth_type})")
            return Response(self.stream(), mimetype="text/event-stream")
        except Exception as ex:
            msg = "Error in streaming response"
            self.sse_logger.exception(msg, ex)
            return msg, 500


def initialize(api):
    """Initialize API endpoints."""
    api.add_resource(TaranisSSE, "/sse")
