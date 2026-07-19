"""This module provides authentication resources for the Taranis-NG application."""

import urllib
import uuid
from http import HTTPStatus

from auth import saml_authenticator, saml_federation
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
            redirect_response = make_response(redirect(_safe_goto_url(request.args["gotoUrl"])))
            redirect_response.set_cookie("jwt", response["access_token"], **_login_cookie_kwargs())
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
                goto_url = _safe_goto_url(request.args["gotoUrl"])
                url = Config.OPENID_LOGOUT_URL.replace("GOTO_URL", urllib.parse.quote(goto_url)) if Config.OPENID_LOGOUT_URL else goto_url
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


def _is_safe_goto_url(goto_url: str) -> bool:
    r"""Tell whether a gotoUrl is a same-origin destination we may redirect to.

    The login flows redirect the browser to ``gotoUrl`` and, on the legacy path,
    plant the JWT cookie right before doing so. Without this check that turns the
    endpoint into an open redirect (phishing, and the bearer cookie landing on an
    attacker's host). Only two shapes are accepted:

    - a relative path (``/dashboard``), rejecting protocol-relative (``//host``)
      and backslash (``/\host``) forms browsers may normalize to another origin;
    - an absolute http(s) URL whose host matches the current request host.

    Args:
        goto_url (str): The candidate return URL.

    Returns:
        bool: True when the URL is safe to redirect to.
    """
    if not goto_url:
        return False
    parsed = urllib.parse.urlparse(goto_url)
    if not parsed.scheme and not parsed.netloc:
        return goto_url.startswith("/") and goto_url[1:2] not in ("/", "\\")
    return parsed.scheme in ("http", "https") and parsed.netloc == request.host


def _safe_goto_url(goto_url: str | None) -> str:
    """Return ``goto_url`` when it is same-origin, otherwise the site root."""
    return goto_url if goto_url and _is_safe_goto_url(goto_url) else "/"


def _login_cookie_kwargs() -> dict:
    """Cookie flags for the tokens handed to the GUI across a redirect login.

    ``Secure`` follows the request scheme (ProxyFix reflects the proxy's
    ``X-Forwarded-Proto``), so the cookie is protected over HTTPS in production
    without breaking plain-HTTP local/E2E runs. ``SameSite=Lax`` lets the cookie
    survive the top-level redirect back from the IdP while blocking cross-site
    POSTs. ``HttpOnly`` is deliberately NOT set: the GUI reads the value from
    ``document.cookie`` to adopt it and then clears it.
    """
    return {"secure": request.is_secure, "samesite": "Lax"}


def _oauth_redirect_uri(provider_slug: str, config: dict) -> str:
    """Build the OAuth callback URL for a provider.

    Uses the configured override when present, otherwise derives it from the
    request (requires correct X-Forwarded-* handling behind a reverse proxy). The
    slug (not the database id) keeps this URL stable across recreation.

    Args:
        provider_slug (str): The provider slug.
        config (dict): The provider configuration.

    Returns:
        str: The redirect URI registered at the IdP.
    """
    override = (config or {}).get("redirect_uri_override")
    if override:
        return override
    return f"{request.scheme}://{request.host}/api/v1/auth/oauth/{provider_slug}/callback"


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
        redirect_response.set_cookie(name, value, **_login_cookie_kwargs())
    return redirect_response


class OAuthLoginRedirect(Resource):
    """Start the authorization-code flow for a redirect-based (OIDC/OAuth2) provider."""

    @no_auth
    def get(self, provider_slug: str) -> Response:
        """Redirect the browser to the identity provider's authorization endpoint.

        Args:
            provider_slug (str): The auth provider to log in with.

        Returns:
            Response: A redirect to the IdP, or an error for unknown providers.
        """
        authenticator = auth_manager.get_oauth_authenticator(provider_slug)
        if not authenticator:
            return {"error": "Unknown login method"}, HTTPStatus.NOT_FOUND
        provider_id = authenticator.provider.id
        goto_url = _safe_goto_url(request.args.get("gotoUrl"))
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
        redirect_uri = _oauth_redirect_uri(provider_slug, authenticator.config)
        try:
            return redirect(authenticator.get_authorization_url(redirect_uri, state, nonce, code_verifier=code_verifier))
        except Exception as ex:
            logger.exception(f"Building the authorization URL failed: {ex}")
            return _login_error_redirect(goto_url, "auth_failed")


