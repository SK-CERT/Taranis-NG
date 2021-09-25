from auth.base_authenticator import BaseAuthenticator
from managers import audit_manager

users = {"user": "user", "user2" : "user", "admin": "admin", "customer": "customer"}


class TestAuthenticator(BaseAuthenticator):

    def get_required_credentials(self):
        return ["username", "password"]

    def authenticate(self, credentials):
        if credentials["username"] in users:
            if users[credentials["username"]] == credentials["password"]:
                return BaseAuthenticator.generate_jwt(credentials["username"])

        audit_manager.store_auth_error_activity("Authentication failed with credentials: " + str(credentials))

        return BaseAuthenticator.generate_error()
