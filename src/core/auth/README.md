# LDAP CA certificate location

**Audience:** Core developers and operators using LDAP authentication.

**Scope:** certificate placement only, not complete LDAP configuration.

Place the CA certificate used to validate the LDAP server in this directory and
name it `ldap_ca.pem`, or configure the current Core/Compose certificate path
explicitly. Keep private credentials out of this directory and out of version
control.

See the current configuration source and Compose environment for the LDAP
server and base-DN settings. This certificate does not configure user mapping,
rotate application passwords, or establish that LDAP login is working.
