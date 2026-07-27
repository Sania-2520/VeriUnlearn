# VeriUnlearn — Deployment Checklist

Comprehensive pre-production and post-deployment checklist for VeriUnlearn. Work top-to-bottom; do not skip items.

> Stack: Next.js frontend (:3000), FastAPI Backend (:8000), ML Engine (:8001), Celery workers, PostgreSQL 16, Redis 7, Qdrant, MinIO, nginx, Prometheus/Grafana/Loki/Alertmanager.

---

## A. Pre-Deployment Checklist

### Planning
- [ ] Maintenance window scheduled and communicated
- [ ] Rollback plan prepared (Section G)
- [ ] Stakeholders notified of expected downtime
- [ ] Release notes / CHANGELOG reviewed

### Source Code
- [ ] `git pull` the exact release tag (e.g., `v1.0.0`) and record SHA
- [ ] CI/CD pipeline green: lint + type-check + tests + security scan
- [ ] All PRs merged to target branch
- [ ] CHANGELOG updated and version bumped
- [ ] Git tag created: `git tag -a v<version> -m "Release v<version>"`

### Prerequisites
- [ ] Docker Engine ≥ 24.0 installed (`docker --version`)
- [ ] Docker Compose v2.20+ installed (`docker compose version`)
- [ ] NVIDIA GPU + CUDA 12.4+ (if using GPU inference)
- [ ] NVIDIA Container Toolkit installed (`docker info | grep nvidia`)
- [ ] 16 GB+ RAM available (32 GB+ recommended)
- [ ] 50 GB+ free disk space
- [ ] Required ports: 80, 443, 5432, 6379, 6333, 8000, 8001, 3000
- [ ] Monitoring ports: 9090, 3001, 3100, 9093 (if monitoring enabled)
- [ ] DNS record points to host / load balancer

### Secrets & Configuration
- [ ] `.env` file created from `.env.example`
- [ ] `JWT_SECRET_KEY` generated (256-bit): `openssl rand -hex 32`
- [ ] `APP_SECRET_KEY` generated (256-bit): `openssl rand -hex 32`
- [ ] `ML_ENGINE_API_KEY` generated (256-bit): `openssl rand -hex 32`
- [ ] `POSTGRES_PASSWORD` set to strong password (20+ characters)
- [ ] `REDIS_PASSWORD` set to strong password (20+ characters)
- [ ] `MINIO_ROOT_PASSWORD` set to strong password (20+ characters)
- [ ] `GRAFANA_ADMIN_PASSWORD` changed from default `admin`
- [ ] All OAuth/SSO credentials configured (Google, GitHub)
- [ ] AI provider API keys configured (OpenAI, Anthropic, HuggingFace)
- [ ] `.env` is git-ignored and NOT committed
- [ ] Secret scan passes: `gitleaks detect --source . --redact`

