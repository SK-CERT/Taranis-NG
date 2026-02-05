"""This module provides an LDAPAuthenticator class that authenticates users against an LDAP server.

Attributes:
    LDAP_SERVER (str): The LDAP server URL.
    LDAP_BASE_DN (str): The base DN (Distinguished Name) for LDAP queries.
    LDAP_CA_CERT_PATH (str): The file path to the LDAP CA certificate.

Classes:
    LDAPAuthenticator: Authenticates users against an LDAP server.

"""

import os
import random
import ssl
import time

from auth.base_authenticator import BaseAuthenticator
from flask import request
from ldap3 import ALL, Connection, Server, Tls
from managers import log_manager


class LDAPAuthenticator(BaseAuthenticator):
    """Authenticate users against an LDAP server.

    Attributes:
        BaseAuthenticator (class): The base authenticator class.
    """

    def __init__(self):
        """Initialize the LDAPAuthenticator class."""
        self.LDAP_SERVER = os.getenv("LDAP_SERVER")
        self.LDAP_BASE_DN = os.getenv("LDAP_BASE_DN")
        # Check if the LDAP CA certificate path is set in the environment variables or the certificate is in the default path
        # Custom path
        if os.getenv("LDAP_CA_CERT_PATH") not in [None, ""]:
            self.LDAP_CA_CERT_PATH = os.getenv("LDAP_CA_CERT_PATH")
        # Default path
        elif os.path.isfile("auth/ldap_ca.pem"):
            self.LDAP_CA_CERT_PATH = "auth/ldap_ca.pem"
        # No path and authentication method is LDAP
        elif os.getenv("TARANIS_NG_AUTHENTICATOR").casefold() == "ldap":
            log_manager.store_auth_error_activity("No LDAP CA certificate found. LDAP authentication might not work.")

    def get_required_credentials(self):
        """Get the username and the password.

        Returns:
            list: The list of required credentials.
        """
        return ["username", "password"]

    def authenticate(self, credentials):
        """Try to authenticate the user against the LDAP server.

        Args:
            credentials (dict): The user's credentials.

        Returns:
            dict: The authentication result.
        """
        tls = Tls(ca_certs_file=self.LDAP_CA_CERT_PATH, validate=ssl.CERT_REQUIRED, version=ssl.PROTOCOL_TLSv1_2)
        server = Server(self.LDAP_SERVER, use_ssl=True, tls=tls, get_info=ALL)
        conn = Connection(server, user=f"uid={credentials['username']},{self.LDAP_BASE_DN}", password=credentials["password"], read_only=True)

        if not conn.bind():
            data = request.get_json()
            data["password"] = log_manager.sensitive_value(data["password"])
            log_manager.store_auth_error_activity(f"Authentication failed for user: {credentials['username']}", request_data=data)
            time.sleep(random.uniform(1, 3))
            return BaseAuthenticator.generate_error()

        return BaseAuthenticator.generate_jwt(credentials["username"])
