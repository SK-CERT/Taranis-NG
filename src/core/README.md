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
configuration, inspect the current configuration classes and Compose examples;
the short files under `auth/` only describe certificate placement.

## Authentication development

Password, LDAP, OpenID Connect, and Keycloak-related behavior changes over
time. Verify environment-variable names against the current source and Compose
files before testing. Changing Docker secret files does not rotate passwords
already stored for application users in PostgreSQL.

The tracked deployment serves the Vue 2 GUI. The optional Vue 3 application has
separate instructions in [`src/gui-v3/README.md`](../gui-v3/README.md); Core
development setup does not enable it.
