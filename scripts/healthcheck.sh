#!/usr/bin/env bash
# =============================================================================
# VeriUnlearn — health check
# Probes every service endpoint and exits 0 only if all are healthy.
# Usage: ./scripts/healthcheck.sh
# =============================================================================
set -uo pipefail

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
ML_ENGINE_PORT="${ML_ENGINE_PORT:-8001}"

check() {
  local name="$1" url="$2"
  if curl -fs --max-time 5 "$url" >/dev/null 2>&1; then
    printf "  [OK]   %-14s %s\n" "$name" "$url"
    return 0
  else
    printf "  [FAIL] %-14s %s\n" "$name" "$url"
    return 1
  fi
}

echo "==> VeriUnlearn health check"
fail=0
check "backend"    "http://localhost:${BACKEND_PORT}/health"      || fail=1
check "ml-engine"  "http://localhost:${ML_ENGINE_PORT}/health"    || fail=1
check "frontend"   "http://localhost:${FRONTEND_PORT}"            || fail=1

# Compose-level container health (postgres/redis/minio/qdrant)
if command -v docker >/dev/null 2>&1; then
  echo "==> Container status"
  docker compose ps --format 'table {{.Name}}\t{{.Status}}' || true
fi

if [ "$fail" -ne 0 ]; then
  echo "✗ One or more services are unhealthy."
  exit 1
fi
echo "✅ All probed services are healthy."
