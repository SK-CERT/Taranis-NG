"""Keycloak authenticator module."""

from os import environ
import jwt
from flask_restful import request
from requests import post
from requests.auth import HTTPBasicAuth

from managers import log_manager, external_auth_manager
from managers.log_manager import logger
from auth.base_authenticator import BaseAuthenticator
from packaging import version


class KeycloakAuthenticator(BaseAuthenticator):
    """Keycloak authenticator class."""

    def authenticate(self, credentials):
        """Authenticate the user using Keycloak.

        Args:
            credentials: The user's credentials.
        """
        # check if code and session_state are present in keycloak callback
        if "code" not in request.args or "session_state" not in request.args:
            return {"error": "Missing code or session_state parameters"}, 400

        link = environ.get("TARANIS_NG_KEYCLOAK_INTERNAL_URL")
        # there's a change in API endpoints from version 17.0.0
        if version.parse(environ.get("KEYCLOAK_VERSION")) < version.parse("17.0.0"):
            link += "/auth"
        link += "/realms/" + environ.get("KEYCLOAK_REALM_NAME") + "/protocol/openid-connect/token"

        # verify code and get JWT token from keycloak
        response = post(
            url=link,
            data={
                "grant_type": "authorization_code",
                "code": request.args["code"],  # code from url
                "redirect_uri": "/".join(request.headers.get("Referer").split("/")[0:3]) + "/login",
                # original redirect_uri (host needs to match)
            },
            auth=HTTPBasicAuth(environ.get("TARANIS_NG_KEYCLOAK_CLIENT_ID"), external_auth_manager.get_keycloak_client_secret_key()),
            # do not forget credentials
            proxies={"http": None, "https": None},
            allow_redirects=False,
            verify=False,
        )

        data = None

        try:
            # get json data from response
            data = response.json()
            logger.debug(f"Keycloak authentication response: {data}")
        except Exception as ex:
            log_manager.store_auth_error_activity("Keycloak returned an unexpected response", ex)
            return {"error": "Internal server error"}, 500

        try:
            # decode token to get user data
            data = jwt.decode(data["access_token"], verify=False)
        except Exception as ex:
            log_manager.store_auth_error_activity("Keycloak returned invalid access_token", ex)
            return {"error": "Internal server error"}, 500

        # generate custom token
        return BaseAuthenticator.generate_jwt(data["preferred_username"])
