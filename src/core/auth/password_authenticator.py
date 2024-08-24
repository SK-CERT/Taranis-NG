"""Password authenticator module."""

from managers import log_manager
from auth.base_authenticator import BaseAuthenticator
from flask import request
from werkzeug.security import check_password_hash
from model.user import User
import time
import random


class PasswordAuthenticator(BaseAuthenticator):
    """Password authenticator class."""

    def get_required_credentials(self):
        """Return the list of required credentials for authentication.

        Returns:
           (list): Username and password.
        """
        return ["username", "password"]

    def authenticate(self, credentials):
        """Authenticate the user using a password.

        Parameters:
            credentials (dict): The user's credentials.
        Returns:
            (dict): The authentication
        """
        user = User.find(credentials["username"])
        if not user:
            hashed_password = "not-really-a-hash"
        else:
            hashed_password = user.password

        password_matches = check_password_hash(hashed_password, credentials["password"])

        if not user or not password_matches:
            data = request.get_json()
            data["password"] = log_manager.sensitive_value(data["password"])
            log_manager.store_auth_error_activity(f"Authentication failed for user: {credentials['username']}", request_data=data)
            time.sleep(random.uniform(1, 3))
            return BaseAuthenticator.generate_error()

        return BaseAuthenticator.generate_jwt(credentials["username"])
