"""OIDC / OAuth 2.0 authenticator driven by a database-configured provider.

Provider ``config`` keys:
    oidc kind: issuer_url (discovery base), client_id, scopes (default
        "openid profile email"), username_claim (default "preferred_username"),
        name_claim (default "name"), email_claim (default "email"),
        redirect_uri_override, logout_url, pkce_method (default "none").
    oauth2 kind: authorize_url, token_url, userinfo_url, client_id, scopes,
        username_claim, name_claim, email_claim, pkce_method (default "none").

The client secret is the provider's encrypted secret. ID tokens are verified
against the issuer's JWKS (signature, issuer, audience, expiry, nonce).

When ``pkce_method`` is ``S256`` or the explicit legacy-compatibility value
``plain``, a random ``code_verifier`` is generated per login attempt and
retained in the opaque server-side authentication transaction until the token
exchange. ``plain`` exposes the verifier in the browser-visible authorization
request and must only be selected for providers that cannot use S256.
"""

from __future__ import annotations

import secrets
from http import HTTPStatus
from typing import TYPE_CHECKING

import jwt as pyjwt
from auth.base_authenticator import BaseAuthenticator, ExternalIdentity, ProviderConfigurationError
from auth.url_guard import OUTBOUND_TIMEOUT, assert_auth_endpoint_url, fetch_auth_json, read_limited_json
from authlib.integrations.base_client import OAuthError
from authlib.integrations.requests_client import OAuth2Session
from managers import log_manager

if TYPE_CHECKING:
    from model.auth_provider import AuthProvider

ID_TOKEN_ALGORITHMS = ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512", "PS256", "PS384", "PS512"]
# PKCE code_verifier: 43-128 chars of the unreserved set [A-Z][a-z][0-9]-._~.
# token_urlsafe(64) yields 86 chars in that alphabet, comfortably in range.
PKCE_VERIFIER_BYTES = 64
# ``none`` remains for providers that do not implement PKCE. ``plain`` is an
# explicit legacy compatibility mode; it is never selected as a fallback.
PKCE_METHODS = ("none", "S256", "plain")
# provider kinds this module drives, and therefore the ones it can test
OAUTH_VERIFIABLE_KINDS = ("oidc", "oauth2")
# Length of the throwaway authorization code the configuration probe sends. It
# only has to be a code no provider could ever have issued.
PROBE_CODE_BYTES = 32

# RFC 6749 section 5.2: the token endpoint authenticates the client before it
# looks at the grant, so these codes can only be a verdict on our client
# credentials. Keycloak answers a wrong secret with ``unauthorized_client``
# rather than the ``invalid_client`` the RFC suggests, hence both.
CLIENT_AUTH_ERRORS = ("invalid_client", "unauthorized_client")
# Conversely, these are all decisions a server can only reach *after* it has
# authenticated the client - the grant, the scope and the resource are all bound
# to the client - so receiving one proves the credentials were accepted.
# ``invalid_request`` is deliberately absent: a malformed request is rejected
# before anyone is authenticated, so it proves nothing either way.
POST_CLIENT_AUTH_ERRORS = ("invalid_grant", "unsupported_grant_type", "invalid_scope", "invalid_target")

# per-provider caches, invalidated when the provider row is updated
_metadata_cache: dict[int, tuple[str, dict]] = {}
_jwks_cache: dict[int, tuple[str, dict]] = {}


