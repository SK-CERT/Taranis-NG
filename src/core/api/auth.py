"""This module provides authentication resources for the Taranis-NG application."""

import secrets
import urllib
from http import HTTPStatus

from config import Config
from flask import Response, make_response, redirect
from flask_restful import Api, Resource, ResponseBase, reqparse, request
from managers import auth_manager
from managers.auth_manager import jwt_required, no_auth
from managers.cache_manager import redis_client
from managers.log_manager import logger


class Login(Resource):
    """A resource for handling user login."""

    SSE_TOKEN_TTL = 86400  # 1 day

    @staticmethod
    def create_sse_token(jwt_token: str) -> str:
        """Generate a secure random token for SSE authentication and store it in Redis with the associated JWT token.

        Args: jwt_token (str): The JWT to associate with the generated SSE token.

        Returns: str: The generated SSE reference token.
        """
        # We have problem store JWT token as cookie because of the size limit, so we store it in Redis and
        # set a small size cookie with a reference token. Not always we can use Authorization header,
        # for example in SSE authentication - it's not possible do it with vue-sse component. If we use in future
        # some custom SSE client, we can switch to header authentication and remove this workaround.
        token = secrets.token_urlsafe(32)
        redis_client.setex(f"sse:{token}", Login.SSE_TOKEN_TTL, jwt_token)
        return token

    @no_auth
    def get(self) -> Response:
        """Handle GET requests for authentication.

        This method attempts to authenticate a user using the `auth_manager`.
        If the authentication response is not an instance of `ResponseBase` and
        contains an `access_token`, it will redirect the user to the URL specified
        in the `gotoUrl` request argument and set a cookie with the JWT.

        Returns:
            response: A redirect response with a JWT cookie if authentication is successful,
                      otherwise the original response from `auth_manager.authenticate`.
        """
        response = auth_manager.authenticate(None)
        if not isinstance(response, ResponseBase) and "gotoUrl" in request.args and "access_token" in response:
            redirect_response = make_response(redirect(request.args["gotoUrl"]))
            redirect_response.set_cookie("jwt", response["access_token"])
            return redirect_response

        return response

    def post(self) -> Response:
        """Handle POST requests for authentication.

        This method parses the required credentials from the JSON payload of the request,
        and then attempts to authenticate the user using these credentials.

        Returns:
            Response: The result of the authentication attempt.
        """
        parser = reqparse.RequestParser()
        for credential in auth_manager.get_required_credentials():
            parser.add_argument(credential, location="json")
        credentials = parser.parse_args()

        auth_response = auth_manager.authenticate(credentials)

        # if auth_response has access_token, set cookie
        if isinstance(auth_response, tuple):
            body, status = auth_response
        else:
            body, status = auth_response, HTTPStatus.OK

        access_token = None
        if not isinstance(body, ResponseBase):
            access_token = body.get("access_token")
        if access_token:
            sse_token = self.create_sse_token(access_token)
            resp = make_response(body, status)  # send JSON back too
            resp.set_cookie(
                "sse_token",
                sse_token,
                httponly=True,  # invisible to JS
                secure=True,  # HTTPS only
                samesite="None",  # cross-origin support
                path="/sse",
                max_age=Login.SSE_TOKEN_TTL,
            )
            logger.debug("SSE: Token created, cookie set")
            return resp

        return auth_response


class Refresh(Resource):
    """A resource for handling token refresh requests."""

    @jwt_required
    def get(self) -> tuple[dict, HTTPStatus]:
        """Handle GET request to refresh the authentication token.

        This method retrieves the current user from the JWT (JSON Web Token) and
        refreshes their authentication token using the auth_manager.

        Returns:
            dict: A dictionary containing the refreshed authentication token.
        """
        return auth_manager.refresh(auth_manager.get_user_from_jwt())


class Logout(Resource):
    """A resource for handling user logout requests."""

    @jwt_required
    def post(self) -> Response:
        """Handle the POST request for logging out a user.

        If a "gotoUrl" is provided in the request arguments,
        it redirects the user to the specified URL. If an OpenID logout URL is configured,
        it replaces "GOTO_URL" in the OpenID logout URL with the encoded "gotoUrl" and redirects to it.

        Returns:
            ResponseBase: The response from the auth_manager.logout method.
            Redirect: A redirect response to the specified "gotoUrl" or OpenID logout URL if applicable.
        """
        try:
            token = request.headers.get("Authorization", "").replace("Bearer ", "")

            # there is problem receive sse_token 1) path: /sse, 2) we don't want send cookies all the time,
            # 3) httponly flag (we can't read it from JS and put it to body). We know JWT so delete it by value
            for key in redis_client.scan_iter("sse:*"):
                if redis_client.get(key).decode("utf-8") == token:
                    redis_client.delete(key)
                    logger.debug("SSE: Token deleted")
                    break

            response = auth_manager.logout(token)

            if not isinstance(response, ResponseBase) and "gotoUrl" in request.args:
                url = (
                    Config.OPENID_LOGOUT_URL.replace("GOTO_URL", urllib.parse.quote(request.args["gotoUrl"]))
                    if Config.OPENID_LOGOUT_URL
                    else request.args["gotoUrl"]
                )
                resp = redirect(url)
            else:
                resp = make_response({}, HTTPStatus.OK) if response is None else response

            # Delete cookie if resp is a Response object
            if hasattr(resp, "delete_cookie"):
                resp.delete_cookie("sse_token", path="/sse")
                logger.debug("SSE: Cookie deleted")

            return resp

        except Exception as ex:
            msg = "Logout failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, HTTPStatus.INTERNAL_SERVER_ERROR


def initialize(api: Api) -> None:
    """Initialize the authentication routes for the given API.

    This function adds the following resources to the API:
    - Login: Endpoint for user login at "/api/v1/auth/login"
    - Refresh: Endpoint for refreshing authentication tokens at "/api/v1/auth/refresh"
    - Logout: Endpoint for user logout at "/api/v1/auth/logout"
    Args:
        api (flask_restful.Api): The Flask-RESTful API object to which the resources will be added.
    """
    api.add_resource(Login, "/api/v1/auth/login")
    api.add_resource(Refresh, "/api/v1/auth/refresh")
    api.add_resource(Logout, "/api/v1/auth/logout")
