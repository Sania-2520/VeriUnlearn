#!/usr/bin/env bash
# =============================================================================
# VeriUnlearn — one-command teardown
# Stops and removes all VeriUnlearn containers, networks, and (optionally)
# persisted volumes.
# Usage: ./scripts/teardown.sh [--volumes] [--all]
#   --volumes   also remove named data volumes (DESTROYS data)
#   --all       remove images too
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

REMOVE_VOLUMES=0
REMOVE_IMAGES=0

for arg in "$@"; do
  case "$arg" in
    --volumes) REMOVE_VOLUMES=1 ;;
    --all) REMOVE_VOLUMES=1; REMOVE_IMAGES=1 ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown argument: $arg" >&2; exit 1 ;;
  esac
done

echo "==> Stopping VeriUnlearn stack..."
docker compose down

if [ "$REMOVE_VOLUMES" -eq 1 ]; then
  echo "==> Removing data volumes (this DESTROYS all persisted data)..."
  docker compose down --volumes
fi

if [ "$REMOVE_IMAGES" -eq 1 ]; then
  echo "==> Removing VeriUnlearn images..."
  docker images --format '{{.Repository}}:{{.Tag}}' | grep -E 'veriunlearn|(ghcr.io/)?veriunlearn' | xargs -r docker rmi -f || true
fi

# Stop monitoring profile services if they were started separately
docker compose --profile monitoring down ${REMOVE_VOLUMES:+"--volumes"} || true

echo "✅ Teardown complete."