def fetch_discovery(issuer_url: str | None, provider_name: str) -> dict:
    """Fetch and validate an OIDC discovery document.

    Args:
        issuer_url (str): The configured issuer (discovery base) URL.
        provider_name (str): Provider name, for error messages.

    Returns:
        dict: The discovery document.

    Raises:
        ValueError: When the issuer is missing, the document's own issuer does
            not match the configured one, or a required endpoint is missing or
            not an acceptable auth endpoint URL.
    """
    issuer = (issuer_url or "").rstrip("/")
    if not issuer:
        msg = f"OIDC provider '{provider_name}' has no issuer URL"
        raise ValueError(msg)
    metadata = fetch_auth_json(f"{issuer}/.well-known/openid-configuration")
    discovered_issuer = metadata.get("issuer")
    if not isinstance(discovered_issuer, str) or discovered_issuer.rstrip("/") != issuer:
        msg = f"OIDC discovery issuer does not match the configured issuer for provider '{provider_name}'"
        raise ValueError(msg)
    for key in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
        endpoint = metadata.get(key)
        if not isinstance(endpoint, str) or not endpoint:
            msg = f"OIDC discovery document has no valid '{key}' for provider '{provider_name}'"
            raise ValueError(msg)
        assert_auth_endpoint_url(endpoint)
    # userinfo is used at login; introspection and revocation only by the
    # configuration test, but all three are fetched server-side and so must pass
    # the same SSRF guard as the endpoints above.
    for key in ("userinfo_endpoint", "introspection_endpoint", "revocation_endpoint"):
        endpoint = metadata.get(key)
        if endpoint is not None:
            if not isinstance(endpoint, str) or not endpoint:
                msg = f"OIDC discovery document has an invalid '{key}' for provider '{provider_name}'"
                raise ValueError(msg)
            assert_auth_endpoint_url(endpoint)
    return metadata


def resolve_endpoints(kind: str, config: dict, provider_name: str, metadata: dict | None = None) -> dict:
    """Resolve a provider's endpoints (discovery for oidc, configuration for oauth2).

    Args:
        kind (str): The provider kind (``oidc`` or ``oauth2``).
        config (dict): The provider configuration.
        provider_name (str): Provider name, for error messages.
        metadata (dict): An already-fetched discovery document, when the caller
            holds a cached one; fetched here otherwise.

    Returns:
        dict: The authorize / token / userinfo / jwks_uri / issuer endpoints.

    Raises:
        ValueError: When a required endpoint is missing or unacceptable.
    """
    if kind == "oidc":
        metadata = metadata if metadata is not None else fetch_discovery(config.get("issuer_url"), provider_name)
        return {
            "authorize": metadata["authorization_endpoint"],
            "token": metadata["token_endpoint"],
            "userinfo": metadata.get("userinfo_endpoint"),
            "jwks_uri": metadata.get("jwks_uri"),
            "issuer": metadata.get("issuer"),
            "introspect": metadata.get("introspection_endpoint"),
            "revoke": metadata.get("revocation_endpoint"),
        }
    endpoints = {
        "authorize": config.get("authorize_url"),
        "token": config.get("token_url"),
        "userinfo": config.get("userinfo_url"),
        "jwks_uri": None,
        "issuer": None,
        "introspect": None,
        "revoke": None,
    }
    for key in ("authorize", "token"):
        endpoint = endpoints[key]
        if not isinstance(endpoint, str) or not endpoint:
            msg = f"OAuth provider '{provider_name}' has no valid {key} URL"
            raise ValueError(msg)
        assert_auth_endpoint_url(endpoint)
    if endpoints["userinfo"]:
        assert_auth_endpoint_url(endpoints["userinfo"])
    return endpoints


def _token_error_code(ex: Exception) -> str | None:
    """Return the OAuth 2.0 error code of a failed token request, when it carries one."""
    error = getattr(ex, "error", None)
    return error if isinstance(error, str) and error else None


def _is_client_auth_rejection(ex: Exception) -> bool:
    """Tell whether a token-endpoint failure was a rejection of our client credentials."""
    if _token_error_code(ex) in CLIENT_AUTH_ERRORS:
        return True
    # A provider that answers client authentication failures with a bare 401 and
    # no parsable body still tells us what we need to know.
    response = getattr(ex, "response", None)
    return getattr(response, "status_code", None) == HTTPStatus.UNAUTHORIZED


