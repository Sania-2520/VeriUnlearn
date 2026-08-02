# Disaster Recovery Plan — VeriUnlearn

## Purpose

This document defines the backup, restore, and recovery procedures for the
VeriUnlearn production stack so that the system can be rebuilt and data
recovered after an infrastructure failure, data corruption, or accidental
deletion.

The scope covers the data-holding services in the Docker Compose stack:

- PostgreSQL — primary relational store (users, models, unlearning requests, proofs, audit)
- Redis — Celery broker / result backend + cache (recoverable, RPO-tolerant)
- MinIO — object storage (datasets, model artifacts)
- Qdrant — vector store (RAG / similarity embeddings)
- `backend-data` / `ml-data` volumes — model cache, HPO studies, RAG storage

## RPO / RTO Targets

| Metric | Target | Notes |
|---|---|---|
| Recovery Point Objective (RPO) | ≤ 24 h | Daily automated backup; acceptable for batch-orchestrated pipeline |
| Recovery Time Objective (RTO) | ≤ 4 h | Restore + `alembic upgrade head` + service restart |
| Backup retention | 7 daily | Offsite copy recommended (see below) |

## 1. Backup

### On-demand backup

```bash
./scripts/backup.sh
```

Creates `./backups/veriunlearn-YYYYMMDD-HHMMSS/` containing:

- `postgres.dump` — custom-format `pg_dump` of the full database
- `redis.tgz` — forced Redis RDB snapshot (broker/cache state)
- `minio/` — mirrored MinIO data
- `qdrant.tgz` — Qdrant storage tarball
- `appdata/` — `backend` and `ml-engine` `/data` volumes
- `MANIFEST.txt` — timestamp, host, compose version

Custom output directory:

```bash
./scripts/backup.sh --out /mnt/backup-volume
```

### Scheduled backup (cron example)

```cron
# Daily 02:00 UTC; rotates to keep the last 7
0 2 * * * cd /opt/veriunlearn && ./scripts/backup.sh >> /var/log/veriunlearn-backup.log 2>&1 && \
  find backups -maxdepth 1 -name 'veriunlearn-*' -mtime +7 -exec rm -rf {} +
```

### Offsite copy (recommended)

For true DR, copy the backup directory off-host (S3, NFS, or remote server):

```bash
aws s3 sync ./backups/veriunlearn-* s3://veriunlearn-backups/
```

Or with MinIO mirror:

```bash
docker exec <minio-container> mc mirror --watch /backup remote-bucket/
```

## 2. Restore

Prerequisite: the stack must be up (`docker compose up -d`) and the database
must be running. Restore from a specific backup directory:

```bash
./scripts/restore.sh ./backups/veriunlearn-20260102-020000
```

This will:

1. `pg_restore --clean --if-exists` the PostgreSQL dump (non-fatal warnings are normal)
2. `FLUSHALL` Redis and restore the RDB snapshot
3. Restore MinIO from the mirrored directory
4. Wipe and restore Qdrant storage from `qdrant.tgz`
5. Copy `appdata/backend` and `appdata/ml-engine` back into the `/data` volumes

After restore:

```bash
docker compose restart backend worker ml-engine
./scripts/healthcheck.sh
```

### Manual Postgres-only restore

```bash
docker exec -i $(docker compose ps -q postgres) pg_restore -U veriunlearn --clean --if-exists \
  -d veriunlearn < backups/veriunlearn-YYYYMMDD-HHMMSS/postgres.dump
```

## 3. Recovery Scenarios

### Full host loss

1. Provision a new host (or GPU instance for ML workloads).
2. Install Docker + Docker Compose + NVIDIA container toolkit.
3. Clone the repository and copy `.env` (secrets) from secure storage.
4. `docker compose up -d`
5. `./scripts/restore.sh <backup-dir>`
6. `./scripts/healthcheck.sh`

### Database corruption / accidental deletion

1. Stop write traffic: `docker compose stop backend worker ml-engine`
2. Restore Postgres only: `./scripts/restore.sh <backup-dir>` (idempotent with `--clean`)
3. Restart services and verify.

### Single corrupted vector index (Qdrant)

Qdrant can rebuild from source data; alternatively restore just `qdrant.tgz`:

```bash
./scripts/restore.sh ./backups/veriunlearn-YYYYMMDD-HHMMSS   # restores everything
```

For a Qdrant-only restore, see the qdrant block inside `restore.sh`.

## 4. Verification of Backups

Backup correctness should be tested regularly (at least monthly):

```bash
./scripts/backup.sh
./scripts/restore.sh <latest-backup-dir>
./scripts/healthcheck.sh
```

A restore drill into a scratch stack (different port range) is the gold
standard and is recommended before relying on backups in production.

## 5. Secrets and Configuration Recovery

`backup.sh` does **not** back up secrets. Keep `.env` (JWT/App secrets, DB
passwords, MinIO/Redis/Grafana credentials) in a separate, encrypted location:

- A secrets manager (e.g., Vault, AWS Secrets Manager), or
- An encrypted file (`gpg -c .env`) stored off-host.

Losing `.env` requires regenerating secrets; rotating `JWT_SECRET_KEY` /
`APP_SECRET_KEY` invalidates existing sessions and refresh tokens.

## 6. Related Documents

- `docs/production-deployment.md` — deployment and environment configuration
- `docs/MONITORING_GUIDE.md` — alerting on disk/backup failures
- `docs/RELEASE_CHECKLIST.md` — pre-release operational checklist
