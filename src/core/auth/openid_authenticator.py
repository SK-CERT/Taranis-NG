"""OpenID Connect authenticator using `flask_oidc`."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from http import HTTPStatus

    import Flask

from auth.base_authenticator import BaseAuthenticator
from flask_oidc import OpenIDConnect

oidc = OpenIDConnect()


class OpenIDAuthenticator(BaseAuthenticator):
    """Authenticator that uses OpenID Connect via `flask_oidc`.

    The class wraps `flask_oidc` helpers and adapts them to the
    application's `BaseAuthenticator` interface.
    """

    @staticmethod
    def initialize(app: Flask) -> None:
        """Initialize flask-oidc with the Flask app.

        Args:
            app: The Flask application instance.

        Returns:
            None
        """
        oidc.init_app(app)

    @oidc.require_login
    def authenticate(self, credentials: dict) -> tuple[dict, HTTPStatus]:  # noqa: ARG002
        """Authenticate the current OIDC session and return a JWT.

        Args:
            credentials: Unused parameter kept for interface compatibility.

        Returns:
            A generated JWT on successful validation, otherwise an error
            payload from `BaseAuthenticator.generate_error()`.
        """
        access_token = oidc.get_access_token()
        valid = oidc.validate_token(access_token)

        if valid is True:
            return BaseAuthenticator.generate_jwt(oidc.user_getfield("preferred_username"))

        return BaseAuthenticator.generate_error()

    @staticmethod
    def logout(jwt_id: str) -> None:
        """Revoke local JWT state and perform OIDC logout.

        Args:
            jwt_id: The JWT identifier to revoke locally.

        Returns:
            None
        """
        BaseAuthenticator.logout(jwt_id)
        oidc.logout()
