"""This module provides authentication resources for the Taranis-NG application."""

import urllib
import uuid
from http import HTTPStatus

from config import Config
from flask import Response, make_response, redirect
from flask_jwt_extended import get_jwt
from flask_restful import Api, Resource, ResponseBase, reqparse, request
from managers import auth_manager
from managers.auth_manager import jwt_token_required, no_auth
from managers.cache_manager import redis_client
from managers.log_manager import logger


class Login(Resource):
    """A resource for handling user login."""

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

        return auth_manager.authenticate(credentials)


class Refresh(Resource):
    """A resource for handling token refresh requests."""

    @jwt_token_required
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

    @jwt_token_required
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
            jwt_data = get_jwt()
            jwt_id = jwt_data.get("jti")
            if jwt_id:
                deleted_count = redis_client.delete(f"jwt:{jwt_id}")
                if deleted_count:
                    logger.debug("JWT token deleted from Redis")
                else:
                    logger.warning(f"JWT token {jwt_id} not found in Redis")

            response = auth_manager.logout(jwt_id)

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
                resp.delete_cookie("jwt_id", path="/sse")
                logger.debug("JWT cookie deleted")

            return resp

        except Exception as ex:
            msg = "Logout failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, HTTPStatus.INTERNAL_SERVER_ERROR


class LoginMethods(Resource):
    """A public resource listing the enabled login methods for the login page."""

    @no_auth
    def get(self) -> tuple[dict, HTTPStatus]:
        """List enabled auth providers (id, name, kind only - no config or secrets).

        Returns:
            dict: The available login methods.
        """
        return auth_manager.get_login_methods(), HTTPStatus.OK


def _oauth_redirect_uri(provider_id: int, config: dict) -> str:
    """Build the OAuth callback URL for a provider.

    Uses the configured override when present, otherwise derives it from the
    request (requires correct X-Forwarded-* handling behind a reverse proxy).

    Args:
        provider_id (int): The provider ID.
        config (dict): The provider configuration.

    Returns:
        str: The redirect URI registered at the IdP.
    """
    override = (config or {}).get("redirect_uri_override")
    if override:
        return override
    return f"{request.scheme}://{request.host}/api/v1/auth/oauth/{provider_id}/callback"


def _login_error_redirect(goto_url: str, code: str) -> Response:
    """Redirect back to the GUI login page with a login_error query parameter.

    Args:
        goto_url (str): The GUI URL to return to.
        code (str): The machine-readable error code.

    Returns:
        Response: The redirect response.
    """
    separator = "&" if "?" in goto_url else "?"
    return redirect(f"{goto_url}{separator}login_error={urllib.parse.quote(code.lower())}")


def _finish_redirect_login(goto_url: str, response: dict) -> Response:
    """Hand the login verdict to the GUI at the end of a redirect (OIDC/OAuth2/SAML) flow.

    The browser is mid-redirect, so there is no JSON body to answer with: the verdict
    travels in cookies the GUI consumes on arrival. Either the JWT, or - when the user
    still owes a second factor - the short-lived scoped token that lets the login page
    finish the MFA step it would have run for a form login.

    Args:
        goto_url (str): The GUI URL to return to.
        response (dict): The login response from the auth manager.

    Returns:
        Response: The redirect response.
    """
    cookies: dict[str, str] = {}
    code = response.get("code", "auth_failed")

    if "access_token" in response:
        cookies["jwt"] = response["access_token"]
    elif code == "MFA_REQUIRED" and response.get("mfa_token"):
        cookies["mfa_token"] = response["mfa_token"]
        # percent-encoded: a bare comma makes werkzeug quote the whole value
        cookies["mfa_methods"] = urllib.parse.quote(",".join(response.get("methods") or ["totp"]))
    elif code == "MFA_ENROLLMENT_REQUIRED" and response.get("enroll_token"):
        cookies["mfa_enroll"] = response["enroll_token"]
        cookies["mfa_methods"] = urllib.parse.quote(",".join(response.get("methods") or ["totp"]))
    else:
        return _login_error_redirect(goto_url, code)

    redirect_response = make_response(redirect(goto_url))
    for name, value in cookies.items():
        redirect_response.set_cookie(name, value)
    return redirect_response


