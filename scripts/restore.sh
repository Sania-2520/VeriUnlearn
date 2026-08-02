#!/usr/bin/env bash
# =============================================================================
# VeriUnlearn — restore
# Restores PostgreSQL / Redis / MinIO / Qdrant / app-data from a backup
# produced by backup.sh.
# Usage: ./scripts/restore.sh <BACKUP_DIR>
#   e.g. ./scripts/restore.sh ./backups/veriunlearn-20240101-120000
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

if [ $# -lt 1 ]; then
  echo "Usage: $0 <BACKUP_DIR>" >&2
  exit 1
fi
SRC="$1"
[ -d "$SRC" ] || { echo "✗ Backup dir not found: $SRC" >&2; exit 1; }

POSTGRES_USER="${POSTGRES_USER:-veriunlearn}"
POSTGRES_DB="${POSTGRES_DB:-veriunlearn}"
POSTGRES_CONTAINER="$(docker compose ps -q postgres | head -n1)"
[ -n "$POSTGRES_CONTAINER" ] || { echo "✗ postgres not running." >&2; exit 1; }

if [ -f "$SRC/postgres.dump" ]; then
  echo "==> Restoring PostgreSQL from $SRC/postgres.dump"
  docker exec -i "$POSTGRES_CONTAINER" pg_restore -U "$POSTGRES_USER" --clean --if-exists -d "$POSTGRES_DB" < "$SRC/postgres.dump" \
    || echo "⚠ pg_restore reported errors (often non-fatal with --clean)."
else
  echo "⚠ No postgres.dump found in backup."
fi

if [ -d "$SRC/minio" ]; then
  echo "==> Restoring MinIO"
  MINIO_CONTAINER="$(docker compose ps -q minio | head -n1)"
  [ -n "$MINIO_CONTAINER" ] && docker cp "$SRC/minio/." "$MINIO_CONTAINER":/data || echo "⚠ MinIO restore skipped."
fi

if [ -f "$SRC/qdrant.tgz" ]; then
  echo "==> Restoring Qdrant"
  QDRANT_CONTAINER="$(docker compose ps -q qdrant | head -n1)"
  if [ -n "$QDRANT_CONTAINER" ]; then
    docker cp "$SRC/qdrant.tgz" "$QDRANT_CONTAINER":/tmp/qdrant.tgz
    docker exec "$QDRANT_CONTAINER" sh -c 'rm -rf /qdrant/storage/* && tar xzf /tmp/qdrant.tgz -C /qdrant/storage'
  fi
fi

if [ -f "$SRC/redis.tgz" ]; then
  echo "==> Restoring Redis"
  REDIS_CONTAINER="$(docker compose ps -q redis | head -n1)"
  if [ -n "$REDIS_CONTAINER" ]; then
    docker exec "$REDIS_CONTAINER" redis-cli -a "$REDIS_PASSWORD" --no-auth-warning FLUSHALL >/dev/null 2>&1 || true
    docker cp "$SRC/redis.tgz" "$REDIS_CONTAINER":/tmp/redis.tgz
    docker exec "$REDIS_CONTAINER" sh -c 'rm -rf /data/* && tar xzf /tmp/redis.tgz -C /data' || true
  fi
fi

if [ -d "$SRC/appdata" ]; then
  echo "==> Restoring app data volumes"
  for svc in backend ml-engine; do
    if [ -d "$SRC/appdata/$svc" ]; then
      CONTAINER="$(docker compose ps -q $svc | head -n1)"
      [ -n "$CONTAINER" ] && docker cp "$SRC/appdata/$svc/." "$CONTAINER":/data/ || echo "⚠ $svc app-data restore skipped."
    fi
  done
fi

echo "✅ Restore complete. Verify with: ./scripts/healthcheck.sh"