class OAuth2Authenticator(BaseAuthenticator):
    """Authorization-code flow against an OIDC or plain OAuth 2.0 provider."""

    def __init__(self, provider: AuthProvider) -> None:
        """Initialize the authenticator from a provider row.

        Args:
            provider (AuthProvider): The oidc- or oauth2-kind provider configuration.
        """
        self.provider = provider
        self.config = provider.config or {}

    def _cache_marker(self) -> str:
        """Return a marker that changes whenever the provider row is updated."""
        return str(self.provider.updated_at)

    def _metadata(self) -> dict:
        """Fetch (and cache) the OIDC discovery document."""
        marker = self._cache_marker()
        cached = _metadata_cache.get(self.provider.id)
        if cached and cached[0] == marker:
            return cached[1]
        metadata = fetch_discovery(self.config.get("issuer_url"), self.provider.name)
        _metadata_cache[self.provider.id] = (marker, metadata)
        return metadata

    def _endpoints(self) -> dict:
        """Resolve the endpoints for this provider (discovery for oidc, config for oauth2)."""
        metadata = self._metadata() if self.provider.kind == "oidc" else None
        return resolve_endpoints(self.provider.kind, self.config, self.provider.name, metadata)

    def _client_secret(self) -> str | None:
        """Return the decrypted client secret, refusing to log in with a broken one.

        A secret that is stored but no longer decryptable (the secrets encryption
        key changed) would otherwise be sent as no secret at all, and the IdP
        would answer with an "invalid client credentials" error that points the
        administrator at the value they typed rather than at the key.

        Raises:
            ProviderConfigurationError: When the stored secret cannot be decrypted.
        """
        secret = self.provider.get_secret_plaintext()
        if self.provider.secret and secret is None:
            msg = (
                f"The stored client secret of provider '{self.provider.name}' could not be decrypted - "
                f"was the secrets encryption key changed? Re-enter the client secret."
            )
            raise ProviderConfigurationError(msg)
        return secret

    def _scopes(self) -> str:
        """Return the configured scopes (with kind-appropriate defaults)."""
        default = "openid profile email" if self.provider.kind == "oidc" else ""
        return self.config.get("scopes") or default

    def _pkce_method(self) -> str:
        """Return the configured PKCE method (``none``, ``S256`` or ``plain``)."""
        method = (self.config.get("pkce_method") or "none").strip()
        if method not in PKCE_METHODS:
            msg = f"Unsupported PKCE method '{method}' for provider '{self.provider.name}'; use S256, plain or none"
            raise ValueError(msg)
        return method

    def _use_pkce(self) -> bool:
        """Return whether this provider requests PKCE on the auth flow."""
        return self._pkce_method() != "none"

    def uses_pkce(self) -> bool:
        """Public accessor for whether PKCE is enabled on this provider."""
        return self._use_pkce()

    def pkce_method(self) -> str:
        """Public accessor for the configured PKCE method."""
        return self._pkce_method()

    @staticmethod
    def generate_code_verifier() -> str:
        """Generate a PKCE code_verifier that satisfies RFC 7636 (43-128 chars)."""
        return secrets.token_urlsafe(PKCE_VERIFIER_BYTES)

    def get_authorization_url(self, redirect_uri: str, state: str, nonce: str, code_verifier: str | None = None) -> str:
        """Build the IdP authorization URL to redirect the browser to.

        Args:
            redirect_uri (str): Our callback URL.
            state (str): Signed state parameter (CSRF protection).
            nonce (str): Nonce to be bound into the ID token (oidc only).
            code_verifier (str): PKCE code_verifier. Required when the
                provider's ``pkce_method`` is ``S256`` or ``plain``; ignored
                otherwise.

        Returns:
            str: The authorization URL.
        """
        endpoints = self._endpoints()
        pkce_method = self._pkce_method()
        # OAuth2Session needs code_challenge_method='S256' in its constructor
        # for Authlib to compute the S256 challenge and emit the parameter.
        session = OAuth2Session(
            self.config.get("client_id"),
            scope=self._scopes(),
            redirect_uri=redirect_uri,
            code_challenge_method="S256" if pkce_method == "S256" else None,
        )
        extra: dict[str, str] = {}
        if self.provider.kind == "oidc":
            extra["nonce"] = nonce
        if pkce_method != "none":
            if not code_verifier:
                msg = f"PKCE method '{pkce_method}' enabled for provider '{self.provider.name}' but no code_verifier was supplied"
                raise ValueError(msg)
            if pkce_method == "S256":
                # Authlib derives code_challenge = BASE64URL(SHA256(code_verifier))
                # and adds code_challenge_method=S256 automatically.
                extra["code_verifier"] = code_verifier
            else:
                # Legacy RFC 7636 compatibility: this is deliberately explicit
                # because the verifier is visible in the authorization request.
                extra["code_challenge"] = code_verifier
                extra["code_challenge_method"] = "plain"
        url, _ = session.create_authorization_url(endpoints["authorize"], state=state, **extra)
        return url

    def handle_callback(self, redirect_uri: str, code: str, nonce: str, code_verifier: str | None = None) -> ExternalIdentity | None:
        """Exchange the authorization code and resolve the external identity.

        Args:
            redirect_uri (str): The callback URL used in the authorization request.
            code (str): The authorization code returned by the IdP.
            nonce (str): The nonce bound into the state (oidc only).
            code_verifier (str): PKCE code_verifier, required when the
                provider's ``pkce_method`` is ``S256`` or ``plain``; must match
                the verifier sent on the authorize request. Ignored otherwise.

        Returns:
            ExternalIdentity: The authenticated identity, or None on failure.

        Raises:
            ProviderConfigurationError: When the identity provider rejected this
                service's own client credentials, which no user can work around.
        """
        try:
            endpoints = self._endpoints()
            secret = self._client_secret()
            session = OAuth2Session(self.config.get("client_id"), secret, scope=self._scopes(), redirect_uri=redirect_uri)
            fetch_kwargs: dict[str, str] = {}
            if self._use_pkce():
                if not code_verifier:
                    log_manager.store_auth_error_activity(
                        f"PKCE method '{self._pkce_method()}' enabled for provider '{self.provider.name}' "
                        f"but no code_verifier was supplied at callback",
                    )
                    return None
                fetch_kwargs["code_verifier"] = code_verifier
            assert_auth_endpoint_url(endpoints["token"])
            try:
                token = session.fetch_token(
                    endpoints["token"],
                    code=code,
                    grant_type="authorization_code",
                    timeout=OUTBOUND_TIMEOUT,
                    allow_redirects=False,
                    **fetch_kwargs,
                )
            except Exception as ex:
                if not _is_client_auth_rejection(ex):
                    raise
                msg = (
                    f"Provider '{self.provider.name}' rejected our client credentials at the token endpoint "
                    f"({_token_error_code(ex) or 'unauthorized'}); check the client ID and client secret"
                )
                log_manager.store_auth_error_activity(msg, ex)
                raise ProviderConfigurationError(msg) from ex

            claims = {}
            if self.provider.kind == "oidc":
                claims = self._verify_id_token(token.get("id_token"), endpoints, nonce)
                if claims is None:
                    return None

            username_claim = self.config.get("username_claim") or "preferred_username"
            if username_claim not in claims and endpoints["userinfo"]:
                assert_auth_endpoint_url(endpoints["userinfo"])
                userinfo = session.get(
                    endpoints["userinfo"],
                    timeout=OUTBOUND_TIMEOUT,
                    allow_redirects=False,
                    stream=True,
                )
                try:
                    claims = {**read_limited_json(userinfo), **claims}
                finally:
                    userinfo.close()

            username = claims.get(username_claim)
            if not username:
                log_manager.store_auth_error_activity(
                    f"Provider '{self.provider.name}' returned no '{username_claim}' claim; available: {sorted(claims.keys())}",
                )
                return None

            external_id = claims.get("sub") or claims.get("id")
            return ExternalIdentity(
                username=str(username),
                external_id=str(external_id) if external_id is not None else None,
                name=claims.get(self.config.get("name_claim") or "name"),
                email=claims.get(self.config.get("email_claim") or "email"),
            )
        except ProviderConfigurationError:
            # An administrator's problem, not the subject's: reported separately
            # so the login page can say so. Already logged where it was raised.
            raise
        except Exception as ex:
            log_manager.store_auth_error_activity(f"OAuth callback failed for provider '{self.provider.name}'", ex)
            return None

    def _verify_id_token(self, id_token: str | None, endpoints: dict, nonce: str) -> dict | None:
        """Verify the ID token signature and standard claims against the issuer's JWKS.

        Args:
            id_token (str): The raw ID token from the token response.
            endpoints (dict): Resolved endpoints including jwks_uri and issuer.
            nonce (str): Expected nonce.

        Returns:
            dict: The verified claims, or None when validation fails.
        """
        if not id_token or not endpoints["jwks_uri"]:
            log_manager.store_auth_error_activity(f"Provider '{self.provider.name}' returned no verifiable ID token")
            return None
        assert_auth_endpoint_url(endpoints["jwks_uri"])
        marker = self._cache_marker()
        cached = _jwks_cache.get(self.provider.id)
        if cached and cached[0] == marker:
            jwks = cached[1]
        else:
            jwks = fetch_auth_json(endpoints["jwks_uri"])
            _jwks_cache[self.provider.id] = (marker, jwks)
        header = pyjwt.get_unverified_header(id_token)
        algorithm = header.get("alg")
        if algorithm not in ID_TOKEN_ALGORITHMS:
            msg = f"ID token from provider '{self.provider.name}' uses an unsupported algorithm"
            raise ValueError(msg)
        key_id = header.get("kid")
        candidates = self._matching_signing_keys(jwks, algorithm, key_id)
        if len(candidates) != 1 and cached:
            # Normal IdP key rollover must not require an administrator to edit
            # the provider merely to invalidate our provider-row cache marker.
            jwks = fetch_auth_json(endpoints["jwks_uri"])
            _jwks_cache[self.provider.id] = (marker, jwks)
            candidates = self._matching_signing_keys(jwks, algorithm, key_id)
        if len(candidates) != 1:
            msg = f"ID token from provider '{self.provider.name}' has no unique matching signing key"
            raise ValueError(msg)
        claims = pyjwt.decode(
            id_token,
            candidates[0].key,
            algorithms=ID_TOKEN_ALGORITHMS,
            audience=self.config.get("client_id"),
            issuer=endpoints["issuer"],
            leeway=120,
        )
        if nonce and claims.get("nonce") != nonce:
            log_manager.store_auth_error_activity(f"Nonce mismatch in ID token from provider '{self.provider.name}'")
            return None
        return claims

    @staticmethod
    def _matching_signing_keys(jwks: dict, algorithm: str, key_id: str | None) -> list[pyjwt.PyJWK]:
        """Return signature keys matching the token header without ambiguity."""
        return [
            key
            for key in pyjwt.PyJWKSet.from_dict(jwks).keys
            if key.algorithm_name == algorithm and key.public_key_use in (None, "sig") and (key_id is None or key.key_id == key_id)
        ]


