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

# Deploying Taranis NG with docker-compose

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

Please note it is important to use the latest version of
`docker-compose`, otherwise the build and deploy can fail.

## Quickly build and run Taranis NG using `docker-compose` or `docker compose`

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
docker-compose -f docker/docker-compose.yml pull
docker-compose -f docker/docker-compose.yml up --no-build
```
or
```bash
docker compose -f docker/docker-compose.yml pull
docker compose -f docker/docker-compose.yml up --no-build
```

or, alternatively, build and run the containers with:

```bash
TARANIS_NG_TAG=build docker-compose -f docker/docker-compose.yml build --pull
TARANIS_NG_TAG=build docker-compose -f docker/docker-compose.yml up
```
or
```bash
TARANIS_NG_TAG=build docker compose -f docker/docker-compose.yml build --pull
TARANIS_NG_TAG=build docker compose -f docker/docker-compose.yml up
```
(`--pull` updates the base images)

**Voila, Taranis NG is up and running. Visit your instance by navigating to
[https://localhost:4443/](https://localhost:4443/) using your web browser**.

**The default credentials are `user` / `user` and `admin` / `admin`.**

For initial configuration instructions, please continue to the main
[README](https://github.com/SK-CERT/Taranis-NG#connecting-to-collectors-presenters-and-publishers).

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


Taranis NG can use [connection pooling](https://docs.sqlalchemy.org/en/14/core/pooling.html) to maintain multiple active connections to the database server. Connection pooling is required when your deployment serves hundreds of customers from one instance. To enable connection pooling, set the `DB_POOL_SIZE`, `DB_POOL_RECYCLE`, and `DB_POOL_TIMEOUT` environment variables.

### `bots`, `collectors`, `presenters`, `publishers`

| Environment variable        | Description | Example |
|-----------------------------|-------------|----------|
| `TARANIS_NG_CORE_URL`       | URL of the Taranis NG core API. | `http://127.0.0.1:8080/api/v1` |

| Secrets file                | Description | Example |
|-----------------------------|-------------|----------|
| `api_key`            | Shared API key. | `supersecret` |


### `gui`

| Environment variable          | Description | Example |
|-------------------------------|-------------|----------|
| `VUE_APP_TARANIS_NG_CORE_API` | URL of the Taranis NG core API. | `http://127.0.0.1:8080/api/v1` |
| `VUE_APP_TARANIS_NG_CORE_SSE` | URL of the Taranis NG SSE endpoint. | `http://127.0.0.1:8080/sse` |
| `VUE_APP_TARANIS_NG_URL`      | URL of the Taranis NG frontend. | `http://127.0.0.1` |
| `VUE_APP_TARANIS_NG_LOCALE`   | Application locale. | `en` |
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
