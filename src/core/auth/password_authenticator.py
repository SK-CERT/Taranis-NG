"""Password authenticator module."""

from auth.base_authenticator import BaseAuthenticator
from model.user import User
from werkzeug.security import check_password_hash


class PasswordAuthenticator(BaseAuthenticator):
    """Password authenticator class."""

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
