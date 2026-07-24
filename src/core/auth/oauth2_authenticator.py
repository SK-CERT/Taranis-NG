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

When ``pkce_method`` is ``S256`` or ``plain``, a random ``code_verifier`` is
generated per login attempt and sent as ``code_challenge`` (with the matching
``code_challenge_method``) on the authorization request, then replayed on the
token exchange. The verifier is carried inside the signed ``state`` JWT so it
survives the browser round-trip without server-side state.
"""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING

import jwt as pyjwt
import requests
from auth.base_authenticator import BaseAuthenticator, ExternalIdentity
from authlib.integrations.requests_client import OAuth2Session
from jwt import PyJWKClient
from managers import log_manager

if TYPE_CHECKING:
    from model.auth_provider import AuthProvider

HTTP_TIMEOUT = 10
ID_TOKEN_ALGORITHMS = ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512", "PS256", "PS384", "PS512"]
# PKCE code_verifier: 43-128 chars of the unreserved set [A-Z][a-z][0-9]-._~.
# token_urlsafe(64) yields 86 chars in that alphabet, comfortably in range.
PKCE_VERIFIER_BYTES = 64
# Supported PKCE code_challenge_method values (RFC 7636 §4.2).
# "none" disables PKCE; "S256" hashes the verifier; "plain" sends the
# verifier verbatim as the challenge.
PKCE_METHODS = ("none", "S256", "plain")

# per-provider caches, invalidated when the provider row is updated
_metadata_cache: dict[int, tuple[str, dict]] = {}
_jwk_client_cache: dict[int, tuple[str, PyJWKClient]] = {}


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
        issuer = (self.config.get("issuer_url") or "").rstrip("/")
        response = requests.get(f"{issuer}/.well-known/openid-configuration", timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        metadata = response.json()
        _metadata_cache[self.provider.id] = (marker, metadata)
        return metadata

    def _endpoints(self) -> dict:
        """Resolve the endpoints for this provider (discovery for oidc, config for oauth2)."""
        if self.provider.kind == "oidc":
            metadata = self._metadata()
            return {
                "authorize": metadata["authorization_endpoint"],
                "token": metadata["token_endpoint"],
                "userinfo": metadata.get("userinfo_endpoint"),
                "jwks_uri": metadata.get("jwks_uri"),
                "issuer": metadata.get("issuer"),
            }
        return {
            "authorize": self.config.get("authorize_url"),
            "token": self.config.get("token_url"),
            "userinfo": self.config.get("userinfo_url"),
            "jwks_uri": None,
            "issuer": None,
        }

    def _scopes(self) -> str:
        """Return the configured scopes (with kind-appropriate defaults)."""
        default = "openid profile email" if self.provider.kind == "oidc" else ""
        return self.config.get("scopes") or default

    def _pkce_method(self) -> str:
        """Return the configured PKCE method (``none``, ``S256``, or ``plain``)."""
        method = (self.config.get("pkce_method") or "none").strip()
        return method if method in PKCE_METHODS else "none"

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
            else:  # "plain"
                # RFC 7636 §4.2: ``code_challenge`` IS the verifier itself.
                # Authlib only handles S256 natively, so emit the params here.
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
        """
        try:
            endpoints = self._endpoints()
            secret = self.provider.get_secret_plaintext()
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
            token = session.fetch_token(endpoints["token"], code=code, grant_type="authorization_code", **fetch_kwargs)

            claims = {}
            if self.provider.kind == "oidc":
                claims = self._verify_id_token(token.get("id_token"), endpoints, nonce)
                if claims is None:
                    return None

            username_claim = self.config.get("username_claim") or "preferred_username"
            if username_claim not in claims and endpoints["userinfo"]:
                userinfo = session.get(endpoints["userinfo"], timeout=HTTP_TIMEOUT)
                userinfo.raise_for_status()
                claims = {**userinfo.json(), **claims}

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
        marker = self._cache_marker()
        cached = _jwk_client_cache.get(self.provider.id)
        if cached and cached[0] == marker:
            jwk_client = cached[1]
        else:
            jwk_client = PyJWKClient(endpoints["jwks_uri"], timeout=HTTP_TIMEOUT)
            _jwk_client_cache[self.provider.id] = (marker, jwk_client)
        signing_key = jwk_client.get_signing_key_from_jwt(id_token)
        claims = pyjwt.decode(
            id_token,
            signing_key.key,
            algorithms=ID_TOKEN_ALGORITHMS,
            audience=self.config.get("client_id"),
            issuer=endpoints["issuer"],
            leeway=120,
        )
        if nonce and claims.get("nonce") != nonce:
            log_manager.store_auth_error_activity(f"Nonce mismatch in ID token from provider '{self.provider.name}'")
            return None
        return claims
