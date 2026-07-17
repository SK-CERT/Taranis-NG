"""LDAP/Active Directory authenticator driven by a database-configured provider.

Provider ``config`` keys:
    server_url (str): LDAP server URL or host (e.g. "ldaps://ldap.example.org").
    use_tls (bool): Use TLS (LDAPS) for the connection.
    ca_cert (str): PEM CA certificate text; empty uses the system trust store.
    user_dn_template (str): Direct-bind template, e.g. "uid={username},ou=people,dc=example,dc=org".
    bind_dn (str): Service account DN for search+bind mode (password = provider secret).
    search_base (str): Search base for search+bind mode.
    search_filter (str): Search filter template, default "(uid={username})".
    username_attr (str): Attribute holding the canonical username (default "uid").
    name_attr (str): Attribute holding the display name (default "cn").

Either ``user_dn_template`` (direct bind) or ``bind_dn``+``search_base``
(search+bind) must be configured.
"""

from __future__ import annotations

import ssl
from typing import TYPE_CHECKING

from auth.base_authenticator import BaseAuthenticator, ExternalIdentity
from ldap3 import ALL, BASE, SUBTREE, Connection, Server, Tls
from ldap3.utils.conv import escape_filter_chars
from ldap3.utils.dn import escape_rdn
from managers import log_manager

if TYPE_CHECKING:
    from model.auth_provider import AuthProvider


