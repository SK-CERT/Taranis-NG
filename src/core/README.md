# Taranis NG Core

**Audience:** Core developers.

**Status:** component-development notes, not an installation guide.

Use the repository's [Docker deployment guide](../../docker/README.md) for a
complete Taranis NG deployment. Core cannot provide an end-to-end installation
on its own: the application also depends on PostgreSQL, Redis, the GUI, and the
configured satellite services.

Do not use test-module imports or sample-data hooks to initialize report forms,
product types, templates, sources, or collector configuration. Use migrations,
bootstrap data, and the supported application APIs.

## Local Core development

The authoritative dependency and Python-version constraints are in the root
`pyproject.toml` and lockfile. Use the repository's current dependency tooling
rather than copying version numbers from this README.

Core requires at least:

- a reachable PostgreSQL database;
- the configured database name and user;
- `postgres_password`, `jwt_secret_key`, and `api_key` secret files;
- a Redis endpoint for server-sent events; and
- database migrations before serving requests.

Use the Core service definition in `docker/docker-compose.yml` as the current
configuration reference. Never use example values such as `12345`,
`admin/admin`, or `user/user` outside an isolated disposable environment.

For account, role, node, API-key, and dictionary management, see the
[management command reference](../../docs/howto.md#_toc5). For authentication
configuration, see [`auth/README.md`](auth/README.md).

## Authentication development

Login methods (local accounts, LDAP, OpenID Connect, OAuth 2.0, SAML) are
database auth providers configured in the GUI under *Access Management →
Login Methods*; no environment variable selects them. Changing Docker secret
files does not rotate passwords already stored for application users in
PostgreSQL.

The GUI has separate development instructions in
[`src/gui/README.md`](../gui/README.md).
