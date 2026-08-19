# VeriUnlearn — Administrator Guide

Operating, securing, and maintaining a VeriUnlearn deployment: users & roles, API keys,
compliance evidence, monitoring, backups, and production operations.

---

## 1. Roles & permissions

Five roles are seeded by `alembic upgrade head` (source of truth: `backend/app/core/rbac.py`):

| Role | Summary |
|---|---|
| `admin` | Full control: users, roles, API keys, monitoring, compliance reports, deployments |
| `researcher` | Read everything + run benchmarks, attacks, experiments, privacy scans |
| `auditor` | Read-only verification, audit trail, compliance, monitoring |
| `operator` | Datasets, models, unlearning, verification, privacy scans |
| `viewer` | Read-only dashboards and reports |

### Managing users (Admin portal → `/admin`)

- **Create** a user: full name, email, password (min 8 chars), role.
- **Change role** / **activate-deactivate**: deactivating a user blocks their token and
  their API keys immediately (checked at request time).
- **RBAC matrix** (`/admin/roles`) shows every role × permission.

Every user/role/activation change is written to the audit trail.

## 2. API keys

Issue keys from the **Developer portal** (or `POST /api/v1/api-keys`). Guidance:

- Give each consumer a named key (e.g. `ci-pipeline`) so usage is attributable.
- Set `quota_per_minute` to the consumer's real need; the platform default is
  `API_KEY_DEFAULT_QUOTA` (60/min).
- Keys inherit their **owner's role** — a viewer key cannot call admin endpoints.
- Revoke keys that are unused, leaked, or tied to a departing user.

## 3. Compliance evidence (GDPR Art. 17 / DPDP)

- **Compliance page** → *Generate snapshot* persists a point-in-time report
  (GDPR/DPDP scores, risk, open/completed requests). Snapshots trend over time.
- Export **CSV/JSON** for regulators; combine with per-request certificates
  (`/certificates`) and the verified audit trail (`/audit`) to build evidence bundles.
- Every deletion has: tombstones → Merkle pre/post roots → RSA-signed certificate →
  audit-chain entries → optional verification report. Download the JSON/PDF certificate
  for the data subject's file.

## 4. Monitoring & alerting

- **System Monitoring** page (`/monitoring`): CPU/RAM/disk, dependency health
  (database, Redis, Qdrant, vector store), worker queue depth, API latency, error rate, uptime.
- **Prometheus**: `GET /metrics` (protect with `METRICS_TOKEN` in production).
- **Grafana**: pre-provisioned dashboard (`deploy/grafana/`) on port `3001` in the prod
  compose stack. Change the default admin password via `GRAFANA_ADMIN_PASSWORD`.

## 5. Backups & recovery

| Asset | Where | Backup |
|---|---|---|
| Database (SQLite dev / PostgreSQL prod) | `DATABASE_URL` | daily dump; test restore |
| Server RSA keypair | `backend/keys/` (`/app/keys` in prod) | **back up — certificate verification depends on it** |
| Uploaded datasets / vectors | `backend/data/`, Qdrant storage | nightly snapshot |
| Compliance snapshots | `compliance_reports` table | included in DB dump |

Rollback: images are tagged by release; keep the previous tag and
`docker compose -f docker-compose.prod.yml up -d` with the old `TAG=`.

## 6. Production hardening checklist

- [ ] `ENV=production`, `DEBUG=false`, strong `SECRET_KEY` (never committed)
- [ ] `CORS_ORIGINS` = exact frontend origin(s)
- [ ] `METRICS_TOKEN` set and matched in `deploy/prometheus/prometheus.yml`
- [ ] `EMAIL_PROVIDER=smtp` with real SMTP credentials (or keep `null`)
- [ ] TLS terminated at nginx/load balancer (the bundled nginx listens on :80)
- [ ] `RATE_LIMIT_DEFAULT` tuned; per-key quotas assigned
- [ ] PostgreSQL + Redis in production (not SQLite) for multi-instance rate limiting
- [ ] Non-root containers, bounded logs (already default in the prod compose)
- [ ] Weekly dependency scans (CI `security.yml` runs Bandit + npm audit)

## 7. Deployments & release workflow

- Tags `v*` trigger `.github/workflows/deploy.yml` (build + push images, staging deploy).
- Record each deployment in-app: **Admin → deployment history → record** (version,
  environment, status, commit sha) — visible for audit.
- Before upgrading: review `CHANGELOG.md`, run `alembic upgrade head` (automatic on prod
  container start), and smoke-test `/health` + one unlearning flow.

## 8. Daily operations checklist

1. Check `/monitoring` for dependency health + error rate.
2. Review unread **system.error** notifications.
3. Confirm compliance snapshots are current; export evidence as needed.
4. Rotate API keys for any consumer whose usage pattern changed.
5. Verify a sample certificate (`/verification`) still validates.