class LDAPAuthenticator(BaseAuthenticator):
    """Authenticate users against the LDAP server configured on an auth provider."""

    def __init__(self, provider: AuthProvider) -> None:
        """Initialize the authenticator from a provider row.

        Args:
            provider (AuthProvider): The LDAP-kind provider configuration.
        """
        self.provider = provider
        self.config = provider.config or {}

    def get_required_credentials(self) -> list:
        """Get the username and the password.

        Returns:
            list: The list of required credentials.
        """
        return ["username", "password"]

    def _build_server(self) -> Server:
        """Build the ldap3 Server from the provider configuration."""
        use_tls = bool(self.config.get("use_tls", True))
        tls = None
        if use_tls:
            ca_cert = self.config.get("ca_cert") or None
            tls = Tls(ca_certs_data=ca_cert, validate=ssl.CERT_REQUIRED, version=ssl.PROTOCOL_TLSv1_2)
        return Server(self.config.get("server_url"), use_ssl=use_tls, tls=tls, get_info=ALL)

    def _fetch_entry(self, conn: Connection, dn: str) -> dict:
        """Read the user's entry attributes after a successful bind.

        Args:
            conn (Connection): A bound connection able to read the entry.
            dn (str): The user's DN.

        Returns:
            dict: The entry attributes (possibly empty).
        """
        attributes = [self.config.get("username_attr") or "uid", self.config.get("name_attr") or "cn", "mail"]
        try:
            if conn.search(dn, "(objectClass=*)", search_scope=BASE, attributes=attributes) and conn.entries:
                return conn.entries[0].entry_attributes_as_dict
        except Exception as ex:
            log_manager.store_auth_error_activity(f"LDAP attribute lookup failed for {dn}", ex)
        return {}

    def _identity_from_entry(self, login_username: str, dn: str, entry: dict) -> ExternalIdentity:
        """Build the external identity from an LDAP entry.

        Args:
            login_username (str): The username typed at login.
            dn (str): The entry DN (used as the stable external id).
            entry (dict): The entry attributes.
        """

        def first(attr: str) -> str | None:
            values = entry.get(attr) or []
            return values[0] if values else None

        username = first(self.config.get("username_attr") or "uid") or login_username
        return ExternalIdentity(
            username=username,
            external_id=dn,
            name=first(self.config.get("name_attr") or "cn"),
            email=first("mail"),
        )

    @staticmethod
    def _bind_failure_reason(conn: Connection) -> str:
        """Best-effort readable reason why ``conn.bind()`` returned False.

        ldap3 populates ``conn.last_error`` and ``conn.result`` (a dict whose
        ``description`` carries the server's LDAP result code, e.g.
        ``invalidCredentials``) when a bind is rejected. Surface both so an
        admin debugging a misconfigured provider sees what the LDAP server
        actually said instead of a bare "Authentication failed".
        """
        parts: list[str] = []
        error = getattr(conn, "last_error", None)
        if error:
            parts.append(f"last_error={error}")
        result = getattr(conn, "result", None) or {}
        if isinstance(result, dict):
            description = result.get("description")
            if description:
                parts.append(f"description={description}")
            code = result.get("result")
            if code not in (None, "", 0, "success"):
                parts.append(f"code={code}")
        return ", ".join(parts).strip() or "no error reported"

    def verify(self, credentials: dict) -> ExternalIdentity | None:
        """Try to authenticate the user against the LDAP server.

        Args:
            credentials (dict): The user's credentials.

        Returns:
            ExternalIdentity: The authenticated identity, or None on failure.
        """
        username = credentials["username"]
        password = credentials["password"]
        if not password:
            return None
        try:
            server = self._build_server()
            if self.config.get("user_dn_template"):
                return self._verify_direct_bind(server, username, password)
            if self.config.get("bind_dn") and self.config.get("search_base"):
                return self._verify_search_bind(server, username, password)
            log_manager.store_auth_error_activity(
                f"LDAP provider '{self.provider.name}' has neither user_dn_template nor bind_dn/search_base",
            )
        except Exception as ex:
            log_manager.store_auth_error_activity(f"LDAP authentication error for provider '{self.provider.name}'", ex)
        return None

    def _direct_bind_dn(self, username: str) -> str:
        r"""Build the user DN for direct bind from the configured template or base DN.

        ``user_dn_template`` may be either:
          * a full template with a ``{username}`` placeholder, e.g.
            ``uid={username},ou=people,dc=example,dc=org`` (explicit form), or
          * a plain base DN, e.g. ``ou=people,dc=example,dc=org`` (base-DN
            form), in which case the bind DN is auto-constructed as
            ``<username_attr>=<username>,<base_dn>`` using the configured
            ``username_attr`` (default ``uid``). This avoids asking the admin
            to repeat the RDN attribute they already declared in
            ``username_attr``.

        The username is escaped per RFC 4514 (ldap3 ``escape_rdn`` for the
        auto-constructed RDN, ``escape_filter_chars`` for the explicit
        ``{username}`` placeholder to preserve backward compatibility) so a
        username containing ``,`` ``+`` ``\"`` etc. cannot inject DN
        components.
        """
        template = self.config["user_dn_template"]
        if "{username}" in template:
            return template.format(username=escape_filter_chars(username))
        username_attr = self.config.get("username_attr") or "uid"
        return f"{username_attr}={escape_rdn(username)},{template}"

    def _verify_direct_bind(self, server: Server, username: str, password: str) -> ExternalIdentity | None:
        """Authenticate by binding directly with a DN built from the template."""
        dn = self._direct_bind_dn(username)
        conn = Connection(server, user=dn, password=password, read_only=True)
        if not conn.bind():
            log_manager.store_auth_error_activity(
                f"LDAP user bind failed for provider '{self.provider.name}', user '{username}' (DN: '{dn}'): "
                f"{self._bind_failure_reason(conn)}",
            )
            return None
        entry = self._fetch_entry(conn, dn)
        conn.unbind()
        return self._identity_from_entry(username, dn, entry)

    def _verify_search_bind(self, server: Server, username: str, password: str) -> ExternalIdentity | None:
        """Authenticate by finding the user with a service account, then rebinding."""
        service_conn = Connection(server, user=self.config["bind_dn"], password=self.provider.get_secret_plaintext(), read_only=True)
        if not service_conn.bind():
            log_manager.store_auth_error_activity(
                f"LDAP service bind failed for provider '{self.provider.name}' (bind_dn: '{self.config['bind_dn']}'): "
                f"{self._bind_failure_reason(service_conn)}",
            )
            return None
        search_filter = (self.config.get("search_filter") or "(uid={username})").format(username=escape_filter_chars(username))
        found = service_conn.search(
            self.config["search_base"],
            search_filter,
            search_scope=SUBTREE,
            attributes=[self.config.get("username_attr") or "uid", self.config.get("name_attr") or "cn", "mail"],
        )
        if not found or not service_conn.entries:
            log_manager.store_auth_error_activity(
                f"LDAP search matched no entries for provider '{self.provider.name}', user '{username}' "
                f"(search_base: '{self.config['search_base']}', filter: '{search_filter}')",
            )
            service_conn.unbind()
            return None
        entry = service_conn.entries[0]
        dn = entry.entry_dn
        attributes = entry.entry_attributes_as_dict
        service_conn.unbind()

        user_conn = Connection(server, user=dn, password=password, read_only=True)
        if not user_conn.bind():
            log_manager.store_auth_error_activity(
                f"LDAP user bind failed for provider '{self.provider.name}', user '{username}' (DN: '{dn}'): "
                f"{self._bind_failure_reason(user_conn)}",
            )
            return None
        user_conn.unbind()
        return self._identity_from_entry(username, dn, attributes)