class OAuthLoginRedirect(Resource):
    """Start the authorization-code flow for a redirect-based (OIDC/OAuth2) provider."""

    @no_auth
    def get(self, provider_id: int) -> Response:
        """Redirect the browser to the identity provider's authorization endpoint.

        Args:
            provider_id (int): The auth provider to log in with.

        Returns:
            Response: A redirect to the IdP, or an error for unknown providers.
        """
        authenticator = auth_manager.get_oauth_authenticator(provider_id)
        if not authenticator:
            return {"error": "Unknown login method"}, HTTPStatus.NOT_FOUND
        goto_url = request.args.get("gotoUrl", "/")
        nonce = uuid.uuid4().hex
        # When PKCE is enabled for this provider, generate a fresh
        # code_verifier per login attempt and carry it inside the signed state
        # JWT so it survives the browser round-trip to the IdP and back.
        code_verifier = authenticator.generate_code_verifier() if authenticator.uses_pkce() else None
        state = auth_manager.make_scoped_token(
            f"provider:{provider_id}",
            "oauth_state",
            expires_minutes=auth_manager.OAUTH_STATE_MINUTES,
            pid=provider_id,
            gotoUrl=goto_url,
            nonce=nonce,
            code_verifier=code_verifier,
            pkce_method=authenticator.pkce_method(),
        )
        redirect_uri = _oauth_redirect_uri(provider_id, authenticator.config)
        try:
            return redirect(authenticator.get_authorization_url(redirect_uri, state, nonce, code_verifier=code_verifier))
        except Exception as ex:
            logger.exception(f"Building the authorization URL failed: {ex}")
            return _login_error_redirect(goto_url, "auth_failed")


class OAuthCallback(Resource):
    """Handle the IdP redirect back: exchange the code and hand the JWT to the GUI."""

    @no_auth
    def get(self, provider_id: int) -> Response:
        """Finish the authorization-code flow and redirect to the GUI.

        The verdict reaches the GUI in cookies: the JWT on success, or the scoped
        MFA token when the user still owes a second factor; on failure the GUI
        login page receives a login_error query parameter.

        Args:
            provider_id (int): The auth provider the flow was started with.

        Returns:
            Response: A redirect response.
        """
        state = auth_manager.decode_scoped_token(request.args.get("state", ""), "oauth_state")
        if not state or state.get("pid") != provider_id:
            return {"error": "Invalid state"}, HTTPStatus.UNAUTHORIZED
        goto_url = state.get("gotoUrl") or "/"

        authenticator = auth_manager.get_oauth_authenticator(provider_id)
        if not authenticator:
            return _login_error_redirect(goto_url, "auth_failed")

        code = request.args.get("code")
        if not code:
            return _login_error_redirect(goto_url, "auth_failed")

        redirect_uri = _oauth_redirect_uri(provider_id, authenticator.config)
        identity = authenticator.handle_callback(redirect_uri, code, state.get("nonce"), code_verifier=state.get("code_verifier"))
        if not identity:
            return _login_error_redirect(goto_url, "auth_failed")

        response, _status = auth_manager.provision_and_issue_jwt(authenticator.provider, identity)
        return _finish_redirect_login(goto_url, response)


def _saml_acs_url(provider_id: int, config: dict) -> str:
    """Build the Assertion Consumer Service URL for a SAML provider.

    Uses the configured override when present, otherwise derives it from the
    request (requires correct X-Forwarded-* handling behind a reverse proxy).

    Args:
        provider_id (int): The provider ID.
        config (dict): The provider configuration.

    Returns:
        str: The ACS URL registered at the identity provider.
    """
    override = (config or {}).get("acs_url_override")
    if override:
        return override
    return f"{request.scheme}://{request.host}/api/v1/auth/saml/{provider_id}/acs"


