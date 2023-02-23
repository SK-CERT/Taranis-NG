from managers import log_manager
from auth.base_authenticator import BaseAuthenticator
from flask import request
from werkzeug.security import generate_password_hash, check_password_hash
from model.user import User
import time, random

class PasswordAuthenticator(BaseAuthenticator):

    def get_required_credentials(self):
        return ["username", "password"]

    def authenticate(self, credentials):
        user = User.find(credentials["username"])
        if not user:
            hashed_password = "not-really-a-hash"
        else:
            hashed_password = user.password

        password_matches = check_password_hash(hashed_password, credentials["password"])

        if not user or not password_matches:
            data = request.get_json()
            data["password"] = log_manager.sensitive_value(data["password"])
            log_manager.store_auth_error_activity("Authentication failed for user: " + credentials["username"], request_data = data)
            time.sleep(random.uniform(1, 3))
            return BaseAuthenticator.generate_error()

        return BaseAuthenticator.generate_jwt(credentials["username"])
