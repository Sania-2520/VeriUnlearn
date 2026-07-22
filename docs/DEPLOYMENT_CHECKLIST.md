# Deployment Checklist — VeriUnlearn

Pre-deploy and post-deploy checklist for both **Docker Compose** and
**Kubernetes (Helm)** targets. Work top-to-bottom; do not skip items.

> Stack baseline: FastAPI backend (`:8000`), ML Engine (`:8001`),
> Next.js frontend (`:3000`), Celery workers, PostgreSQL 16, Redis 7,
> Qdrant, MinIO, and Prometheus/Grafana/Loki monitoring.

---

## A. Pre-Deploy — Common (all targets)

- [ ] `git pull` the exact commit / tag you intend to ship and record the SHA.
- [ ] Read [docs/RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) and confirm the
      release was cut (tag, CHANGELOG, CI green, scans clean).
- [ ] Confirm target environment matches prerequisites:
  - [ ] Docker 24+ / Docker Compose v2.20+ (Compose target)
  - [ ] Kubernetes cluster + Helm 3 + `kubectl` access (Helm target)
  - [ ] NVIDIA GPU + CUDA 12.4+ and NVIDIA Container Toolkit (for ML Engine)
  - [ ] 16 GB+ RAM (32 GB+ recommended); GPU node for real inference
- [ ] DNS record points to the deployment host / load balancer.
- [ ] Backup taken **before** deploy (see Section D).
- [ ] Maintenance window communicated if required.

## B. Secrets Generation

Generate fresh, high-entropy secrets per environment. Never reuse across
environments.

```bash
openssl rand -hex 32   # JWT_SECRET_KEY  (256-bit)
openssl rand -hex 32   # APP_SECRET_KEY  (256-bit)
openssl rand -hex 32   # REDIS_PASSWORD
```

- [ ] `JWT_SECRET_KEY` set (256-bit, `openssl rand -hex 32`)
- [ ] `APP_SECRET_KEY` set (256-bit, `openssl rand -hex 32`)
- [ ] `POSTGRES_PASSWORD` — strong, 20+ chars
- [ ] `MINIO_ROOT_PASSWORD` — strong, 20+ chars
- [ ] `REDIS_PASSWORD` — set and referenced by broker/backend URLs
- [ ] `GRAFANA_ADMIN_PASSWORD` — changed from default `admin:admin`
- [ ] `.env` is git-ignored and not committed
- [ ] (Helm) secrets injected via `--set secrets.jwtSecret=...` or a sealed
      secret / external secret store — **not** plaintext in Git
- [ ] Secret scan passed: `gitleaks detect --source . --redact`

## C. TLS / Cert-Manager

- [ ] TLS certificate issued for the domain (Let's Encrypt via cert-manager or
      manual cert)
- [ ] (Helm) `cert-manager` ClusterIssuer configured; `Ingress` uses
      `tls:` with the issued secret
- [ ] (Compose) nginx terminates TLS (443) with `fullchain.pem` / `privkey.pem`
- [ ] HSTS, X-Content-Type-Options, X-Frame-Options headers present (nginx
      security headers)
- [ ] HTTP→HTTPS redirect enforced
- [ ] `/metrics` endpoint IP-restricted / not publicly exposed

## D. Resource Sizing & Backup

- [ ] PostgreSQL: managed RDS/Cloud SQL (prod) or persistent volume (compose);
      reserved CPU/memory sized for workload
- [ ] Redis: managed ElastiCache/Memorystore or persistent volume
- [ ] Qdrant: persistent volume / Qdrant Cloud; index pre-built
- [ ] MinIO: S3-compatible bucket with lifecycle policy
- [ ] ML Engine: `deploy.resources.limits.memory: 16G` + 1 GPU reservation
- [ ] **Backup before deploy** completed:
  - [ ] `pg_dump` of PostgreSQL captured and verified
  - [ ] MinIO model artifacts snapshot / `mc cp --recursive`
  - [ ] Qdrant volume snapshot
- [ ] Backup restore tested on a staging copy (at least once)

## E. Deploy

### Docker Compose

- [ ] `docker compose build`
- [ ] `docker compose up -d`
- [ ] `docker compose exec backend alembic upgrade head` (DB migration)
- [ ] `docker compose ps` — all services `healthy`/`Up`

### Kubernetes (Helm)

- [ ] `helm repo update`
- [ ] `helm upgrade --install veriunlearn infra/k8s/helm/veriunlearn \
        --namespace veriunlearn --create-namespace \
        --set image.tag=<TAG> --set secrets.jwtSecret=$(openssl rand -hex 32)`
- [ ] `kubectl -n veriunlearn get pods` — all `Running`/`Ready`
- [ ] `kubectl -n veriunlearn rollout status deploy/<component>`

## F. Health Checks

- [ ] Backend: `curl http://localhost:8000/health` → 200
- [ ] ML Engine: `curl http://localhost:8001/health` → 200
- [ ] Frontend reachable via HTTPS (`:443` / load balancer)
- [ ] Celery worker registered: `docker compose logs worker` shows beat/worker
      ready (or `kubectl logs` for the worker deployment)
- [ ] Liveness/readiness probes passing in Kubernetes
- [ ] Prometheus target `up` for all jobs (`/metrics` scrape OK)

## G. Smoke Tests

- [ ] `curl http://localhost:8000/health` returns healthy
- [ ] Log in via API: `POST /api/v1/auth/login` with a known account
- [ ] Submit a deletion request: `POST /api/v1/unlearning/requests`
- [ ] Generate a proof: `POST /api/v1/verify/proofs/generate`
- [ ] Load frontend in browser; dashboards render
- [ ] Swagger UI available at `http://localhost:8000/api/docs`

## H. Rollback Plan

- [ ] (Compose) Previous image tags pinned; `docker compose up -d \
        --scale ...` to prior version documented
- [ ] (Helm) `helm rollback veriunlearn <REVISION>` rehearsed
- [ ] DB rollback: `alembic downgrade <prev>` verified safe, or restore from
      pre-deploy `pg_dump`
- [ ] Decision owner named; rollback trigger criteria documented (error rate,
      latency SLO breach)
- [ ] Communication channel (Slack/PagerDuty) ready for incident call

## I. Monitoring & Alerting

- [ ] Grafana dashboards provisioned from
      `infra/monitoring/grafana/dashboards/`
- [ ] Grafana admin password changed; login verified at `:3001`
- [ ] Prometheus scrape targets healthy (`:9090`)
- [ ] Loki datasource reachable from Grafana (logs queryable)
- [ ] Alertmanager receivers configured (Slack, PagerDuty)
- [ ] Critical alerts fire-tested (e.g., synthetic alert or silence-then-test)
- [ ] SLO/error-budget dashboards visible to on-call

---

_See also: [docs/production-deployment.md](production-deployment.md),
[docs/RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md)._
