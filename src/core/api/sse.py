"""SSE API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask_restful import Api

import json
import socket
from http import HTTPStatus

from flask import Response, request, stream_with_context
from flask_restful import Resource
from managers import auth_manager
from managers.log_manager import logger, sensitive_value
from model.bots_node import BotsNode
from model.remote import RemoteAccess


class SseResource(Resource):
    """SSE API endpoint."""

    @stream_with_context
    def stream(self):  # noqa: ANN201
        """Stream data."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(60)
        except Exception as ex:
            msg = f"SSE: Failed to create socket: {ex}"
            logger.exception(msg)
            raise RuntimeError(msg) from ex

        try:
            sock.connect(("localhost", 5001))
            sock.settimeout(1)
        except Exception as ex:
            msg = f"SSE: Failed to connect to server: {ex}"
            logger.exception(msg)
            sock.close()
            raise RuntimeError(msg) from ex

        buffer = ""
        try:
            data = b""
            while True:
                try:
                    b = sock.recv(1)
                except TimeoutError:
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
            logger.exception(f"SSE: Error during data reception or processing: {ex}")
        finally:
            sock.close()

    def get(self) -> tuple[str, HTTPStatus]:
        """Get Response."""
        try:
            jwt_token = request.args.get("jwt")
            api_key = request.args.get("api_key")

            auth_type = ""
            if jwt_token is not None:
                auth_type = "JWT"
                if auth_manager.decode_user_from_jwt(jwt_token) is None:
                    msg = "SSE: decoding user from jwt failed."
                    logger.warning(msg)
                    return msg, HTTPStatus.FORBIDDEN
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
                    api_key = sensitive_value(api_key)
                    msg = f"SSE: invalid {auth_type}: '{api_key}'"
                    logger.warning(msg)
                    return msg, HTTPStatus.FORBIDDEN

            else:
                msg = "SSE: missing authentication credentials."
                logger.warning(msg)
                return msg, HTTPStatus.FORBIDDEN

            logger.info(f"SSE: streaming response {request.remote_addr} ({auth_type})")
            return Response(self.stream(), mimetype="text/event-stream")

        except Exception as ex:
            msg = "SSE: Error in streaming response"
            logger.exception(msg, ex)
            return msg, HTTPStatus.INTERNAL_SERVER_ERROR


def initialize(api: Api) -> None:
    """Initialize API endpoints."""
    api.add_resource(SseResource, "/sse")
