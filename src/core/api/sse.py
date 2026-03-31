"""SSE API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask_restful import Api

import json
import socket
from http import HTTPStatus

from flask import Response, make_response, request, stream_with_context
from flask_jwt_extended import get_jwt
from flask_restful import Resource
from managers import auth_manager
from managers.auth_manager import jwt_token_required
from managers.cache_manager import redis_client
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
            # SSE-VUE component can transfer JWT info only by cookie. We don't want send it as url parameter due of security reasons
            # JWT token is also big to fit in cookie, so we use JWT guid.
            jwt_id = request.cookies.get("jwt_id")
            api_key = request.headers.get("Authorization", "").replace("ApiKey ", "")

            auth_type = ""
            msg = ""
            if jwt_id is not None:
                auth_type = "JWT token"
                jwt_token = redis_client.get(f"jwt:{jwt_id}")
                if jwt_token:
                    if auth_manager.decode_user_from_jwt(jwt_token) is None:
                        msg = "SSE: decoding user from jwt failed."
                else:
                    msg = "SSE: invalid or expired jwt_id."

            elif api_key != "":
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

            else:
                msg = "SSE: missing authentication credentials."

            if msg:
                logger.warning(msg)
                return msg, HTTPStatus.FORBIDDEN

            logger.info(f"SSE: streaming response {request.remote_addr} ({auth_type})")
            return Response(self.stream(), mimetype="text/event-stream")

        except Exception as ex:
            msg = "SSE: Error in streaming response"
            logger.exception(f"{msg}: {ex}")
            return msg, HTTPStatus.INTERNAL_SERVER_ERROR


class SseInitResource(Resource):
    """SSE API init endpoint."""

    SSE_TOKEN_TTL = 86400  # 1 day

    @jwt_token_required
    def post(self) -> Response:
        """Post Response."""
        try:
            jwt_data = get_jwt()
            jwt_id = jwt_data.get("jti")
            jwt_token = request.headers.get("Authorization", "").replace("Bearer ", "")
            if jwt_token:
                redis_client.setex(f"jwt:{jwt_id}", SseInitResource.SSE_TOKEN_TTL, jwt_token)
                resp = make_response("", HTTPStatus.OK)
                resp.set_cookie(
                    "jwt_id",
                    jwt_id,
                    httponly=True,  # invisible to JS
                    secure=True,  # HTTPS only
                    samesite="None",  # cross-origin support
                    path="/sse",
                    max_age=SseInitResource.SSE_TOKEN_TTL,
                )
                logger.debug("JWT token created in Redis, cookie set")
                return resp

            msg = "SSE: missing Authorization"
            logger.error(msg)
            return make_response(msg, HTTPStatus.UNAUTHORIZED)

        except Exception as ex:
            msg = "SSE: Init failed"
            logger.exception(f"{msg}: {ex}")
            return make_response(msg, HTTPStatus.INTERNAL_SERVER_ERROR)


def initialize(api: Api) -> None:
    """Initialize API endpoints."""
    api.add_resource(SseResource, "/sse")
    api.add_resource(SseInitResource, "/api/v1/sse-init")