class OAuthCallback(Resource):
    """Handle the IdP redirect back: exchange the code and hand the JWT to the GUI."""

    @no_auth
    def get(self, provider_slug: str) -> Response:
        """Finish the authorization-code flow and redirect to the GUI.

        The verdict reaches the GUI in cookies: the JWT on success, or the scoped
        MFA token when the user still owes a second factor; on failure the GUI
        login page receives a login_error query parameter.

        Args:
            provider_slug (str): The auth provider the flow was started with.

        Returns:
            Response: A redirect response.
        """
        authenticator = auth_manager.get_oauth_authenticator(provider_slug)
        state = auth_manager.decode_scoped_token(request.args.get("state", ""), "oauth_state")
        if not authenticator or not state or state.get("pid") != authenticator.provider.id:
            return {"error": "Invalid state"}, HTTPStatus.UNAUTHORIZED
        goto_url = state.get("gotoUrl") or "/"

        code = request.args.get("code")
        if not code:
            return _login_error_redirect(goto_url, "auth_failed")

        redirect_uri = _oauth_redirect_uri(provider_slug, authenticator.config)
        identity = authenticator.handle_callback(redirect_uri, code, state.get("nonce"), code_verifier=state.get("code_verifier"))
        if not identity:
            return _login_error_redirect(goto_url, "auth_failed")

        response, _status = auth_manager.provision_and_issue_jwt(authenticator.provider, identity)
        return _finish_redirect_login(goto_url, response)


def _saml_acs_url(provider_slug: str, config: dict) -> str:
    """Build the Assertion Consumer Service URL for a SAML provider.

    Uses the configured override when present, otherwise derives it from the
    request (requires correct X-Forwarded-* handling behind a reverse proxy).

    Args:
        provider_slug (str): The provider slug.
        config (dict): The provider configuration.

    Returns:
        str: The ACS URL registered at the identity provider.
    """
    override = (config or {}).get("acs_url_override")
    if override:
        return override
    return f"{request.scheme}://{request.host}/api/v1/auth/saml/{provider_slug}/acs"


def _saml_disco_url(provider_slug: str) -> str:
    """Build the DiscoveryResponse URL for a federation-mode SAML provider.

    Derived from the request (correct X-Forwarded-* handling required behind a
    proxy). Both the login redirect and the published metadata use this, so the
    ``return`` we hand the discovery service always matches the DiscoveryResponse
    the service validates it against.

    Args:
        provider_slug (str): The provider slug.

    Returns:
        str: The DiscoveryResponse endpoint URL.
    """
    return f"{request.scheme}://{request.host}/api/v1/auth/saml/{provider_slug}/disco"


class SamlLoginRedirect(Resource):
    """Start the SAML web browser SSO flow for a saml-kind provider."""

    @no_auth
    def get(self, provider_slug: str) -> Response:
        """Redirect the browser to the IdP, or to the discovery service in federation mode.

        Args:
            provider_slug (str): The auth provider to log in with.

        Returns:
            Response: A redirect to the IdP or WAYF, or an error for unknown providers.
        """
        authenticator = auth_manager.get_saml_authenticator(provider_slug)
        if not authenticator:
            return {"error": "Unknown login method"}, HTTPStatus.NOT_FOUND
        provider_id = authenticator.provider.id
        goto_url = _safe_goto_url(request.args.get("gotoUrl"))
        try:
            if authenticator.is_federation():
                # Send the user to the discovery service to pick their IdP. Our
                # state rides along in the return URL; the WAYF preserves that
                # query string and appends the chosen entityID to it.
                disco_state = auth_manager.make_scoped_token(
                    f"provider:{provider_id}",
                    "saml_disco",
                    expires_minutes=auth_manager.OAUTH_STATE_MINUTES,
                    pid=provider_id,
                    gotoUrl=goto_url,
                )
                return_url = f"{_saml_disco_url(provider_slug)}?state={urllib.parse.quote(disco_state)}"
                return redirect(authenticator.get_discovery_redirect_url(return_url))

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
            acs_url = _saml_acs_url(provider_slug, authenticator.config)
            return redirect(authenticator.get_login_redirect_url(acs_url, relay_state, request_id))
        except Exception as ex:
            logger.exception(f"Building the SAML request failed: {ex}")
            return _login_error_redirect(goto_url, "auth_failed")