class SamlLoginRedirect(Resource):
    """Start the SAML web browser SSO flow for a saml-kind provider."""

    @no_auth
    def get(self, provider_id: int) -> Response:
        """Redirect the browser to the identity provider's SSO endpoint.

        Args:
            provider_id (int): The auth provider to log in with.

        Returns:
            Response: A redirect to the IdP, or an error for unknown providers.
        """
        authenticator = auth_manager.get_saml_authenticator(provider_id)
        if not authenticator:
            return {"error": "Unknown login method"}, HTTPStatus.NOT_FOUND
        goto_url = request.args.get("gotoUrl", "/")
        # xsd:ID values must not start with a digit; the AuthnRequest ID is
        # verified against the response's InResponseTo at the ACS.
        request_id = f"_{uuid.uuid4().hex}"
        relay_state = auth_manager.make_scoped_token(
            f"provider:{provider_id}",
            "saml_state",
            expires_minutes=auth_manager.OAUTH_STATE_MINUTES,
            pid=provider_id,
            gotoUrl=goto_url,
            request_id=request_id,
        )
        acs_url = _saml_acs_url(provider_id, authenticator.config)
        try:
            return redirect(authenticator.get_login_redirect_url(acs_url, relay_state, request_id))
        except Exception as ex:
            logger.exception(f"Building the SAML request failed: {ex}")
            return _login_error_redirect(goto_url, "auth_failed")


class SamlMetadata(Resource):
    """Publish the SP metadata an identity provider needs to register this service."""

    @no_auth
    def get(self, provider_id: int) -> Response:
        """Serve the SAML SP metadata document.

        Args:
            provider_id (int): The auth provider to describe.

        Returns:
            Response: The metadata XML, or an error for unknown providers.
        """
        authenticator = auth_manager.get_saml_authenticator(provider_id)
        if not authenticator:
            return {"error": "Unknown login method"}, HTTPStatus.NOT_FOUND
        acs_url = _saml_acs_url(provider_id, authenticator.config)
        metadata = authenticator.get_metadata_xml(acs_url)
        return Response(metadata, mimetype="application/samlmetadata+xml")


class SamlAcs(Resource):
    """Assertion Consumer Service: validate the posted SAMLResponse and log in."""

    @no_auth
    def post(self, provider_id: int) -> Response:
        """Finish the SAML flow and redirect to the GUI.

        The verdict reaches the GUI in cookies: the JWT on success, or the scoped
        MFA token when the user still owes a second factor; on failure the GUI
        login page receives a login_error query parameter.

        Args:
            provider_id (int): The auth provider the flow was started with.

        Returns:
            Response: A redirect response.
        """
        relay_state = auth_manager.decode_scoped_token(request.form.get("RelayState", ""), "saml_state")
        if not relay_state or relay_state.get("pid") != provider_id:
            return {"error": "Invalid state"}, HTTPStatus.UNAUTHORIZED
        goto_url = relay_state.get("gotoUrl") or "/"

        authenticator = auth_manager.get_saml_authenticator(provider_id)
        if not authenticator:
            return _login_error_redirect(goto_url, "auth_failed")

        saml_response = request.form.get("SAMLResponse")
        if not saml_response:
            return _login_error_redirect(goto_url, "auth_failed")

        identity = authenticator.handle_response(saml_response, relay_state.get("request_id"))
        if not identity:
            return _login_error_redirect(goto_url, "auth_failed")

        response, _status = auth_manager.provision_and_issue_jwt(authenticator.provider, identity)
        return _finish_redirect_login(goto_url, response)


class MfaTotp(Resource):
    """Second login step: verify a TOTP code."""

    @no_auth
    def post(self) -> tuple[dict, HTTPStatus]:
        """Verify the TOTP code and issue the access token.

        Returns:
            dict: The login response.
        """
        data = request.json or {}
        return auth_manager.complete_mfa_totp(data.get("mfa_token", ""), data.get("code", ""))


class MfaTotpEnroll(Resource):
    """Forced TOTP enrollment during login (provider requires MFA)."""

    @no_auth
    def post(self) -> tuple[dict, HTTPStatus]:
        """Begin (no code) or confirm (with code) the TOTP enrollment.

        Returns:
            dict: The otpauth URI to render as QR code, or the login response.
        """
        data = request.json or {}
        return auth_manager.complete_totp_enrollment(data.get("enroll_token", ""), data.get("code"))


