#!/bin/bash
# Start backend services for E2E testing
# This script starts docker compose services and waits for them to be ready

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_DIR="$PROJECT_ROOT/docker"
E2E_ENV_FILE="$COMPOSE_DIR/.env.example"

echo "Starting Taranis-NG backend services for E2E tests..."

# Start core, postgres, redis with localhost port exposure for the frontend dev server.
# Build the core image from the current workspace so new backend routes are available in E2E runs.
cd "$COMPOSE_DIR"
docker compose --env-file "$E2E_ENV_FILE" -f docker-compose.yml -f docker-compose.e2e.yml -p taranis-e2e up -d --build postgres redis core

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
  if curl -sf http://127.0.0.1:8082/api/v1/isalive > /dev/null 2>&1; then
    echo "✓ Core API is reachable on localhost:8082"
    break
  fi
  if [ $i -eq 30 ]; then
    echo "✗ Core API is not reachable on localhost:8082"
    exit 1
  fi
  sleep 1
done

echo "✓ All services ready"
