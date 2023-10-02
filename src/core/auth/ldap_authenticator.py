from managers import log_manager
from auth.base_authenticator import BaseAuthenticator
from flask import request
from ldap3 import Server, Connection, ALL, Tls
import ssl
import time
import random
import os


class LDAPAuthenticator(BaseAuthenticator):
    """Authenticates users against an LDAP server.

    Args:
        BaseAuthenticator (_type_): _description_

    Returns:
        _type_: _description_
    """

    LDAP_SERVER = os.getenv('LDAP_SERVER')
    LDAP_BASE_DN = os.getenv('LDAP_BASE_DN')
    LDAP_CA_CERT_PATH = os.getenv('LDAP_CA_CERT_PATH')
    if LDAP_CA_CERT_PATH is not None and not os.path.isfile(LDAP_CA_CERT_PATH):
        LDAP_CA_CERT_PATH = None
        log_manager.store_auth_error_activity("No LDAP CA certificate found. LDAP authentication might not work.")

    def get_required_credentials(self):
        """Gets the username and the password.

        Returns:
            _type_: _description_
        """
        return ["username", "password"]

    def authenticate(self, credentials):
        """Tries to authenticate the user against the LDAP server.

        Args:
            credentials (_type_): _description_

        Returns:
            _type_: _description_
        """
        tls = Tls(ca_certs_file=self.LDAP_CA_CERT_PATH, validate=ssl.CERT_REQUIRED, version=ssl.PROTOCOL_TLSv1_2)
        server = Server(self.LDAP_SERVER, use_ssl=True, tls=tls, get_info=ALL)
        conn = Connection(server, user=f'uid={credentials["username"]},{self.LDAP_BASE_DN}', password=credentials["password"], read_only=True)

        if not conn.bind():
            data = request.get_json()
            data["password"] = log_manager.sensitive_value(data["password"])
            log_manager.store_auth_error_activity("Authentication failed for user: " + credentials["username"], request_data=data)
            time.sleep(random.uniform(1, 3))
            return BaseAuthenticator.generate_error()

        return BaseAuthenticator.generate_jwt(credentials["username"])
