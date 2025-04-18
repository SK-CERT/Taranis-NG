"""BaseAuthenticator class provides methods for handling authentication processes."""

from flask_jwt_extended import create_access_token

from managers import log_manager
from model.token_blacklist import TokenBlacklist
from model.user import User


class BaseAuthenticator:
    """BaseAuthenticator class provides methods for handling authentication processes."""

    def get_required_credentials(self):
        """Retrieve the list of required credentials for authentication.

        Returns:
            list: An empty list indicating no credentials are required.
        """
        return []

    def authenticate(self, credentials):
        """Authenticate the provided credentials.

        Args:
            credentials (dict): A dictionary containing authentication credentials.
        Returns:
            dict: An error response generated by the BaseAuthenticator.
        """
        return BaseAuthenticator.generate_error()

    def refresh(self, user):
        """Refresh the JWT token for the given user.

        Args:
            user (User): The user object for which the JWT token needs to be refreshed.
        Returns:
            str: A new JWT token generated for the user's username.
        """
        return BaseAuthenticator.generate_jwt(user.username)

    @staticmethod
    def logout(token):
        """Log out a user by adding their token to the blacklist.

        Args:
            token (str): The token to be blacklisted. If None, no action is taken.
        """
        if token is not None:
            TokenBlacklist.add(token)

    @staticmethod
    def initialize(app):
        """Initialize the authenticator with the given application.

        Args:
            app: The application instance to initialize the authenticator with.
        """
        pass

    @staticmethod
    def generate_error():
        """Generate an error response for authentication failure.

        Returns:
            tuple: A dictionary containing the error message and the HTTP status code 401.
        """
        return {"error": "Authentication failed"}, 401

    @staticmethod
    def generate_jwt(username):
        """Generate a JSON Web Token (JWT) for a given username.

        This function retrieves the user associated with the provided username,
        logs the authentication activity, and generates a JWT containing user
        information and permissions if the user exists. If the user does not
        exist, it logs an error and returns an error response.
        Args:
            username (str): The username of the user for whom the JWT is to be generated.
        Returns:
            tuple: A tuple containing a dictionary with the access token and an HTTP status code.
                   If the user does not exist, returns an error response.
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
                    "user_claims": {
                        "id": user.id,
                        "name": user.name,
                        "organization_name": user.get_current_organization_name(),
                        "permissions": user.get_permissions(),
                    }
                },
            )

            return {"access_token": access_token}, 200
