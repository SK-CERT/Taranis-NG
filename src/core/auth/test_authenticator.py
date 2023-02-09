from managers import log_manager
from auth.base_authenticator import BaseAuthenticator
from flask import request

users = {"user": "user", "user2" : "user", "admin": "admin", "customer": "customer"}


class TestAuthenticator(BaseAuthenticator):

    def get_required_credentials(self):
        return ["username", "password"]

    def authenticate(self, credentials):
        if credentials["username"] in users:
            if users[credentials["username"]] == credentials["password"]:
                return BaseAuthenticator.generate_jwt(credentials["username"])

        data = request.get_json()
        data["password"] = log_manager.sensitive_value(data["password"])
        log_manager.store_auth_error_activity("Authentication failed for user: " + credentials["username"], request_data = data)

        return BaseAuthenticator.generate_error()
