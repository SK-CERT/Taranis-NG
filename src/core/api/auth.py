"""This module provides authentication resources for the Taranis-NG application.

Classes:
    Login(Resource): A resource for handling user login.
    Refresh(Resource): A resource for handling token refresh requests.
    Logout(Resource): A resource for handling user logout requests.

Functions:
    initialize(api): Initialize the authentication routes for the given API.

Usage:
    - Login: Handles GET and POST requests for user authentication.
    - Refresh: Handles GET requests to refresh authentication tokens.
    - Logout: Handles GET requests for logging out users.

Dependencies:
    - flask: For creating redirect responses and handling requests.
    - flask_restful: For creating RESTful resources.
    - config: For accessing application configuration.
    - managers.auth_manager: For handling authentication logic.
"""

import urllib

from config import Config
from flask import make_response, redirect
from flask_restful import Resource, ResponseBase, reqparse, request
from managers import auth_manager
from managers.auth_manager import jwt_required, no_auth


class Login(Resource):
    """A resource for handling user login."""

    @no_auth
    def get(self):
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

        if not isinstance(response, ResponseBase):
            if "gotoUrl" in request.args and "access_token" in response:
                redirect_response = make_response(redirect(request.args["gotoUrl"]))
                redirect_response.set_cookie("jwt", response["access_token"])
                return redirect_response

        return response

    def post(self):
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

        return auth_manager.authenticate(credentials)


class Refresh(Resource):
    """A resource for handling token refresh requests."""

    @jwt_required
    def get(self):
        """Handle GET request to refresh the authentication token.

        This method retrieves the current user from the JWT (JSON Web Token) and
        refreshes their authentication token using the auth_manager.

        Returns:
            dict: A dictionary containing the refreshed authentication token.
        """
        return auth_manager.refresh(auth_manager.get_user_from_jwt())


class Logout(Resource):
    """A resource for handling user logout requests."""

    @no_auth
    def get(self):
        """Handle the GET request for logging out a user.

        This method checks for a JWT token in the request arguments and attempts to decode it.
        If the token is valid, it proceeds to log out the user using the auth_manager.
        If the logout is successful and a "gotoUrl" is provided in the request arguments,
        it redirects the user to the specified URL. If an OpenID logout URL is configured,
        it replaces "GOTO_URL" in the OpenID logout URL with the encoded "gotoUrl" and redirects to it.

        Returns:
            ResponseBase: The response from the auth_manager.logout method.
            Redirect: A redirect response to the specified "gotoUrl" or OpenID logout URL if applicable.
        """
        token = None
        if "jwt" in request.args:
            if auth_manager.decode_user_from_jwt(request.args["jwt"]) is not None:
                token = request.args["jwt"]

        response = auth_manager.logout(token)

        if not isinstance(response, ResponseBase):
            if "gotoUrl" in request.args:
                if Config.OPENID_LOGOUT_URL:
                    url = Config.OPENID_LOGOUT_URL.replace("GOTO_URL", urllib.parse.quote(request.args["gotoUrl"]))
                    return redirect(url)
                return redirect(request.args["gotoUrl"])

        return response


def initialize(api):
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