def _probe_client_authenticated_endpoint(session: OAuth2Session, url: str, method: str) -> tuple[str, str] | None:
    """Ask an endpoint whose *only* precondition is client authentication.

    RFC 7662 (introspection) and RFC 7009 (revocation) both require the client to
    authenticate and both answer 200 for a token they know nothing about. That
    makes them the sharpest possible test of a client ID and secret: nothing but
    the credentials can decide the outcome, so 200 means they were accepted and
    401 means they were not. Authlib signs the request with the same client
    authentication the login uses, so a pass here is a pass at login too.

    Args:
        session (OAuth2Session): Session carrying the client ID and secret.
        url (str): The introspection or revocation endpoint.
        method (str): ``introspect_token`` or ``revoke_token``.

    Returns:
        tuple | None: The verdict and detail, or None when this endpoint gave no
            usable answer and the next probe should be tried.
    """
    try:
        response = getattr(session, method)(
            url,
            token=secrets.token_urlsafe(PROBE_CODE_BYTES),
            token_type_hint="access_token",  # noqa: S106 - a hint about the throwaway token's type, not a secret
            timeout=OUTBOUND_TIMEOUT,
            allow_redirects=False,
            stream=True,  # the body is irrelevant; the status code carries the verdict
        )
    except Exception:
        return None
    try:
        if response.status_code == HTTPStatus.OK:
            return "accepted", f"the client ID and secret were accepted at {url}"
        # 401 is what RFC 6749 section 5.2 reserves for failed client
        # authentication. 403 is not read as a rejection: it usually means the
        # client authenticated but may not introspect, so let the next probe try.
        if response.status_code == HTTPStatus.UNAUTHORIZED:
            return "rejected", f"{url} refused the client ID or client secret (HTTP 401)"
    finally:
        response.close()
    return None


