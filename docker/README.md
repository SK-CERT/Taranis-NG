# TaranisNG Docker images

TaranisNG also supports deployment in Docker containers. This repository also contains an example [docker-compose.yml](docker-compose.yml) file which runs the whole application in one stack.

This folder also contains support files for the creation of the Docker containers. These include start and pre-start scripts, the application entrypoint and the gunicorn configuration file.

## Prerequisites

- [Docker](https://docs.docker.com/engine/install/)
- (Optional) [Visual Studio Code](https://code.visualstudio.com/) - for development

## Build

To build the Docker images individually, you need to clone this repository.

```bash
git clone https://github.com/SK-CERT/Taranis-NG.git
```

Afterwards go to the cloned repository and launch the `docker build` command for the specific container image, like so:

```bash
cd taranis-ng
docker build -t taranis-ng-bots . -f ./docker/Dockerfile.bots
docker build -t taranis-ng-collectors . -f ./docker/Dockerfile.collectors
docker build -t taranis-ng-core . -f ./docker/Dockerfile.core
docker build -t taranis-ng-gui . -f ./docker/Dockerfile.gui
docker build -t taranis-ng-presenters . -f ./docker/Dockerfile.presenters
docker build -t taranis-ng-publishers . -f ./docker/Dockerfile.publishers
```

There are several Dockerfiles and each of them builds a different component of the system. These Dockerfiles exist:

- [Dockerfile.bots](Dockerfile.bots)
- [Dockerfile.collectors](Dockerfile.collectors)
- [Dockerfile.core](Dockerfile.core)
- [Dockerfile.gui](Dockerfile.gui)
- [Dockerfile.presenters](Dockerfile.presenters)
- [Dockerfile.publishers](Dockerfile.publishers)

## Run using the example [docker-compose.yml](docker-compose.yml) file

```bash
cd taranis-ng
docker-compose -f docker/docker-compose.yml up --build
```
