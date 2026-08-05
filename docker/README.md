<!-- use full external links because this file is also published on Docker Hub -->

# Deploying Taranis NG with Docker

This is the canonical Docker installation guide for Taranis NG.

## Install and complete the first workflow

Follow this section from top to bottom. Installation is complete only after the
final product preview succeeds.

### Requirements

- Docker Engine with the Docker Compose v2 plugin (`docker compose`), or
  Docker Desktop on Windows and macOS
- at least 2 GB RAM, 2 CPU cores, and 5 GB free disk space
- at least 20 GB free disk space when building the images locally

### 1. Clone and prepare the configuration

```bash
git clone https://github.com/SK-CERT/Taranis-NG.git
cd Taranis-NG

cp docker/.env.example docker/.env
cp docker/secrets/postgres_password.txt.example docker/secrets/postgres_password.txt
cp docker/secrets/jwt_secret_key.txt.example docker/secrets/jwt_secret_key.txt
cp docker/secrets/api_key.txt.example docker/secrets/api_key.txt
```

Replace every example secret with an independently generated value. These
files configure PostgreSQL, JWT signing, and the shared key used between Core
and the satellite services. They do not set the passwords of Taranis NG user
accounts.

Edit `docker/.env` if you want to change the hostname, ports, timezone, or image
tag. Keep local changes in this gitignored file or in
`docker/docker-compose.override.yml`; do not edit the tracked Compose file.

### 2. Start Taranis NG

Enter the Compose directory:

```bash
cd docker
```

Use published images when the configured release tag is available:

```bash
docker compose pull
docker compose up -d --no-build
```

If that tag is not available, build the checked-out source instead:

```bash
TARANIS_NG_TAG=build docker compose up -d --build
```

Always run Compose from the `docker/` directory. Compose automatically loads
`docker-compose.override.yml` when that local file exists. If you use explicit
`-f` arguments, include every required main and override file.

### Web interfaces

The tracked Compose stack serves the Vue 2 interface at `/`. The Vue 3 source
is built for the `/v2/` base path, but its service is not enabled in the
tracked Compose definition. Use the Vue 3 development instructions for
frontend evaluation; do not expect `/v2/` to work in an unmodified deployment.

### 3. Open the application and secure the accounts