def _probe_client_credentials_grant(session: OAuth2Session, token_url: str) -> tuple[str, str] | None:
    """Ask the token endpoint for a client_credentials token, which tests only the credentials.

    Args:
        session (OAuth2Session): Session carrying the client ID and secret.
        token_url (str): The token endpoint.

    Returns:
        tuple | None: The verdict and detail, or None when the answer does not
            separate the credentials from the grant and the next probe should run.
    """
    try:
        session.fetch_token(token_url, grant_type="client_credentials", timeout=OUTBOUND_TIMEOUT, allow_redirects=False)
    except OAuthError as ex:
        error = _token_error_code(ex) or "unknown_error"
        if error == "invalid_client":
            return "rejected", f"invalid_client: {ex.description or 'the client ID or client secret was refused'}"
        if error in POST_CLIENT_AUTH_ERRORS:
            # The server got past client authentication and only then refused the
            # grant, so the credentials are good.
            return "accepted", f"the client authenticated; only the client_credentials grant was refused ({error})"
        # ``unauthorized_client`` is deliberately not decided here: Keycloak uses
        # it both for a wrong secret and for a client with service accounts off.
        return None
    except Exception:
        return None
    return "accepted", "the client ID and secret were accepted for a client_credentials token"


def _probe_authorization_code(session: OAuth2Session, token_url: str) -> tuple[str, str]:
    """Last resort: exchange an authorization code that was never issued.

    Weaker than the probes above, because it assumes the server authenticates the
    client before it validates the grant (RFC 6749 section 5.2) - not every
    implementation does, and one that checks the code first would answer
    ``invalid_grant`` without ever looking at the secret. It is still the only
    probe that works everywhere, so it decides when nothing better is available.

    Args:
        session (OAuth2Session): Session carrying the client ID and secret.
        token_url (str): The token endpoint.

    Returns:
        tuple: The verdict and a detail describing what the provider answered.
    """
    try:
        session.fetch_token(
            token_url,
            code=secrets.token_urlsafe(PROBE_CODE_BYTES),
            grant_type="authorization_code",
            timeout=OUTBOUND_TIMEOUT,
            allow_redirects=False,
        )
    except OAuthError as ex:
        error = _token_error_code(ex) or "unknown_error"
        if _is_client_auth_rejection(ex):
            return "rejected", f"{error}: {ex.description or 'the client ID or client secret was refused'}"
        if error in POST_CLIENT_AUTH_ERRORS:
            return "inconclusive", (
                f"the throwaway authorization code was refused ({error}) before the client credentials were reported on; "
                f"this provider publishes no introspection or revocation endpoint, so the secret could not be confirmed"
            )
        return "inconclusive", f"{error}: {ex.description or 'unexpected token endpoint response'}"
    except Exception as ex:
        if _is_client_auth_rejection(ex):
            return "rejected", "the token endpoint refused the client ID or client secret"
        return "inconclusive", f"the token endpoint could not be reached: {ex}"
    # A provider that issues a token for a code nobody ever authorized is broken,
    # but it did accept our credentials, so report both halves.
    return "accepted", "the token endpoint issued a token for an invented authorization code - verify the provider's configuration"