class MfaWebauthnEnroll(Resource):
    """Forced enrollment during login, satisfied with a passkey instead of TOTP."""

    @no_auth
    def post(self) -> tuple[dict, HTTPStatus]:
        """Begin (no credential) or complete (with credential) a passkey enrollment.

        Returns:
            dict: The WebAuthn creation options, or the login response.
        """
        data = request.json or {}
        return auth_manager.complete_passkey_enrollment(
            data.get("enroll_token", ""),
            data.get("challenge_id"),
            data.get("credential"),
            data.get("name", ""),
        )


class MfaWebauthnBegin(Resource):
    """Second login step: start a passkey assertion for the challenged user."""

    @no_auth
    def post(self) -> tuple[dict, HTTPStatus]:
        """Return WebAuthn request options for the MFA passkey ceremony.

        Returns:
            dict: The options and challenge handle.
        """
        data = request.json or {}
        return auth_manager.begin_passkey_authentication(data.get("mfa_token", ""))


class MfaWebauthnFinish(Resource):
    """Second login step: verify the passkey assertion."""

    @no_auth
    def post(self) -> tuple[dict, HTTPStatus]:
        """Verify the assertion and issue the access token.

        Returns:
            dict: The login response.
        """
        data = request.json or {}
        return auth_manager.complete_mfa_passkey(data.get("mfa_token", ""), data.get("challenge_id", ""), data.get("credential") or {})


class WebauthnLoginBegin(Resource):
    """Passwordless passkey login: start a discoverable-credential assertion."""

    @no_auth
    def post(self) -> tuple[dict, HTTPStatus]:
        """Return WebAuthn request options for passwordless login.

        Returns:
            dict: The options and challenge handle.
        """
        return auth_manager.begin_passkey_authentication(None)


class WebauthnLoginFinish(Resource):
    """Passwordless passkey login: verify the assertion and log the user in."""

    @no_auth
    def post(self) -> tuple[dict, HTTPStatus]:
        """Verify the assertion and issue the access token.

        Returns:
            dict: The login response.
        """
        data = request.json or {}
        return auth_manager.complete_passkey_login(data.get("challenge_id", ""), data.get("credential") or {})


def initialize(api: Api) -> None:
    """Initialize the authentication routes for the given API.

    This function adds the following resources to the API:
    - Login: Endpoint for user login at "/api/v1/auth/login"
    - LoginMethods: Public list of enabled login methods at "/api/v1/auth/methods"
    - OAuth login/callback endpoints for redirect-based providers
    - MFA endpoints (TOTP, TOTP enrollment, passkey second factor)
    - Passwordless passkey login endpoints
    - Refresh: Endpoint for refreshing authentication tokens at "/api/v1/auth/refresh"
    - Logout: Endpoint for user logout at "/api/v1/auth/logout"
    Args:
        api (flask_restful.Api): The Flask-RESTful API object to which the resources will be added.
    """
    api.add_resource(Login, "/api/v1/auth/login")
    api.add_resource(LoginMethods, "/api/v1/auth/methods")
    api.add_resource(OAuthLoginRedirect, "/api/v1/auth/oauth/<int:provider_id>/login")
    api.add_resource(OAuthCallback, "/api/v1/auth/oauth/<int:provider_id>/callback")
    api.add_resource(SamlLoginRedirect, "/api/v1/auth/saml/<int:provider_id>/login")
    api.add_resource(SamlAcs, "/api/v1/auth/saml/<int:provider_id>/acs")
    api.add_resource(SamlMetadata, "/api/v1/auth/saml/<int:provider_id>/metadata")
    api.add_resource(MfaTotp, "/api/v1/auth/mfa/totp")
    api.add_resource(MfaTotpEnroll, "/api/v1/auth/mfa/totp/enroll")
    api.add_resource(MfaWebauthnEnroll, "/api/v1/auth/mfa/webauthn/enroll")
    api.add_resource(MfaWebauthnBegin, "/api/v1/auth/mfa/webauthn/begin")
    api.add_resource(MfaWebauthnFinish, "/api/v1/auth/mfa/webauthn/finish")
    api.add_resource(WebauthnLoginBegin, "/api/v1/auth/webauthn/login/begin")
    api.add_resource(WebauthnLoginFinish, "/api/v1/auth/webauthn/login/finish")
    api.add_resource(Refresh, "/api/v1/auth/refresh")
    api.add_resource(Logout, "/api/v1/auth/logout")