Open [https://localhost:4443/](https://localhost:4443/) unless you changed the
hostname or port.

The current password-authenticator database starts with `admin` / `admin` and
`user` / `user`. Sign in locally, change **both** passwords immediately, then
verify that the old passwords no longer work. Use `user` for normal work and
reserve `admin` for configuration.

Changing the Docker secret files does not change these database-stored account
passwords.

### 4. Confirm the included services

The Compose stack automatically registers its collector, bot, presenter, and
publisher and discovers their capabilities. Open their node pages and confirm
that all four appear. Existing nodes and their operator-selected names and
descriptions are preserved during upgrades.

### 5. Check the supplied workflows

Open these administration pages:

- **Configuration → Attributes**
- **Configuration → Report Types**
- **Configuration → Product Types**

The installation automatically supplies 26 attributes/data types, ten report
types in total, and these four distribution product types:

- `Weekly Bulletin`
- `OSINT Weekly Report`
- `Disinformation`
- `Offensive Content`

For the first workflow below, confirm that `News by Sector` and
`Weekly Bulletin` are available and that the product type is bound to the HTML
presenter and `/app/templates/weekly.html`.

### 6. Import a small source set

The repository contains an optional source catalog. For the first evaluation,
import one or both bounded definitions below rather than the aggregate catalog:

- `resources/osint/distros/ubuntu_rss.json` — Ubuntu Security Notices
- `resources/osint/software/microsoft_rss.json` — MSRC Security Update Guide

Both definitions limit a collection pass to ten links.

In **Configuration → OSINT Sources**, select **Import**, choose the included
collector node, upload one JSON file, and confirm the imported source. Repeat
for the second file if desired.

Do not import `all.json` for the first evaluation. Deleting a source can leave
previously collected news without its original source relation, so do not use
source deletion as a demo-reset mechanism.

Wait for a collection pass, then open **Assess** and confirm that collected news
appears. If it does not, inspect the collector node's capabilities and the
source's last collection status before proceeding.

### 7. Create and preview the first product

Use the normal `user` account for this workflow:

1. In **Assess**, select a collected news item and create a report item of type
   `News by Sector`.
2. Supply its sector, date, headline, and article fields, then save it.
3. Open **Publish**, create a product of type `Weekly Bulletin`, and add the
   report item.
4. Select **Preview**.

The preview should open as HTML without presenter warnings. Previewing verifies
the complete chain from collected news through report data and product type to
the bundled presenter template. It does not send the product to an external
publisher.

### 8. Confirm completion

The evaluation installation is complete when all of these are true:

- the published images were pulled, or every application image was built;
- both application-account passwords were changed and the old passwords fail;
- collector, bot, presenter, and publisher capabilities are visible;
- the official report and product types required above exist;
- at least one bounded source collected news;
- a `News by Sector` report item was saved; and
- a `Weekly Bulletin` product preview rendered successfully.

Large enrichment dictionaries and a real external publisher destination are
optional and are not required for this completion check. The separate
configuration how-to is reference material for later customization, not a
continuation of installation.

## Optional data and external publication

The first-workflow completion check does not require large enrichment downloads
or a real publication destination:

- Configure and populate a stop-word list for the language of collected
  content before evaluating tag-cloud quality.
- Import CVE, CWE, and CPE dictionaries when the related analysis fields are
  needed; they can be large and are maintained separately from the application
  schema.
- A publisher capability and a publisher preset are not the same as a working
  destination. Supply real endpoints and credentials deliberately, and test
  external side effects only when the destination is intended to receive data.

## Local TLS and custom ports

### Trusted production or managed LAN

Use a certificate trusted by every client. Keep HTTPS redirection and HSTS
enabled. Custom certificates placed in `docker/tls` must cover
`TARANIS_NG_HOSTNAME`.

### Local evaluation with an untrusted certificate

The current GUI sends a one-year HSTS header. If a browser rejects an untrusted
local certificate, add this local-only override to
`docker/docker-compose.override.yml`, adapting the ports as needed:

```yaml
services:
  traefik:
    ports: !override
      - "127.0.0.1:8080:80"
      - "127.0.0.1:4443:443"
      - "127.0.0.1:4443:443/udp"
      - "127.0.0.1:8081:9090"
  gui:
    labels:
      traefik.http.middlewares.local-disable-hsts.headers.customresponseheaders.Strict-Transport-Security: "max-age=0"
      traefik.http.routers.taranis-gui-443.middlewares: "local-disable-hsts"
```

Keep `TARANIS_NG_HOSTNAME`, `TARANIS_NG_HTTPS_PORT`, and
`TARANIS_NG_HTTPS_URI` in `.env` consistent with the chosen URL. Check the
effective bindings with `docker compose config`, then recreate the affected
services:

```bash
docker compose up -d traefik gui
```

The `!override` tag prevents the original public bindings from being merged
with the local-only bindings. Do not expose this evaluation mode publicly. A
browser that already cached the old HSTS policy may also require removal of its
stored domain-security entry.

## ACME/Let's Encrypt

ACME requires the instance to be publicly reachable. From the `docker/`
directory:

1. Copy `docker-compose.override.yml.example` to
   `docker-compose.override.yml`. If an override already exists, merge the ACME
   volume changes instead of replacing it.
2. Edit `traefik/traefik.yml` and enable the ACME configuration for the chosen
   certificate provider.
3. Restart Traefik with `docker compose restart traefik`.

Keep ACME configuration in `traefik.yml`, not in `dynamic/`. For testing, use
the provider's staging endpoint. Ensure the configured hostname resolves
publicly and the required HTTP/HTTPS ports are reachable.

For certificate authorities that require External Account Binding:

```yaml
certificatesResolvers:
  myresolver:
    acme:
      email: your-email@example.com
      storage: /letsencrypt/acme.json
      caServer: https://your-ca-server.com/acme/directory
      keyType: EC384
      eab:
        kid: your-eab-key-id
        hmacEncoded: your-eab-hmac-key
      httpChallenge:
        entryPoint: web
```

## Configuration reference

### Core

| Environment variable | Description                            | Example               |
| -------------------- | -------------------------------------- | --------------------- |
| `REDIS_URL`          | Redis database URL used for SSE events | `redis://redis`       |
| `DB_URL`             | PostgreSQL host                        | `postgres`            |
| `DB_DATABASE`        | PostgreSQL database                    | `taranis-ng`          |
| `DB_USER`            | PostgreSQL user                        | `taranis-ng`          |
| `DB_POOL_SIZE`       | Maximum active pooled connections      | `100`                 |
| `DB_POOL_RECYCLE`    | Maximum pooled-connection age          | `300`                 |
| `DB_POOL_TIMEOUT`    | Pool connection timeout                | `30`                  |
| `OPENID_LOGOUT_URL`  | OpenID/Keycloak logout URL             | provider-specific URL |
| `GUNICORN_WORKERS`   | Gunicorn worker count                  | `AUTO`                |

| Secret file             | Description                                                                           |
| ----------------------- | ------------------------------------------------------------------------------------- |
| `postgres_password.txt` | PostgreSQL password; initializes a fresh database but does not rotate an existing one |
| `jwt_secret_key.txt`    | JWT signing key; changing it invalidates existing tokens                              |
| `api_key.txt`           | Shared authentication key for Core and satellite services                             |

### Satellites

Collectors, bots, presenters, and publishers use `TARANIS_NG_CORE_URL` for the
Core endpoint and `api_key.txt` for shared authentication.

### Vue 2 GUI

| Environment variable          | Description            |
| ----------------------------- | ---------------------- |
| `VUE_APP_TARANIS_NG_CORE_API` | Core API URL           |
| `VUE_APP_TARANIS_NG_CORE_SSE` | Core SSE URL           |
| `VUE_APP_TARANIS_NG_URL`      | Public frontend URL    |
| `VUE_APP_TARANIS_NG_LOCALE`   | Default locale         |
| `NGINX_WORKERS`               | Nginx worker count     |
| `NGINX_CONNECTIONS`           | Connections per worker |

### Vue 3 GUI

The optional Vue 3 container uses `VITE_APP_TARANIS_NG_URL`,
`VITE_APP_TARANIS_NG_CORE_API`, `VITE_APP_TARANIS_NG_CORE_SSE`,
`VITE_APP_TARANIS_NG_LOCALE`, and `VITE_APP_VERSION`. Its public base path is
`/v2/`.

Locale availability differs between the interfaces. Vue 2 supports Czech
(`cs`), English (`en`), and Slovak (`sk`). Vue 3 supports Brazilian Portuguese
(`pt-BR`), Czech (`cs`), Dutch (`nl`), English (`en`), French (`fr`), German
(`de`), Hindi (`hi`), Italian (`it`), Japanese (`ja`), Korean (`ko`), Polish
(`pl`), Russian (`ru`), Simplified Chinese (`zh-CN`), Slovak (`sk`), Spanish
(`es`), Thai (`th`), Turkish (`tr`), Ukrainian (`uk`), and Vietnamese (`vi`).
English is the fallback for both interfaces.

### Redis and PostgreSQL

Redis and PostgreSQL use their standard container configuration. If Redis
warns that host memory overcommit is disabled, follow the operating system's
Redis deployment guidance before using the instance under load.

## Upgrades

Do not use the fresh-install copy commands to upgrade an existing deployment.
Preserve `.env`, all secret files, PostgreSQL data, `core_data`, presenter user
templates, and collector storage. The repository does not provide a fully
validated upgrade-and-rollback procedure, so test restoration and review
release-specific migration notes before upgrading a production instance.

## MCP companion

MCP is not bundled in this Compose stack. Install it separately and use only a
release that explicitly declares compatibility with the installed Taranis NG
version.

## Project links

- [Source code](https://github.com/SK-CERT/Taranis-NG)
- [Docker images](https://hub.docker.com/u/skcert)
- [Configuration how-to](https://github.com/SK-CERT/Taranis-NG/blob/main/docs/howto.md)
- [OSINT source catalog](https://github.com/SK-CERT/Taranis-NG/tree/main/resources/osint)
- [Issue tracker](https://github.com/SK-CERT/Taranis-NG/issues)
- Security reports: [incident@nbu.gov.sk](mailto:incident@nbu.gov.sk)
