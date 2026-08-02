#!/usr/bin/env bash
# =============================================================================
# VeriUnlearn — backup
# Creates timestamped backups of PostgreSQL, Redis, MinIO, Qdrant, and the
# backend/ml-engine app-data volumes.
# Usage: ./scripts/backup.sh [--out DIR]
# Output: ./backups/veriunlearn-YYYYMMDD-HHMMSS/{postgres.sql,minio/,qdrant/,redis.tgz,appdata/}
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

OUT_DIR="./backups"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --out) OUT_DIR="$2"; shift 2 ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

TS="$(date +%Y%m%d-%H%M%S)"
DEST="$OUT_DIR/veriunlearn-$TS"
mkdir -p "$DEST"

POSTGRES_USER="${POSTGRES_USER:-veriunlearn}"
POSTGRES_DB="${POSTGRES_DB:-veriunlearn}"
POSTGRES_CONTAINER="$(docker compose ps -q postgres | head -n1)"

if [ -z "$POSTGRES_CONTAINER" ]; then
  echo "✗ postgres container not running. Start the stack first (./scripts/setup.sh)." >&2
  exit 1
fi

echo "==> Backing up PostgreSQL -> $DEST/postgres.sql"
docker exec "$POSTGRES_CONTAINER" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$DEST/postgres.dump" \
  && echo "    (custom-format dump written)"

echo "==> Backing up MinIO -> $DEST/minio"
MINIO_CONTAINER="$(docker compose ps -q minio | head -n1)"
if [ -n "$MINIO_CONTAINER" ]; then
  docker exec "$MINIO_CONTAINER" sh -c 'mc alias set local http://localhost:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null 2>&1; mc mirror local /backup' \
    || docker cp "$MINIO_CONTAINER":/data "$DEST/minio" || echo "⚠ MinIO backup skipped (mc not available)."
fi

echo "==> Backing up Qdrant -> $DEST/qdrant"
QDRANT_CONTAINER="$(docker compose ps -q qdrant | head -n1)"
if [ -n "$QDRANT_CONTAINER" ]; then
  docker exec "$QDRANT_CONTAINER" sh -c 'tar czf /tmp/qdrant.tgz -C /qdrant/storage .' || true
  docker cp "$QDRANT_CONTAINER":/tmp/qdrant.tgz "$DEST/qdrant.tgz" || echo "⚠ Qdrant backup skipped."
fi

echo "==> Backing up Redis (forced RDB snapshot) -> $DEST/redis"
REDIS_CONTAINER="$(docker compose ps -q redis | head -n1)"
if [ -n "$REDIS_CONTAINER" ]; then
  docker exec "$REDIS_CONTAINER" sh -c 'redis-cli -a "$REDIS_PASSWORD" --no-auth-warning SAVE >/dev/null 2>&1; tar czf /tmp/redis.tgz -C /data .' || true
  docker cp "$REDIS_CONTAINER":/tmp/redis.tgz "$DEST/redis.tgz" || echo "⚠ Redis backup skipped (cache/broker state is recoverable)."
fi

echo "==> Backing up app data volumes -> $DEST/appdata"
mkdir -p "$DEST/appdata"
for svc in backend ml-engine; do
  CONTAINER="$(docker compose ps -q $svc | head -n1)"
  if [ -n "$CONTAINER" ]; then
    docker cp "$CONTAINER":/data "$DEST/appdata/$svc" 2>/dev/null \
      && echo "    ($svc /data copied)" \
      || echo "⚠ $svc app-data backup skipped (caches are reproducible)."
  fi
done

echo "==> Writing manifest"
cat > "$DEST/MANIFEST.txt" <<EOF
VeriUnlearn backup
Created : $(date -u +"%Y-%m-%dT%H:%M:%SZ")
Host    : $(hostname)
Compose : $(docker compose version --short 2>/dev/null || echo unknown)
EOF

echo "✅ Backup complete: $DEST"
