from auth.base_authenticator import BaseAuthenticator
from authlib.integrations.flask_client import OAuth

oauth = OAuth()


class OpenIDAuthenticator(BaseAuthenticator):

    @staticmethod
    def initialize(app):
        oauth.init_app(app)

    def authenticate(self, credentials):
        # oauth.twitter.authorize_redirect(redirect_uri)
        # resp = oauth.github.get('user')
        # user = resp.json()
        user = 'admin'

        if valid is True:
            return BaseAuthenticator.generate_jwt(user)

        return BaseAuthenticator.generate_error()

    @staticmethod
    def logout(token):
        BaseAuthenticator.logout(token)
