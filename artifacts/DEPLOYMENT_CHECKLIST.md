# VeriUnlearn — Deployment Checklist (v1.0 RC)

Consolidated from `docs/DEPLOYMENT_CHECKLIST.md` and extended for the v1.0 Release
Candidate. Work top-to-bottom; do not skip items. Items new for RC are marked **[RC]**.

> Stack baseline: Next.js frontend (`:3000`), FastAPI Backend (`:8000`),
> ML Engine (`:8001`), Celery workers, PostgreSQL 16, Redis 7, Qdrant, MinIO,
> Prometheus/Grafana/Loki.

---

## A. Pre-Deploy — Common

- [ ] `git pull` the exact RC tag (e.g. `v1.0.0-rc1`) and record SHA.
- [ ] Confirm [Release Checklist](../../docs/RELEASE_CHECKLIST.md) green (tag, CHANGELOG, CI, scans).
- [ ] Prereqs: Docker 24+ / Compose v2.20+ **or** K8s + Helm 3; NVIDIA GPU + CUDA 12.4+ for ML Engine; 16 GB+ RAM (32 GB+ rec).
- [ ] DNS record points to host / LB.
- [ ] Backup taken **before** deploy (Section D).
- [ ] Maintenance window communicated.

## B. Secrets Generation **[RC: added MONITORING/ML-ENGINE keys]**

```bash
openssl rand -hex 32   # JWT_SECRET_KEY  (256-bit)
openssl rand -hex 32   # APP_SECRET_KEY  (256-bit)
openssl rand -hex 32   # ML_ENGINE_API_KEY  (X-API-Key header, see ml_engine.py:21)
openssl rand -hex 32   # REDIS_PASSWORD
openssl rand -hex 32   # GRAFANA_ADMIN_PASSWORD
```

- [ ] `JWT_SECRET_KEY`, `APP_SECRET_KEY` set (256-bit).
- [ ] **[RC]** `ML_ENGINE_API_KEY` set; Backend `MLEngineClient` uses it (`packages/backend/app/infrastructure/external/ml_engine.py:21`).
- [ ] `POSTGRES_PASSWORD`, `MINIO_ROOT_PASSWORD`, `REDIS_PASSWORD` strong (20+ chars).
- [ ] `GRAFANA_ADMIN_PASSWORD` changed from default.
- [ ] `.env` git-ignored; not committed.
- [ ] (Helm) secrets via `--set secrets.*` / sealed secret / external store — never plaintext in Git.
- [ ] **[RC]** Secret scan: `gitleaks detect --source . --redact` passes (no `proofs/users.json`, no root `app.py` secret).

## C. TLS / Cert-Manager

- [ ] TLS cert issued (cert-manager or manual).
- [ ] (Helm) Ingress `tls:` references the issued secret; (Compose) nginx terminates 443.
- [ ] Security headers (HSTS, X-Content-Type-Options, X-Frame-Options) present.
- [ ] HTTP→HTTPS redirect enforced.
- [ ] `/metrics` IP-restricted / not public.

## D. Resource Sizing & Backup

- [ ] PostgreSQL / Redis / Qdrant / MinIO sized (managed or persistent volumes).
- [ ] ML Engine: `deploy.resources.limits.memory: 16G` + 1 GPU reservation (Helm
      `infra/kubernetes/helm/veriunlearn/values/production.yaml`).
- [ ] **Backup before deploy:** `pg_dump`, MinIO snapshot, Qdrant volume snapshot.
- [ ] Backup restore tested on a staging copy.

## E. Deploy

### Docker Compose
- [ ] `docker compose build`
- [ ] `docker compose up -d`
- [ ] `docker compose exec backend alembic upgrade head`
- [ ] `docker compose ps` — all `healthy`/`Up`
- [ ] **[RC]** Confirm only `docker-compose.yml` is used (not `docker-compose.phase5.yml`).

### Kubernetes (Helm)
- [ ] `helm repo update`
- [ ] `helm upgrade --install veriunlearn infra/kubernetes/helm/veriunlearn \
        --namespace veriunlearn --create-namespace \
        --set image.tag=<RC_TAG> \
        --set secrets.jwtSecret=$(openssl rand -hex 32) \
        --set secrets.mlEngineApiKey=$(openssl rand -hex 32)`
- [ ] `kubectl -n veriunlearn get pods` — all `Running`/`Ready`
- [ ] `kubectl -n veriunlearn rollout status deploy/<component>`
- [ ] **[RC]** Staging overlay validated: `helm upgrade ... -f values/staging.yaml`; prod: `values/production.yaml`.

## F. Health Checks

- [ ] Backend `GET /health` → 200 (`packages/backend`).
- [ ] ML Engine `GET /health` → 200 (`packages/ml-engine`).
- [ ] **[RC]** ML Engine `GET /controller/health` → 200 (`hybrid_controller.health_check`).
- [ ] Frontend reachable via HTTPS.
- [ ] Celery worker registered (beat/worker ready).
- [ ] Liveness/readiness probes passing; Prometheus targets `up`.

## G. Smoke Tests **[RC: added new routes]**

- [ ] `POST /api/v1/auth/login` with known account.
- [ ] **[RC]** `GET /api/v1/monitoring` (needs `MONITORING_READ`, `rbac.py:37`).
- [ ] `POST /api/v1/unlearning/requests` (deletion request).
- [ ] `POST /api/v1/verify/proofs/generate`.
- [ ] **[RC]** `GET /api/v1/models` and `POST /api/v1/training/start`.
- [ ] **[RC]** `GET /api/v1/auth/oauth/{provider}/authorize` redirects.
- [ ] `POST /api/v1/unlearning/e2e` → calls `execute_full_pipeline` (`api.py:1224`).
- [ ] Frontend dashboards render; Swagger at `:8000/api/docs`.

## H. CI/CD Gates **[RC]**

- [ ] CI green: lint + type-check + tests (`.github/workflows/ci.yml`).
- [ ] CD promoted RC through staging → prod (`.github/workflows/cd.yml`).
- [ ] Release workflow ran (`.github/workflows/release.yml`); tag + notes published.

## I. Rollback Plan

- [ ] (Compose) prior image tags pinned.
- [ ] (Helm) `helm rollback veriunlearn <REVISION>` rehearsed.
- [ ] DB rollback: `alembic downgrade <prev>` safe, or restore pre-deploy `pg_dump`.
- [ ] Rollback owner named; trigger criteria (error rate, latency SLO) documented.
- [ ] Incident channel (Slack/PagerDuty) ready.

## J. Monitoring & Alerting

- [ ] Grafana dashboards from `infra/monitoring/grafana/dashboards/`.
- [ ] Grafana admin password changed; Prometheus/Loki reachable.
- [ ] Alertmanager receivers configured; critical alerts fire-tested.
- [ ] SLO/error-budget dashboards visible to on-call.

---

_See also: [docs/DEPLOYMENT_CHECKLIST.md](../../docs/DEPLOYMENT_CHECKLIST.md),
[docs/production-deployment.md](../../docs/production-deployment.md),
[artifacts/SECURITY_AUDIT.md](SECURITY_AUDIT.md)._