def _probe_client_credentials(endpoints: dict, client_id: str, secret: str | None, redirect_uri: str | None) -> tuple[str, str]:
    """Decide whether the identity provider accepts this client ID and secret.

    Tries the checks in order of how sharply each separates the credentials from
    everything else, stopping at the first that gives a straight answer:
    introspection, then revocation (both require client authentication and
    nothing else), then the client_credentials grant, and finally an
    authorization code that was never issued. No state is created at the provider
    by any of them.

    Args:
        endpoints (dict): Resolved provider endpoints.
        client_id (str): The configured client ID.
        secret (str): The client secret, or None for a public client.
        redirect_uri (str): Our callback URL, so a mismatch surfaces too.

    Returns:
        tuple: The verdict (``accepted`` | ``rejected`` | ``inconclusive``) and a
            detail string describing what the provider answered.
    """
    session = OAuth2Session(client_id, secret, redirect_uri=redirect_uri)
    for url, method in ((endpoints.get("introspect"), "introspect_token"), (endpoints.get("revoke"), "revoke_token")):
        if url:
            verdict = _probe_client_authenticated_endpoint(session, url, method)
            if verdict:
                return verdict
    verdict = _probe_client_credentials_grant(session, endpoints["token"])
    if verdict:
        return verdict
    return _probe_authorization_code(session, endpoints["token"])


