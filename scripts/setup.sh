#!/usr/bin/env bash
# =============================================================================
# VeriUnlearn — one-command setup
# Brings up the full stack (core services) and waits until it is healthy.
# Usage: ./scripts/setup.sh [--with-monitoring] [--seed] [--no-build]
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE_FILE="docker-compose.yml"
PROFILE_ARGS=()
SEED=0
NO_BUILD=0

for arg in "$@"; do
  case "$arg" in
    --with-monitoring) PROFILE_ARGS=(--profile monitoring) ;;
    --seed) SEED=1 ;;
    --no-build) NO_BUILD=1 ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "Unknown argument: $arg" >&2; exit 1 ;;
  esac
done

echo "==> VeriUnlearn setup"
echo "    Root: $ROOT_DIR"

# ─── Prerequisites ────────────────────────────────────────────────────────
command -v docker >/dev/null 2>&1 || { echo "✗ docker is required but not installed. See https://docs.docker.com/get-docker/"; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "✗ docker compose (v2) is required but not available."; exit 1; }

# ─── Environment file ─────────────────────────────────────────────────────
if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    cp .env.example .env
    echo "==> Created .env from .env.example (review and adjust secrets for production)."
  else
    echo "✗ .env.example not found; cannot bootstrap environment." >&2
    exit 1
  fi
fi

# ─── Start services ───────────────────────────────────────────────────────
echo "==> Starting VeriUnlearn stack (this may take a few minutes on first pull)..."
if [ "$NO_BUILD" -eq 1 ]; then
  docker compose "${PROFILE_ARGS[@]}" up -d
else
  docker compose "${PROFILE_ARGS[@]}" up -d --build
fi

# ─── Wait for backend health ──────────────────────────────────────────────
echo "==> Waiting for backend to become healthy..."
HEALTH_URL="http://localhost:${BACKEND_PORT:-8000}/health"
for i in $(seq 1 60); do
  if curl -fs "$HEALTH_URL" >/dev/null 2>&1; then
    echo "==> Backend is healthy."
    break
  fi
  if [ "$i" -eq 60 ]; then
    echo "✗ Backend did not become healthy within 5 minutes. Check logs: docker compose logs backend" >&2
    exit 1
  fi
  sleep 5
done

# ─── Optional demo data ───────────────────────────────────────────────────
if [ "$SEED" -eq 1 ]; then
  echo "==> Seeding demo data..."
  if [ -f infra/scripts/seed_demo_data.py ]; then
    python infra/scripts/seed_demo_data.py --api-url "http://localhost:${BACKEND_PORT:-8000}/api/v1" \
      || echo "⚠ Seeding failed (is the API reachable and migrated?). Run 'make seed' later."
  else
    echo "⚠ seed script not found; skipping."
  fi
fi

# ─── Summary ──────────────────────────────────────────────────────────────
FRONTEND="http://localhost:${FRONTEND_PORT:-3000}"
BACKEND="http://localhost:${BACKEND_PORT:-8000}"
echo ""
echo "✅ VeriUnlearn is up!"
echo "   Frontend : $FRONTEND"
echo "   API      : $BACKEND/docs"
echo "   Health   : $BACKEND/health"
if [ "${#PROFILE_ARGS[@]}" -gt 0 ]; then
  echo "   Grafana  : http://localhost:${GRAFANA_PORT:-3001}  (admin / see GRAFANA_ADMIN_PASSWORD in .env)"
  echo "   Prometheus: http://localhost:${PROMETHEUS_PORT:-9090}"
fi
echo ""
echo "   Tear down with: ./scripts/teardown.sh"
