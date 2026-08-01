"""Password authenticator module."""

import random
import time
from http import HTTPStatus

from auth.base_authenticator import BaseAuthenticator
from flask import request
from managers import log_manager
from model.user import User
from werkzeug.security import check_password_hash


class PasswordAuthenticator(BaseAuthenticator):
    """Password authenticator class."""

    def get_required_credentials(self) -> list:
        """Return the list of required credentials for authentication.

        Returns:
           (list): Username and password.
        """
        return ["username", "password"]

    @staticmethod
    def verify(credentials: dict) -> User | None:
        """Verify a username/password pair against the local user database.

        Users without a stored password (externally provisioned accounts) can
        never log in with a password.

        Args:
            credentials (dict): The user's credentials.

        Returns:
            User: The matching user, or None when verification fails.
        """
        user = User.find(credentials["username"])
        hashed_password = user.password if user and user.password else "not-really-a-hash"
        if check_password_hash(hashed_password, credentials["password"]) and user and user.password:
            return user
        return None

    def authenticate(self, credentials: dict) -> tuple[dict, HTTPStatus]:
        """Authenticate the user using a password.

        Args:
            credentials (dict): The user's credentials.

        Returns:
            (dict): The authentication
        """
        user = PasswordAuthenticator.verify(credentials)

        if not user:
            data = request.get_json()
            data["password"] = log_manager.sensitive_value(data["password"])
            log_manager.store_auth_error_activity(f"Authentication failed for user: {credentials['username']}", request_data=data)
            time.sleep(random.uniform(1, 3))  # noqa: S311 - timing jitter, not cryptographic
            return BaseAuthenticator.generate_error()

        return BaseAuthenticator.generate_jwt(user)
