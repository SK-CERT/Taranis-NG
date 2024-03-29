from flask_jwt_extended import create_access_token

from managers import log_manager
from model.token_blacklist import TokenBlacklist
from model.user import User


class BaseAuthenticator:

    def get_required_credentials(self):
        return []

    def authenticate(self, credentials):
        return BaseAuthenticator.generate_error()

    def refresh(self, user):
        return BaseAuthenticator.generate_jwt(user.username)

    @staticmethod
    def logout(token):
        if token is not None:
            TokenBlacklist.add(token)

    @staticmethod
    def initialize(app):
        pass

    @staticmethod
    def generate_error():
        return {'error': 'Authentication failed'}, 401

    @staticmethod
    def generate_jwt(username):

        user = User.find(username)
        if not user:
            log_manager.store_auth_error_activity("User does not exist after authentication: " + username)
            return BaseAuthenticator.generate_error()
        else:
            log_manager.store_user_activity(user, "LOGIN", "Successful")
            access_token = create_access_token(identity=user.username,
                                               user_claims={'id': user.id,
                                                            'name': user.name,
                                                            'organization_name': user.get_current_organization_name(),
                                                            'permissions': user.get_permissions()})

            return {'access_token': access_token}, 200
