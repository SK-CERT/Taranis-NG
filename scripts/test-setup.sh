#!/bin/bash
# Start backend services for E2E testing
# This script starts docker compose services and waits for them to be ready

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_DIR="$PROJECT_ROOT/docker"
# Dedicated E2E env file (COMPOSE_PROJECT_NAME=taranis-e2e + E2E_* host ports chosen
# to avoid production's published ports). See docker/.env.e2e for the rationale.
E2E_ENV_FILE="$COMPOSE_DIR/.env.e2e"

# Source the E2E env file so the readiness probes below can reference E2E_CORE_PORT /
# E2E_COLLECTORS_PORT / E2E_PRESENTERS_PORT / E2E_PUBLISHERS_PORT. Fall back to the
# compose defaults if the env file is missing or only partially defined (e.g. the user
# invoked the script directly without docker/.env.e2e present).
# shellcheck disable=SC1090
set -a; [ -f "$E2E_ENV_FILE" ] && . "$E2E_ENV_FILE"; set +a
: "${E2E_CORE_PORT:=8090}"
: "${E2E_COLLECTORS_PORT:=5091}"
: "${E2E_PRESENTERS_PORT:=5092}"
: "${E2E_PUBLISHERS_PORT:=5093}"
export E2E_CORE_PORT E2E_COLLECTORS_PORT E2E_PRESENTERS_PORT E2E_PUBLISHERS_PORT

echo "Starting Taranis-NG backend services for E2E tests (project=taranis-e2e, core=127.0.0.1:${E2E_CORE_PORT})..."

# Tear down any previous E2E stack AND its postgres volume before starting. The seed
# tests (00-config-seed.spec.js) create nodes/types/presets with fixed names (e.g.
# "E2E Presenters Node"), whose `name` columns are unique=True. Without a wipe the
# named postgres_data volume persists across runs, seed data accumulates, and the
# second+ run hits a UniqueViolation (IntegrityError → HTTP 500). The Vue dialog
# then shows its generic `*.nodes.error` i18n key ("Could not connect to X node."),
# which is misleading — it's a duplicate-name 500, NOT a connectivity failure.
#
# -p taranis-e2e namespaces containers, networks AND volumes under taranis-e2e_*, so
# down -v only ever wipes the E2E stack's own volumes (taranis-e2e_postgres_data etc.)
# and cannot touch a production stack's taranis-ng_* volumes.
cd "$COMPOSE_DIR"
docker compose --env-file "$E2E_ENV_FILE" -f docker-compose.yml -f docker-compose.e2e.yml -p taranis-e2e down -v --remove-orphans >/dev/null 2>&1 || true

# docker/secrets/*.txt is gitignored (developers copy the .example files). Seed any
# missing secret from its example so a fresh checkout - or a checkout predating a
# newly added secret - can boot the stack without manual steps.
for example in "$COMPOSE_DIR"/secrets/*.txt.example; do
  secret="${example%.example}"
  if [ ! -f "$secret" ]; then
    echo "Seeding missing secret $(basename "$secret") from its example"
    cp "$example" "$secret"
  fi
done

# Start core, postgres, redis with localhost port exposure for the frontend dev server.
# Build the core image from the current workspace so new backend routes are available in E2E runs.
docker compose --env-file "$E2E_ENV_FILE" -f docker-compose.yml -f docker-compose.e2e.yml -p taranis-e2e up -d --build postgres redis core collectors presenters publishers

echo "Waiting for services to be ready..."

# Wait for postgres
for i in {1..30}; do
  if docker compose --env-file "$E2E_ENV_FILE" -f docker-compose.yml -p taranis-e2e exec -T postgres pg_isready -U taranis-ng > /dev/null 2>&1; then
    echo "✓ PostgreSQL is ready"
    break
  fi
  if [ $i -eq 30 ]; then
    echo "✗ PostgreSQL failed to start"
    exit 1
  fi
  sleep 1
done

# Wait for core container health first
for i in {1..30}; do
  core_status=$(docker compose --env-file "$E2E_ENV_FILE" -f docker-compose.yml -f docker-compose.e2e.yml -p taranis-e2e ps --format json core 2>/dev/null | tr -d '\n')
  if echo "$core_status" | grep -q 'healthy'; then
    echo "✓ Core container is healthy"
    break
  fi
  if [ $i -eq 30 ]; then
    echo "✗ Core container failed to become healthy"
    exit 1
  fi
  sleep 1
done

# Verify the published localhost port is reachable for the dev frontend and Playwright
for i in {1..30}; do
  if curl -sf "http://127.0.0.1:${E2E_CORE_PORT}/api/v1/isalive" > /dev/null 2>&1; then
    echo "✓ Core API is reachable on localhost:${E2E_CORE_PORT}"
    break
  fi
  if [ $i -eq 30 ]; then
    echo "✗ Core API is not reachable on localhost:${E2E_CORE_PORT}"
    exit 1
  fi
  sleep 1
done

# Wait for collectors, presenters, and publishers HTTP services to be serving.
# Probe /api/v1/isalive (exposed to the host via docker-compose.e2e.yml ports
# collectors / presenters / publishers). An isalive 200 means the container is up AND
# the Python HTTP service is accepting connections — exactly what the seed tests need.
# We intentionally do NOT parse `docker compose ps --format json` for the "running"
# state here: that JSON's shape varies across compose versions (some emit
# `"running":true` boolean, others `"State":"running"` string), so a grep for one
# shape silently never matches on the other and the probe hangs. The isalive response
# is the source of truth and is portable.
declare -A SERVICE_PORT=( ["collectors"]="${E2E_COLLECTORS_PORT}" ["presenters"]="${E2E_PRESENTERS_PORT}" ["publishers"]="${E2E_PUBLISHERS_PORT}" )
for service in collectors presenters publishers; do
  port="${SERVICE_PORT[$service]}"
  ready=0
  for i in {1..60}; do
    # 1) The service's own HTTP must be serving on its host port-forward.
    if curl -sf "http://127.0.0.1:${port}/api/v1/isalive" > /dev/null 2>&1; then
      ready=1
    fi
    # 2) The CORE container must be able to resolve the service via Docker DNS and reach
    #    its isalive — this is the exact path add_presenters_node / add_collectors_node /
    #    add_publishers_node uses (PresentersApi(node.api_url, ...) → http://<service>).
    #    Docker's embedded DNS resolver can lag service start by a few seconds; if the
    #    seed test fires before DNS resolves, the node-add 500s with the misleading
    #    "Could not connect to <x> node." alert. Exec-ing a curl from core closes that gap.
    if [ "$ready" = "1" ]; then
      if docker compose --env-file "$E2E_ENV_FILE" -f docker-compose.yml -p taranis-e2e exec -T core curl -sf "http://${service}/api/v1/isalive" > /dev/null 2>&1; then
        echo "✓ $service is ready (isalive on :${port} AND core resolves http://${service})"
        break
      fi
      # Service serves on its own port, but core can't resolve it yet — keep waiting.
      ready=0
    fi
    if [ $i -eq 60 ]; then
      echo "✗ $service not fully ready within 60s (isalive on :${port} or core DNS resolution failed)"
      exit 1
    fi
    sleep 1
  done
done

echo "✓ All services ready"
