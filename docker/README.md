<!-- use whole link on github files becasue this .md is also on https://hub.docker.com -->

# Quick reference

- Source code: [github.com/SK-CERT/Taranis-NG](https://github.com/SK-CERT/Taranis-NG)
- Docker images: [hub.docker.com/u/skcert](https://hub.docker.com/u/skcert)
- Maintained by: [SK-CERT](https://www.sk-cert.sk)
- Project web page: [taranis.ng](https://taranis.ng)
- Where to file issues (no vulnerability reports please): [GitHub issues page](https://github.com/SK-CERT/Taranis-NG/issues)
- Where to send security issues and vulnerability reports: [incident@nbu.gov.sk](mailto:incident@nbu.gov.sk)

## What is Taranis NG?

Taranis NG is an OSINT gathering and analysis tool for CSIRT teams and
organisations. It allows osint gathering, analysis and reporting; team-to-team
collaboration; and contains a user portal for simple self asset management.

Taranis crawls various **data sources** such as web sites or tweets to gather
unstructured **news items**. These are processed by analysts to create
structured **report items**, which are used to create **products** such as PDF
files, which are finally **published**.

Taranis supports **team-to-team collaboration**, and includes a light weight
**self service asset management** which automatically links to the advisories
that mention vulnerabilities in the software.

# Deploying Taranis NG with Docker

Taranis NG supports deployment in Docker containers. [The docker/ folder on
GitHub repository](https://github.com/SK-CERT/Taranis-NG/tree/main/docker)
contains a sample
[docker-compose.yml](https://raw.githubusercontent.com/SK-CERT/Taranis-NG/main/docker/docker-compose.yml)
file which runs the whole application in one stack.

The same folder also contains additional support files for the creation of the
Docker containers. These include start and pre-start scripts, the application
entrypoint, and the [gunicorn](https://gunicorn.org/) configuration file.

## Prerequisites

- [Docker](https://docs.docker.com/engine/install/) and [docker-compose](https://docs.docker.com/compose/install/)
- [Docker Desktop](https://docs.docker.com/desktop/) for Windows and macOS users
- (Optional) [Vim](https://www.vim.org/) or other text editor - for configuration and development
- (Optional) [Notepad++](https://notepad-plus-plus.org/) text editor for Windows users

Please note it is important to use the latest version of Docker, otherwise the build and deploy can fail.

## Quickly build and run Taranis NG using `docker compose`

_First_, you need to clone the source code repository:

```bash
git clone https://github.com/SK-CERT/Taranis-NG.git
cd Taranis-NG
```

_Then_, remove `.example` extension from file `docker/.env.example` and files in `docker/secrets`. Use your favorite text editor and change default passwords. Taranis NG uses [Docker secrets](https://docs.docker.com/compose/use-secrets/) to store sensitive data. (Saving passwords in variables defined in `docker/.env` is not advised and you will need to modify Docker compose YAML files to make it work correctly.

```bash
vim docker/.env
```

*_Optionally:_ you may modify other settings in the `docker/.env` and `docker/docker-compose.yml` files to your liking.  More information on container configuration can be found [here](#configuration).*

_Finally_, either deploy the ready-made images from Docker hub with:

```bash
cd Taranis-NG/docker
docker compose pull
docker compose up --no-build
```

or, alternatively, build and run the containers with:

```bash
cd Taranis-NG/docker
TARANIS_NG_TAG=build docker compose build --pull
TARANIS_NG_TAG=build docker compose up
```

**Important:** If you have `docker-compose.override.yml` configured (for ACME), the override file is automatically loaded when running from the docker/ directory. Do NOT use explicit `-f docker-compose.yml` flags as this disables automatic override loading.

(`--pull` updates the base images)

**Voila, Taranis NG is up and running. Visit your instance by navigating to
[https://localhost:4443/](https://localhost:4443/) using your web browser**.

**The default credentials are `user` / `user` and `admin` / `admin`.**

For initial configuration instructions, please continue to the main
[README](https://github.com/SK-CERT/Taranis-NG#connecting-to-collectors-presenters-and-publishers).

## Enabling ACME for automatic HTTPS certificates

Taranis NG gets certificates from any ACME certificate authority. This requires your instance to be publicly accessible on the internet, with port 80 open for the HTTP-01 challenge.

**Step 1:** Copy the CA templates and uncomment the block for the authority you use:

```bash
cd docker
cp acme.env.example acme.env
```

`acme.env` is gitignored, so the account e-mail and any EAB credentials stay out of git. Each block defines one *resolver*; the name is yours to choose and is what everything else refers to. Several may be defined at once.

**Step 2:** Set `TRAEFIK_CERT_RESOLVER` in `docker/.env` to that name, e.g. `letsencrypt`. That one variable puts the resolver on every router: the main hostname (GUI, API, SSE) and each public web. A public web can use a different one — set *ACME certificate resolver* in its dialog under *Configuration → Public Web*.

**Step 3:** Recreate Traefik — this is static configuration, read once at startup:

```bash
docker compose up -d traefik
```

Check it worked in the GUI, under *Configuration → Application Settings → Routing & TLS*: the certificate panel lists every hostname with the certificate actually being served, its issuer and expiry. `docker compose logs traefik | grep -i "certificate resolver"` should also be silent — "Router uses a nonexistent certificate resolver" means `TRAEFIK_CERT_RESOLVER` names a resolver `acme.env` does not define.

**Choosing a CA:**
- **Let's Encrypt** needs no External Account Binding and validates any domain that passes the challenge. Test against its staging server first — untrusted certificates, but forgiving rate limits
- **Other CAs** need their own directory URL, and most commercial ones need External Account Binding credentials from your account. Many also expect the domain to be authorised on the account beforehand — such a CA rejects the order outright rather than failing the challenge, and the Traefik log carries the CA's own message

**Changing CA:** add a **new resolver** under a new name and point `TRAEFIK_CERT_RESOLVER` at it. Do not repoint an existing resolver — an ACME account is bound to the CA that registered it, so the stored account would be meaningless to the new CA. A new name gets its own account, leaves the previous certificates in `acme.json` untouched, and is undone by putting the variable back.

**Important notes:**
- **Do not create a `docker/traefik/traefik.yml`.** Traefik takes its static configuration from exactly one source, in the order file → command-line flags → environment variables, and whichever wins makes the others invisible without any warning. Only `traefik/dynamic/` is mounted, so the `TRAEFIK_*` variables are the single source. A static config file would silently disable all of them, and the first symptom is every router serving the self-signed certificate
- The non-secret Traefik settings — entrypoints, providers, logging, dashboard — live in `docker-compose.yml`, so upgrades reach your deployment on a pull
- Changes only take effect at the **next** issuance. Traefik does not re-issue a hostname that already holds a valid certificate — neither for a new `keyType` nor for a switch to a different resolver — it logs `No ACME certificate generation required for domains`. The renewal date in the certificate panel is when a change lands; to force it sooner, remove that domain's entry from `acme.json` in the `acme_storage` volume and recreate Traefik
- Ensure `TARANIS_NG_HOSTNAME` is publicly reachable and ports 80/443 are open. Each public web needs its own DNS record pointing here
- Certificates live in the `acme_storage` volume and survive a recreate
- A hostname that needs to bypass ACME entirely can carry its own certificate: paste the PEM pair into that web's dialog, or set an instance-wide default under *Routing & TLS*
- Turn on HSTS only *after* certificates are being issued. It is in the GUI under *Routing & TLS* — Traefik sends it, since it terminates TLS. HSTS makes a certificate error impossible to click through for the whole `max-age`, so enabling it while still on the self-signed certificate locks browsers out. Turning it back off sends `max-age=0`, which releases browsers already pinned

## Advanced build methods

### Individually build the containers

To build the Docker images individually, you need to clone the source code repository.

```bash
git clone https://github.com/SK-CERT/Taranis-NG.git
```

Afterwards go to the cloned repository and launch the `docker build` command for the specific container image, like so:

```bash
cd Taranis-NG
docker build -t taranis-ng-bots . -f ./docker/Dockerfile.bots
docker build -t taranis-ng-collectors . -f ./docker/Dockerfile.collectors
docker build -t taranis-ng-core . -f ./docker/Dockerfile.core
docker build -t taranis-ng-gui . -f ./docker/Dockerfile.gui
docker build -t taranis-ng-presenters . -f ./docker/Dockerfile.presenters
docker build -t taranis-ng-publishers . -f ./docker/Dockerfile.publishers
```

# Container variables configuration

### `core`

| Environment variable        | Description | Example |
|-----------------------------|-------------|----------|
| `REDIS_URL`                 | Redis database URL. Used for SSE events. | `redis://redis` |
| `DB_URL`                    | PostgreSQL database URL. | `127.0.0.1` |
| `DB_DATABASE`               | PostgreSQL database name. | `taranis-ng` |
| `DB_USER`                   | PostgreSQL database user. | `taranis-ng` |
| `DB_POOL_SIZE`              | SQLAlchemy QueuePool number of active connections to the database. | `100` |
| `DB_POOL_RECYCLE`           | SQLAlchemy QueuePool maximum connection age. | `300` |
| `DB_POOL_TIMEOUT`           | SQLAlchemy QueuePool connection timeout. | `5` |
| `OPENID_LOGOUT_URL`         | Keycloak logout URL. | `https://example.com/realms/master/protocol/openid-connect/logout` |
| `GUNICORN_WORKERS`          | Number of Gunicorn worker threads. | `AUTO`, `8` |

| Secrets file                | Description | Example |
|-----------------------------|-------------|----------|
| `postgres_password`         | PostgreSQL database password. | `supersecret` |
| `jwt_secret_key`            | JWT token secret key. | `supersecret` |
| `secrets_encryption_key`    | Key used to encrypt secrets stored in the database (auth provider client secrets, LDAP bind passwords, TOTP seeds). Falls back to `jwt_secret_key` when missing; a dedicated key is recommended. Changing the key requires re-entering provider secrets and re-enrolling TOTP. | `supersecretkeyminimal32byteslong` |


Taranis NG can use [connection pooling](https://docs.sqlalchemy.org/en/14/core/pooling.html) to maintain multiple active connections to the database server. Connection pooling is required when your deployment serves hundreds of customers from one instance. To enable connection pooling, set the `DB_POOL_SIZE`, `DB_POOL_RECYCLE`, and `DB_POOL_TIMEOUT` environment variables.

### `bots`, `collectors`, `presenters`, `publishers`

| Environment variable        | Description | Example |
|-----------------------------|-------------|----------|
| `TARANIS_NG_CORE_URL`       | URL of the Taranis NG core API. | `http://127.0.0.1:8080/api/v1` |

| Secrets file                | Description | Example |
|-----------------------------|-------------|----------|
| `api_key`            | Shared API key. | `supersecret` |


### `gui`

| Environment variable            | Description | Example |
|---------------------------------|-------------|----------|
| `VITE_APP_TARANIS_NG_CORE_API` | URL of the Taranis NG core API. | `http://127.0.0.1:8080/api/v1` |
| `VITE_APP_TARANIS_NG_CORE_SSE` | URL of the Taranis NG SSE endpoint. | `http://127.0.0.1:8080/sse` |
| `VITE_APP_TARANIS_NG_URL`      | URL of the Taranis NG frontend. | `http://127.0.0.1` |
| `VITE_APP_TARANIS_NG_LOCALE`   | Application locale. | `en` |
| `NGINX_WORKERS`               | Number of NginX worker threads to spawn. | `4` |
| `NGINX_CONNECTIONS`           | Maximum number of allowed connections per one worker thread. | `16` |

### `redis`
Any configuration options are available at [https://hub.docker.com/_/redis](https://hub.docker.com/_/redis).

If you see in logs this message:
```
redis-1       | 1:C 07 Jan 2025 08:35:21.560 # WARNING Memory overcommit must be enabled! Without it, a background save or replication may fail under low memory condition. Being disabled, it can also cause failures without low memory condition, see https://github.com/jemalloc/jemalloc/issues/1328. To fix this issue add 'vm.overcommit_memory = 1' to /etc/sysctl.conf and then reboot or run the command 'sysctl vm.overcommit_memory=1' for this to take effect.
```
Run following in your host OS:
```bash
sysctl -w vm.overcommit_memory=1
```

### `database`
Any configuration options are available at [https://hub.docker.com/_/postgres](https://hub.docker.com/_/postgres).

## Learn more...

Main documentation can be found in the [README](https://github.com/SK-CERT/Taranis-NG/blob/main/README.md), which includes basic information and initial setup instructions.

For instructions on configuring other components, refer to the [How to guide](https://github.com/SK-CERT/Taranis-NG/blob/main/docs/howto.md).