class SamlDisco(Resource):
    """DiscoveryResponse endpoint: receive the IdP the user picked at the WAYF."""

    @no_auth
    def get(self, provider_slug: str) -> Response:
        """Turn the chosen IdP entityID into an AuthnRequest to that IdP.

        The discovery service sends the browser here with the chosen entityID; we
        resolve it against the verified federation metadata (an entity not in the
        federation is refused), then build and redirect to the AuthnRequest just
        as the single-IdP flow does.

        Args:
            provider_slug (str): The auth provider the flow was started with.

        Returns:
            Response: A redirect to the chosen IdP, or a login-error redirect.
        """
        authenticator = auth_manager.get_saml_authenticator(provider_slug)
        state = auth_manager.decode_scoped_token(request.args.get("state", ""), "saml_disco")
        if not authenticator or not state or state.get("pid") != authenticator.provider.id:
            return {"error": "Invalid state"}, HTTPStatus.UNAUTHORIZED
        provider_id = authenticator.provider.id
        goto_url = state.get("gotoUrl") or "/"

        entity_id = request.args.get(saml_authenticator.DISCOVERY_RETURN_ID_PARAM)
        if not entity_id:
            # the user cancelled at the discovery service, or it returned nothing
            return _login_error_redirect(goto_url, "auth_cancelled")

        try:
            resolved = saml_federation.resolve_idp(authenticator.provider, entity_id)
            if not resolved:
                logger.warning(f"SAML discovery: '{entity_id}' is not an IdP in the federation for provider {provider_id}")
                return _login_error_redirect(goto_url, "auth_failed")
            request_id = f"_{uuid.uuid4().hex}"
            relay_state = auth_manager.make_scoped_token(
                f"provider:{provider_id}",
                "saml_state",
                expires_minutes=auth_manager.OAUTH_STATE_MINUTES,
                pid=provider_id,
                gotoUrl=goto_url,
                request_id=request_id,
                idp_entity_id=entity_id,
            )
            acs_url = _saml_acs_url(provider_slug, authenticator.config)
            return redirect(authenticator.get_authn_request_url(resolved.sso_url, acs_url, relay_state, request_id))
        except Exception as ex:
            logger.exception(f"Building the SAML request after discovery failed: {ex}")
            return _login_error_redirect(goto_url, "auth_failed")


class SamlMetadata(Resource):
    """Publish the SP metadata an identity provider needs to register this service."""

    @no_auth
    def get(self, provider_slug: str) -> Response:
        """Serve the SAML SP metadata document.

        Args:
            provider_slug (str): The auth provider to describe.

        Returns:
            Response: The metadata XML, or an error for unknown providers.
        """
        authenticator = auth_manager.get_saml_authenticator(provider_slug)
        if not authenticator:
            return {"error": "Unknown login method"}, HTTPStatus.NOT_FOUND
        acs_url = _saml_acs_url(provider_slug, authenticator.config)
        disco_url = _saml_disco_url(provider_slug)
        metadata = authenticator.get_metadata_xml(acs_url, disco_url)
        return Response(metadata, mimetype="application/samlmetadata+xml")


class SamlAcs(Resource):
    """Assertion Consumer Service: validate the posted SAMLResponse and log in."""

    @no_auth
    def post(self, provider_slug: str) -> Response:
        """Finish the SAML flow and redirect to the GUI.

        The verdict reaches the GUI in cookies: the JWT on success, or the scoped
        MFA token when the user still owes a second factor; on failure the GUI
        login page receives a login_error query parameter.

        Args:
            provider_slug (str): The auth provider the flow was started with.

        Returns:
            Response: A redirect response.
        """
        authenticator = auth_manager.get_saml_authenticator(provider_slug)
        relay_state = auth_manager.decode_scoped_token(request.form.get("RelayState", ""), "saml_state")
        if not authenticator or not relay_state or relay_state.get("pid") != authenticator.provider.id:
            return {"error": "Invalid state"}, HTTPStatus.UNAUTHORIZED
        goto_url = relay_state.get("gotoUrl") or "/"

        saml_response = request.form.get("SAMLResponse")
        if not saml_response:
            return _login_error_redirect(goto_url, "auth_failed")

        identity = authenticator.handle_response(saml_response, relay_state.get("request_id"), relay_state.get("idp_entity_id"))
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
    api.add_resource(OAuthLoginRedirect, "/api/v1/auth/oauth/<string:provider_slug>/login")
    api.add_resource(OAuthCallback, "/api/v1/auth/oauth/<string:provider_slug>/callback")
    api.add_resource(SamlLoginRedirect, "/api/v1/auth/saml/<string:provider_slug>/login")
    api.add_resource(SamlDisco, "/api/v1/auth/saml/<string:provider_slug>/disco")
    api.add_resource(SamlAcs, "/api/v1/auth/saml/<string:provider_slug>/acs")
    api.add_resource(SamlMetadata, "/api/v1/auth/saml/<string:provider_slug>/metadata")
    api.add_resource(MfaTotp, "/api/v1/auth/mfa/totp")
    api.add_resource(MfaTotpEnroll, "/api/v1/auth/mfa/totp/enroll")
    api.add_resource(MfaWebauthnEnroll, "/api/v1/auth/mfa/webauthn/enroll")
    api.add_resource(MfaWebauthnBegin, "/api/v1/auth/mfa/webauthn/begin")
    api.add_resource(MfaWebauthnFinish, "/api/v1/auth/mfa/webauthn/finish")
    api.add_resource(WebauthnLoginBegin, "/api/v1/auth/webauthn/login/begin")
    api.add_resource(WebauthnLoginFinish, "/api/v1/auth/webauthn/login/finish")
    api.add_resource(Refresh, "/api/v1/auth/refresh")
    api.add_resource(Logout, "/api/v1/auth/logout")