### TLS / Certificate
- [ ] TLS certificate issued (Let's Encrypt / cert-manager / manual)
- [ ] nginx configured to terminate TLS on port 443
- [ ] HTTP→HTTPS redirect enforced
- [ ] Security headers configured (HSTS, X-Content-Type-Options, X-Frame-Options)
- [ ] `/metrics` endpoint IP-restricted (internal network only)
- [ ] (Helm) Ingress `tls:` references the certificate secret

### Resource Sizing
- [ ] PostgreSQL persistent volume sized (≥ 100 GB for production)
- [ ] Redis persistent volume sized (≥ 10 GB)
- [ ] Qdrant persistent volume sized (≥ 50 GB)
- [ ] MinIO persistent volume sized (≥ 100 GB)
- [ ] ML Engine resource limits configured (4 CPU, 16 GB RAM, 1 GPU)
- [ ] Backend resource limits configured (2 CPU, 2 GB RAM)
- [ ] Worker resource limits configured (2 CPU, 4 GB RAM)

### Backup
- [ ] Full backup taken BEFORE deployment:
  - [ ] PostgreSQL: `pg_dump`
  - [ ] MinIO: `mc mirror`
  - [ ] Qdrant: snapshot via API
  - [ ] Redis: `BGSAVE` + copy RDB
- [ ] Backup restore tested on staging environment
- [ ] Backup retention policy documented

---

## B. Deployment Steps

### Docker Compose
- [ ] `docker compose build` — builds all images
- [ ] `docker compose up -d` — starts all services
- [ ] `docker compose exec backend alembic upgrade head` — runs DB migrations
- [ ] `./scripts/setup.sh --seed` — seeds demo data (if first deployment)
- [ ] `docker compose ps` — all services show `healthy` / `Up`

### Kubernetes (Helm)
- [ ] `helm repo update`
- [ ] `helm upgrade --install veriunlearn ./infra/kubernetes/helm/veriunlearn \
        --namespace veriunlearn --create-namespace \
        --set image.tag=<RELEASE_TAG>`
- [ ] `kubectl -n veriunlearn get pods` — all `Running` / `Ready`
- [ ] `kubectl -n veriunlearn rollout status deploy/veriunlearn-backend`
- [ ] `kubectl -n veriunlearn rollout status deploy/veriunlearn-frontend`
- [ ] `kubectl -n veriunlearn rollout status deploy/veriunlearn-ml-engine`
- [ ] `kubectl -n veriunlearn rollout status deploy/veriunlearn-worker`

### Infrastructure (Terraform)
- [ ] `cd infra/terraform/environments/production`
- [ ] `terraform init` — initializes backend
- [ ] `terraform plan` — reviews changes
- [ ] `terraform apply -auto-approve` — provisions infrastructure
- [ ] `aws eks update-kubeconfig --name veriunlearn-production`

---

## C. Post-Deployment Verification

### Health Checks
- [ ] Backend `GET /health` → `200 OK`
- [ ] ML Engine `GET /health` → `200 OK`
- [ ] Frontend `GET /` → `200 OK` (renders HTML)
- [ ] nginx `GET /health` → `200 OK` (via proxy)
- [ ] All Docker containers healthy: `docker compose ps`

### Smoke Tests
- [ ] Login: `POST /api/v1/auth/login` with demo credentials → JWT token
- [ ] List datasets: `GET /api/v1/datasets` → 200 with data
- [ ] List models: `GET /api/v1/models` → 200 with data
- [ ] Submit unlearning request: `POST /api/v1/unlearning/requests` → 201
- [ ] View jobs: `GET /api/v1/unlearning/requests` → 200
- [ ] Verification certificate: `GET /api/v1/certificates/<id>` → 200
- [ ] Benchmarks: `GET /api/v1/benchmarks` → 200
- [ ] API docs: `GET /api/docs` → Swagger UI renders

### Data Integrity
- [ ] Seed data present (datasets, models, sample certificates)
- [ ] New unlearning request appears in database
- [ ] Verification certificate hashes match expected values
- [ ] Ed25519 signature verifies correctly

### Load Testing (optional)
- [ ] Baseline latency: p99 < 500ms for API endpoints
- [ ] Concurrent requests handled without errors
- [ ] ML Engine queue processes within expected time

---

## D. Monitoring Setup Verification

### Prometheus
- [ ] Prometheus UI reachable at `http://localhost:9090`
- [ ] All targets are `UP` in Prometheus target list
- [ ] Backend metrics: `http_requests_total` increments on API calls
- [ ] ML Engine metrics: `inference_request_duration_seconds` present
- [ ] Node exporter metrics: `node_cpu_seconds_total` present
- [ ] Storage retention: 30 days configured

### Grafana
- [ ] Grafana UI reachable at `http://localhost:3001`
- [ ] Pre-provisioned datasources present (Prometheus, Loki, Tempo)
- [ ] Pre-provisioned dashboards load without errors
- [ ] Admin password changed from default `admin`
- [ ] Dashboard data populating (verify with test API call)

### Loki
- [ ] Loki endpoint reachable at `http://localhost:3100`
- [ ] Logs queryable: `{service="backend"}`
- [ ] Log retention configured appropriately

### Alertmanager
- [ ] Alertmanager UI reachable at `http://localhost:9093`
- [ ] Slack webhook configured and tested
- [ ] PagerDuty routing key configured (if using PagerDuty)
- [ ] Silences / inhibition rules configured
- [ ] Test alert fires and is received on configured channels

### Alert Rules (verify with `curl`)
- [ ] `HighErrorRate` — trigger: >1% 5xx for 5 min
- [ ] `HighLatency` — trigger: p99 > 2s for 5 min
- [ ] `ServiceDown` — trigger: `up == 0` for 1 min
- [ ] `DiskSpaceLow` — trigger: disk < 20% for 5 min
- [ ] `UnlearningQueueGrowing` — trigger: queue > 100 for 10 min
- [ ] `CertificateExpiring` — trigger: expiry < 30 days

---

## E. Security Verification

### Authentication
- [ ] JWT tokens issued on login
- [ ] Protected endpoints return 401 without token
- [ ] Token expiry enforced (30 min access, 7 day refresh)
- [ ] Rate limiting on auth endpoints (5 req/s)
- [ ] OAuth flows work (Google, GitHub)

### Authorization
- [ ] RBAC enforced on sensitive endpoints
- [ ] ML Engine API key required for inter-service communication
- [ ] Admin endpoints restricted to admin users

### Network Security
- [ ] Internal services not exposed on public interface
- [ ] nginx is the only entry point
- [ ] `/metrics` endpoints restricted to internal network
- [ ] CORS configured correctly: only allowed origins
- [ ] Rate limiting active on auth endpoints

### Container Security
- [ ] All containers run as non-root user
- [ ] No privileged containers
- [ ] Containers have `no-new-privileges` set
- [ ] Unnecessary capabilities dropped
- [ ] Container images scanned for vulnerabilities

### Data Security
- [ ] PostgreSQL connections use password authentication
- [ ] Redis connections require password (`AUTH`)
- [ ] MinIO connections use access/secret keys
- [ ] JWT tokens use strong signing key
- [ ] Certificates signed with Ed25519

---

## F. Compliance Verification

### GDPR Compliance
- [ ] Deletion requests processed within 30-day SLA
- [ ] Verification certificates generated for each deletion
- [ ] Audit log captures all deletion operations
- [ ] Data subject can request verification certificate
- [ ] GDPR contact configured in environment

### CCPA Compliance
- [ ] Deletion requests accepted and processed
- [ ] Categories of personal information tracked
- [ ] Opt-out mechanism functional

### EU AI Act Compliance
- [ ] Model documentation generated
- [ ] Training data provenance tracked
- [ ] Unlearning operations logged
- [ ] AI Act contact configured

### Audit Trail
- [ ] All mutation operations logged to hash chain
- [ ] Hash chain entries are cryptographically linked
- [ ] Blockchain anchoring functional (if configured)
- [ ] Audit log retention ≥ 7 years
- [ ] Logs tamper-evident

---

## G. Rollback Procedures

### Docker Compose Rollback

```bash
# Option 1: Rollback specific service
docker compose up -d --force-recreate <service>  # if using :latest

# Option 2: Rollback to previous image tag
export IMAGE_TAG=<previous_tag>
docker compose up -d

# Option 3: Full stack rollback
git checkout <previous-release-tag>
docker compose down
docker compose up -d
```

### Database Rollback

```bash
# Alembic downgrade
docker compose exec backend alembic downgrade <previous_revision>

# Restore from backup (last resort)
gunzip -c <backup.sql.gz> | docker compose exec -T postgres psql -U veriunlearn
```

### Helm Rollback

```bash
# View revision history
helm history veriunlearn -n veriunlearn

# Rollback to previous revision
helm rollback veriunlearn <REVISION> -n veriunlearn

# Verify rollback
kubectl -n veriunlearn get pods
kubectl -n veriunlearn rollout status deploy/veriunlearn-backend
```

### Rollback Decision Criteria

Trigger rollback if any of these conditions are met:

- [ ] Error rate > 5% for 5 consecutive minutes
- [ ] p99 latency > 5s for 5 consecutive minutes
- [ ] Critical services (backend, ML Engine) unhealthy for > 2 minutes
- [ ] Data integrity issues detected
- [ ] Security vulnerability identified
- [ ] User-facing functionality broken

### Post-Rollback

- [ ] Verify all services healthy
- [ ] Run smoke tests (Section C)
- [ ] Notify stakeholders of rollback and root cause
- [ ] Create incident report
- [ ] Schedule fix in next sprint

---

## H. Incident Response Checklist

### Detection
- [ ] Alert received (Slack / PagerDuty / email)
- [ ] Verify alert is not a false positive
- [ ] Determine severity (Critical / Warning / Info)
- [ ] Acknowledge alert in PagerDuty (if configured)

### Triage
- [ ] Check Grafana dashboards for anomalies
- [ ] Check Loki logs for error patterns
- [ ] Check Prometheus Alertmanager for related alerts
- [ ] Determine affected services and user impact
- [ ] Estimate time to resolution

### Response
- [ ] **Critical:** Page on-call engineer immediately
- [ ] **Warning:** Investigate within 1 hour
- [ ] Apply rollback if criteria met (Section G)
- [ ] Scale affected service if resource-constrained
- [ ] Communicate status to stakeholders

### Resolution
- [ ] Root cause identified and documented
- [ ] Fix applied (config change, code fix, scaling)
- [ ] All services healthy again
- [ ] Monitoring metrics return to baseline
- [ ] Incident report drafted

### Post-Mortem
- [ ] Root cause analysis completed
- [ ] Action items created to prevent recurrence
- [ ] Runbook updated with incident details
- [ ] Monitoring improved (additional alerts, dashboards)
- [ ] Post-mortem shared with team within 48 hours

---

## Appendices

### A. Useful Commands

```bash
# Service health
docker compose ps
curl http://localhost:8000/health
curl http://localhost:8001/health

# Logs
docker compose logs --tail=100 -f backend
docker compose logs --tail=100 -f worker

# Shell access
docker compose exec backend sh
docker compose exec postgres psql -U veriunlearn veriunlearn

# Database migration
docker compose exec backend alembic upgrade head
docker compose exec backend alembic downgrade -1

# Scaling
docker compose up -d --scale worker=4

# Full cleanup
docker compose down -v
```

### B. Quick Reference — Environment Checks

```bash
./scripts/validate_deployment.sh  # full validation
./scripts/healthcheck.sh          # quick health check
```

### C. Monitoring URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Prometheus | `http://localhost:9090` | — |
| Grafana | `http://localhost:3001` | `admin` / `{GRAFANA_ADMIN_PASSWORD}` |
| Alertmanager | `http://localhost:9093` | — |
| Loki | `http://localhost:3100` | — |
| MinIO Console | `http://localhost:9001` | `{MINIO_ROOT_USER}` / `{MINIO_ROOT_PASSWORD}` |
| RabbitMQ | `http://localhost:15672` | `guest` / `guest` |

### D. Reference Documents

- [Deployment Guide](DEPLOYMENT_GUIDE.md) — full deployment documentation
- [Monitoring Guide](MONITORING_GUIDE.md) — monitoring setup and procedures
- [Demo Package](DEMO_PACKAGE.md) — demonstration walkthrough
- [Release Checklist](RELEASE_CHECKLIST.md) — release-specific checks
- [Security Audit](../artifacts/SECURITY_AUDIT.md) — security assessment report

---

*Maintained by the VeriUnlearn DevOps team. Last updated: July 2026.*
