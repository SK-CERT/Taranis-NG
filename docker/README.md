# TaranisNG Docker images

TaranisNG also supports deployment in Docker containers. This repository also contains an example [docker-compose.yml](docker-compose.yml) file which runs the whole application in one stack.

This folder also contains support files for the creation of the Docker containers. These include start and pre-start scripts, the application entrypoint and the gunicorn configuration file.

## Prerequisites

- [Docker](https://docs.docker.com/engine/install/)
- (Optional) [Visual Studio Code](https://code.visualstudio.com/) - for development

## Build

To build the Docker images individually, you need to clone this repository.

```bash
git clone https://gitlab.com/sk-cert/taranis-ng
```

Afterwards go to the cloned repository and launch the `docker build` command for the specific container image, like so:

```bash
cd taranis-ng
docker build -t taranis-ng-core . -f ./src/Dockerfile.core
```

There are several Dockerfiles and each of them builds a different component of the system. These Dockerfiles exist:

- [Dockerfile.bots](../src/Dockerfile.bots)
- [Dockerfile.collectors](../src/Dockerfile.collectors)
- [Dockerfile.core](../src/Dockerfile.core)
- [Dockerfile.gui](../src/Dockerfile.gui)
- [Dockerfile.presenters](../src/Dockerfile.presenters)
- [Dockerfile.publishers](../src/Dockerfile.publishers)

## Run using the example [docker-compose.yml](docker-compose.yml) file

```bash
cd taranis-ng/docker
docker-compose up --build
```