def verify_configuration(
    kind: str,
    config: dict,
    secret: str | None,
    redirect_uri: str | None = None,
    provider_name: str = "this login method",
) -> dict:
    """Check an unsaved OIDC/OAuth 2.0 configuration against the identity provider.

    Resolves the endpoints (discovery for oidc), fetches the signing keys, and
    puts the client ID and client secret to the identity provider directly (see
    :func:`_probe_client_credentials`), so a wrong credential is caught here
    rather than as an opaque failed login. Nothing is stored and no state is
    created at the provider.

    Args:
        kind (str): The provider kind (``oidc`` or ``oauth2``).
        config (dict): The provider configuration being tested.
        secret (str): The client secret in plaintext, or None.
        redirect_uri (str): The callback URL registered at the provider.
        provider_name (str): Provider name, for error messages.

    Returns:
        dict: The resolved endpoints, the signing key count and the client
            credential verdict (``client_status`` and ``detail``).

    Raises:
        ValueError: When the configuration itself is unusable (missing issuer or
            client ID, discovery mismatch, unreachable or unacceptable endpoint).
    """
    if kind not in OAUTH_VERIFIABLE_KINDS:
        msg = f"Only OIDC and OAuth 2.0 login methods can be tested, not '{kind}'"
        raise ValueError(msg)

    metadata = fetch_discovery(config.get("issuer_url"), provider_name) if kind == "oidc" else None
    endpoints = resolve_endpoints(kind, config, provider_name, metadata)

    client_id = (config.get("client_id") or "").strip()
    if not client_id:
        msg = f"No client ID is configured for {provider_name}"
        raise ValueError(msg)

    signing_key_count = None
    if endpoints["jwks_uri"]:
        jwks = fetch_auth_json(endpoints["jwks_uri"])
        try:
            signing_key_count = len([key for key in pyjwt.PyJWKSet.from_dict(jwks).keys if key.public_key_use in (None, "sig")])
        except Exception as ex:
            msg = f"The signing keys published at {endpoints['jwks_uri']} could not be read: {ex}"
            raise ValueError(msg) from ex

    client_status, detail = _probe_client_credentials(endpoints, client_id, secret, redirect_uri)
    if not secret:
        # Say so plainly: with no secret to send, a pass means the identity
        # provider knows this client ID, not that any credential was verified.
        detail = f"no client secret is configured, so only the client ID was checked - {detail}"

    return {
        "issuer": endpoints["issuer"],
        "authorize_url": endpoints["authorize"],
        "token_url": endpoints["token"],
        "userinfo_url": endpoints["userinfo"],
        "signing_key_count": signing_key_count,
        "client_status": client_status,
        "has_secret": bool(secret),
        "detail": detail,
    }
