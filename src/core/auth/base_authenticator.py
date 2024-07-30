"""This module contains the `BaseAuthenticator` class which provides the base functionality for authentication.

The `BaseAuthenticator` class defines methods for authentication, token generation, token refresh, and user logout.
"""

from flask_jwt_extended import create_access_token

from managers import log_manager
from model.token_blacklist import TokenBlacklist
from model.user import User


class BaseAuthenticator:
    """Base class for authenticators.

    This class provides the basic structure and methods for implementing an authenticator.
    Subclasses should override the methods as needed for specific authentication mechanisms.

    Methods:
        get_required_credentials: Return the required credentials for authentication.
        authenticate: Authenticate the user based on the provided credentials.
        refresh: Refresh the authentication token for the given user.
        logout: Logout the user by adding the token to the blacklist.
        initialize: Initialize the authenticator.
        generate_error: Generate an error response for authentication failure.
        generate_jwt: Generate a JSON Web Token (JWT) for the given username.
    """

    def get_required_credentials(self):
        """Return the required credentials for authentication.

        Returns:
            A list of required credentials.
        """
        return []

    def authenticate(self, credentials):
        """Authenticate the user based on the provided credentials.

        Arguments:
            credentials -- The user's credentials.

        Returns:
            The result of the authentication process.
        """
        return BaseAuthenticator.generate_error()

    def refresh(self, user):
        """Refresh the authentication token for the given user.

        Arguments:
            user -- The user object.

        Returns:
            The refreshed authentication token.
        """
        return BaseAuthenticator.generate_jwt(user.username)

    @staticmethod
    def logout(token):
        """Logout the user by adding the token to the blacklist.

        Arguments:
            token -- The token to be blacklisted.
        """
        if token is not None:
            TokenBlacklist.add(token)

    @staticmethod
    def initialize(app):
        """Initialize the authenticator.

        Arguments:
            app -- The application object.
        """
        pass

    @staticmethod
    def generate_error():
        """Generate an error response for authentication failure.

        Returns:
            A tuple containing the error message and the HTTP status code.
        """
        return {"error": "Authentication failed"}, 401

    @staticmethod
    def generate_jwt(username):
        """Generate a JSON Web Token (JWT) for the given username.

        Arguments:
            username (str): The username for which to generate the JWT.

        Returns:
            tuple: A tuple containing the generated access token and the HTTP status code.
        """
        user = User.find(username)
        if not user:
            log_manager.store_auth_error_activity(f"User does not exist after authentication: {username}")
            return BaseAuthenticator.generate_error()
        else:
            log_manager.store_user_activity(user, "LOGIN", "Successful")
            access_token = create_access_token(
                identity=user.username,
                additional_claims={
                    "id": user.id,
                    "name": user.name,
                    "organization_name": user.get_current_organization_name(),
                    "permissions": user.get_permissions(),
                },
            )

            return {"access_token": access_token}, 200
