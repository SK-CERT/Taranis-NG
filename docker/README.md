# Taranis NG Docker images

Taranis NG supports deployment in Docker containers. This repository also contains an example [docker-compose.yml](docker-compose.yml) file which runs the whole application in one stack.

This folder contains additional support files for the creation of the Docker containers. These include start and pre-start scripts, the application entrypoint and the gunicorn configuration file.

## Prerequisites

- [Docker](https://docs.docker.com/engine/install/)
- (Optional) [Visual Studio Code](https://code.visualstudio.com/) - for development

## Quickly build and run using [docker-compose.yml](docker-compose.yml)

To build and deploy the Docker images using docker-compose, you need to clone this repository:

```bash
git clone https://github.com/SK-CERT/Taranis-NG.git
cd Taranis-NG
```

Optionally, modify the `docker/docker-compose.yml` file to your liking.

Finally, run the containers with:

```bash
# either run empty instance
docker-compose --build -f docker/docker-compose.yml up

# or automatically populate with sample data
docker-compose --build -f docker/docker-compose.yml -f docker/docker-sample-data.yml up
```

Voila, Taranis NG is up and running. Visit your instance by navigating to [http://127.0.0.1:8080/](http://127.0.0.1:8080/) using your web browser. If you have imported the sample data, the default credentials are `user` / `user` and `admin` / `admin`.

## Advanced methods

### Individually build the containers

To build the Docker images individually, you need to clone this repository.

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

There are several Dockerfiles and each of them builds a different component of the system. These Dockerfiles exist:

- [Dockerfile.bots](Dockerfile.bots)
- [Dockerfile.collectors](Dockerfile.collectors)
- [Dockerfile.core](Dockerfile.core)
- [Dockerfile.gui](Dockerfile.gui)
- [Dockerfile.presenters](Dockerfile.presenters)
- [Dockerfile.publishers](Dockerfile.publishers)

