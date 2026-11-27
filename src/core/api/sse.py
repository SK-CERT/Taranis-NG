"""SSE API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask_restful import Api

import json
import re
import socket
import time
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

SSE_HEARTBEAT_INTERVAL = 15
# The cookie names the session by the token's jti, which flask-jwt-extended makes a UUID.
SESSION_ID = re.compile(r"^[0-9a-fA-F-]{36}$")


def session_key(jwt_id: str) -> str:
    """The Redis key of an SSE session (see SseInitResource)."""
    return f"sse:{jwt_id}"


def session_open(key: str | None) -> bool:
    """Whether an SSE session still exists: logout deletes it, and it lapses with its token."""
    return key is None or bool(redis_client.exists(key))


class SseResource(Resource):
    """SSE API endpoint."""

    @stream_with_context
    def stream(self, session: str | None = None):  # noqa: ANN201
        """Stream data until the client leaves or, for a user's stream, the session ends.

        Args:
            session (str | None): The Redis key of the user's SSE session, checked at every
                heartbeat; None for a node's stream (API key).
        """
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
        last_heartbeat = time.monotonic()
        try:
            data = b""
            while True:
                try:
                    b = sock.recv(1)
                except TimeoutError:
                    yield ":\n\n"
                    b = None

                if b == b"":
                    break

                now = time.monotonic()
                if now - last_heartbeat >= SSE_HEARTBEAT_INTERVAL:
                    if not session_open(session):
                        logger.info("SSE: the session ended (logout or expiry); closing the stream")
                        break
                    yield "event: heartbeat\ndata: {}\n\n"
                    last_heartbeat = now

                if b is None:
                    continue

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
            # EventSource cannot send an Authorization header, so JWT info can only travel by cookie.
            # We don't want to send it as a URL parameter for security reasons.
            # JWT token is also big to fit in cookie, so we use JWT guid.
            jwt_id = request.cookies.get("jwt_id")
            api_key = request.headers.get("Authorization", "").replace("ApiKey ", "")

            auth_type = ""
            msg = ""
            session = None
            if jwt_id is not None:
                auth_type = "JWT session"
                stored = redis_client.get(session_key(jwt_id)) if SESSION_ID.fullmatch(jwt_id) else None
                try:
                    claims = json.loads(stored) if stored else None
                except (TypeError, ValueError):
                    claims = None
                if claims is None:
                    msg = "SSE: invalid or expired jwt_id."
                elif auth_manager.decode_user_from_session(claims) is None:
                    msg = "SSE: the session's token is no longer valid."
                else:
                    session = session_key(jwt_id)

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
                elif master_class is RemoteAccess and validated_object.enabled is not True:
                    msg = f"SSE: the Remote Access '{validated_object.name}' is disabled"

            else:
                msg = "SSE: missing authentication credentials."

            if msg:
                logger.warning(msg)
                return msg, HTTPStatus.FORBIDDEN

            logger.info(f"SSE: streaming response {request.remote_addr} ({auth_type})")
            return Response(self.stream(session), mimetype="text/event-stream")

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
            if jwt_id:
                # The token's claims, not the token: a bearer credential must not lie in Redis,
                # which every container on the compose network can reach. The session lapses
                # with the token; logout deletes it.
                # With the sign-in's session id and credential, so that logging out of the sign-in
                # and a password change end the session as they end the token.
                stored = (
                    "sub",
                    "jti",
                    "exp",
                    auth_manager.AUTH_GENERATION_CLAIM,
                    auth_manager.SESSION_ID_CLAIM,
                    auth_manager.CREDENTIAL_CLAIM,
                )
                claims = {key: jwt_data.get(key) for key in stored}
                lifetime = int(claims["exp"] - time.time()) if isinstance(claims["exp"], int | float) else SseInitResource.SSE_TOKEN_TTL
                lifetime = max(1, min(lifetime, SseInitResource.SSE_TOKEN_TTL))
                redis_client.set(session_key(jwt_id), json.dumps(claims), ex=lifetime)
                resp = make_response("", HTTPStatus.OK)
                resp.set_cookie(
                    "jwt_id",
                    jwt_id,
                    httponly=True,  # invisible to JS
                    secure=True,  # HTTPS only
                    samesite="None",  # cross-origin support
                    path="/sse",
                    max_age=lifetime,
                )
                logger.debug("SSE session stored in Redis, cookie set")
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
