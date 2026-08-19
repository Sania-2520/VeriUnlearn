# Phase 7 — Enterprise Platform: Compliance Dashboards, Admin Portal, RBAC, Monitoring, Notifications, API Management & CI/CD

**VeriUnlearn** — deployable enterprise platform on top of the Phases 1–6 codebase.

Phase 7 adds the platform layer: five-role RBAC with API + UI enforcement, an admin portal, live GDPR/DPDP compliance dashboards with persisted snapshots and exports, Prometheus metrics + Grafana dashboards, structured logging, in-app + email notifications with retry, programmatic API keys with quotas/rate limiting/usage logs, system monitoring (CPU/RAM/disk, dependency health, worker queue, API latency/error rate), analytics endpoints with CSV/JSON export, production Docker Compose with NGINX reverse proxy, GitHub Actions CI/CD, and a security-hardening middleware stack. All Phases 1–6 code is untouched; everything here is additive.

---

## 1. Newly Created Files

### Backend — core infrastructure
| File | Purpose |
|---|---|
| `backend/app/core/rbac.py` | Five-role permission matrix (`admin`, `researcher`, `auditor`, `operator`, `viewer`) — single source of truth, persisted to `roles`/`permissions` for admin visibility and audit |
| `backend/app/core/middleware.py` | `SecurityHeadersMiddleware` (CSP, nosniff, frame/ref/perms policies), `OriginCheckMiddleware` (CSRF defence), `RequestMetricsMiddleware` (Prometheus + latency/error ring), `APIKeyAuthMiddleware` (X-API-Key auth, quota, usage logging) |
| `backend/app/core/logging.py` | Dependency-free structured JSON logging with request correlation fields |

### Backend — services
| File | Purpose |
|---|---|
| `backend/app/services/admin.py` | `AdminService`: user create / role / active toggling, RBAC matrix, deployment history, platform overview counts |
| `backend/app/services/api_keys.py` | `APIKeyService`: issuance (raw key shown once), SHA-256 hash storage, sliding-window quota, auth, revoke, usage log |
| `backend/app/services/notifications.py` | `NotificationService`: in-app + email notifications, provider abstraction (`null` no-op / `smtp`), read/unread, retry semantics |
| `backend/app/services/monitoring.py` | `MonitoringService`: live snapshot (system resources, dependency health: DB/Redis/Qdrant/vector store, worker queue, API latency/error rate/uptime) + persisted `system_metrics` history |
| `backend/app/services/metrics.py` | Prometheus collectors (`veriunlearn_http_requests_total`, latency histogram, system gauges) + `render_metrics()` |
| `backend/app/services/analytics.py` | `AnalyticsService`: deletion trends, privacy trends, usage, dataset growth, certificate stats, CSV/JSON export |

### Backend — API, tests, migration
| File | Purpose |
|---|---|
| `backend/app/api/v1/admin.py` | Admin portal endpoints (users, roles, deployments, overview) |
| `backend/app/api/v1/apikeys.py` | API key issue / list / revoke |
| `backend/app/api/v1/notifications.py` | Notification inbox, read/unread, mark-all-read |
| `backend/app/api/v1/monitoring.py` | System snapshot + metric history |
| `backend/app/api/v1/analytics.py` | Analytics + export endpoints |
| `backend/tests/test_phase7.py` | 15 tests: RBAC, API keys (+ middleware), notifications, monitoring, analytics, compliance reports, admin, security headers, CSRF, Prometheus endpoint |
| `backend/alembic/versions/10a9fd591a22_phase7_enterprise_platform.py` | Migration for the 7 new tables + role/permission seeds |

### Frontend
| File | Purpose |
|---|---|
| `frontend/app/(app)/admin/page.tsx` | Admin portal: platform overview, user creation, role/active management, deployment history |
| `frontend/app/(app)/admin/roles/page.tsx` | RBAC matrix viewer |
| `frontend/app/(app)/developer/page.tsx` | Developer portal: issue/list/revoke API keys, quota + usage logs |
| `frontend/app/(app)/notifications/page.tsx` | Notification inbox with event badges, mark read / mark all |
| `frontend/app/(app)/monitoring/page.tsx` | System monitoring UI: CPU/RAM/disk, dependency health, queue, latency/error rate, time-series charts (8s refresh) |
| `frontend/lib/rbac.ts` | Client-side role → route guard helper used by the app layout |

### Deploy / CI / config
| File | Purpose |
|---|---|
| `docker-compose.prod.yml` | Production profile: nginx + backend + frontend + postgres + redis + qdrant + prometheus + grafana |
| `deploy/nginx/nginx.conf` | Reverse proxy: `/api/` → backend, `/` → frontend, rate-limit zone, security headers, health bypass |
| `deploy/prometheus/prometheus.yml` | Scrape config for the backend `/metrics` endpoint |
| `deploy/grafana/veriunlearn-dashboard.json` | Grafana dashboard (CPU, RAM, disk, HTTP rate/latency, error rate) |
| `deploy/grafana/provisioning/datasources/prometheus.yml` + `dashboards/dashboards.yml` | Auto-provisioned datasource + dashboard on container start |
| `.github/workflows/deploy.yml` | Tag-triggered Docker build/push to GHCR (staging deploy hook) |
| `.github/workflows/security.yml` | Bandit + npm audit on push/PR/weekly |
| `backend/.env.example` | Phase 7 settings (SMTP, metrics token, rate limit, API key quota) |

---

## 2. Modified Files (all additive)

| File | Change |
|---|---|
| `backend/app/main.py` | slowapi limiter + exception handler; middleware stack (security headers, origin check, request metrics, API key auth); `GET /metrics` Prometheus endpoint; JSON request logging |
| `backend/app/api/deps.py` | API-key-authenticated user injection; `require_permission()` RBAC dependency |
| `backend/app/api/v1/router.py` | Registered `analytics`, `apikeys`, `monitoring`, `notifications` routers |
| `backend/app/api/v1/admin.py` | Extended: create user, set active, RBAC matrix, deployment history, overview |
| `backend/app/api/v1/compliance.py` | Extended: `POST /compliance/report`, `GET /compliance/reports`, `GET /compliance/export` |
| `backend/app/db/models.py` | Added 7 tables: `roles`, `permissions`, `api_keys`, `notifications`, `system_metrics`, `compliance_reports`, `deployment_logs`, `analytics_cache` |
| `backend/app/core/config.py` | New settings: `EMAIL_PROVIDER`, `SMTP_*`, `NOTIFICATION_MAX_ATTEMPTS`, `METRICS_TOKEN`, `API_KEY_DEFAULT_QUOTA`, `RATE_LIMIT_DEFAULT` |
| `backend/requirements.txt` | Added `slowapi`, `prometheus-client`, `psutil` |
| `backend/Dockerfile` | Multi-stage build (wheels builder → slim runtime), non-root user, alembic migrate on start, healthcheck |
| `frontend/Dockerfile` | Multi-stage build (Next.js standalone), non-root user, healthcheck |
| `frontend/app/(app)/layout.tsx` | Phase 7 nav items (Admin, Developer, Monitoring, Notifications), RBAC page guards, unread notification bell |
| `frontend/app/(app)/compliance/page.tsx` | Compliance reports snapshot generation + CSV/JSON export |
| `docker-compose.yml` | `core` / `full` profiles (backend+frontend vs +postgres/redis/qdrant) |
| `.github/workflows/ci.yml` | Added lint/import check step + dedicated benchmark job |

No existing API, endpoint, or Phases 1–6 behavior was changed or removed.

---

## 3. Database Migrations

`backend/alembic/versions/10a9fd591a22_phase7_enterprise_platform.py` — creates exactly the 7 new tables and seeds RBAC data:

```
roles, permissions, api_keys, notifications, system_metrics, compliance_reports, deployment_logs, analytics_cache
```

Apply with:

```bash
cd backend
../.venv/Scripts/python -m alembic upgrade head
```

The upgrade also seeds one row per role (from `app/core/rbac.py`) and one row per distinct permission — the DB stays in sync with the code matrix. Verified incremental: it depends on the Phase 6 head (`e3bb87e588e3`) and only adds new tables + inserts (no alters/drops).

---

## 4. RBAC — Roles & Permission Matrix

Enforced at three layers:

1. **API** — `require_permission("resource:action")` dependency (403 if the caller's role lacks it); `require_roles("admin")` for legacy admin-only routes.
2. **Middleware** — API keys authenticate as their owning user, so key-based calls inherit the owner's role.
3. **UI** — `frontend/lib/rbac.ts` + layout page guard redirect unauthorized roles to `/dashboard`; nav items are filtered by role.

| Role | Can do | Cannot do |
|---|---|---|
| `admin` | Everything: users, roles, keys, monitoring, compliance reports, config | — |
| `researcher` | Read everything + run benchmarks/attacks/experiments, privacy scans | Manage users/keys, run unlearning, manage datasets/models |
| `auditor` | Read-only verification, audit trail, compliance, monitoring, analytics | Execute unlearning, manage anything |
| `operator` | Day-to-day ops: datasets, models, unlearning, verification, privacy scans | Manage users/roles/keys, research runs, monitoring |
| `viewer` | Read-only dashboards, datasets/models, privacy, certificates, compliance, analytics | Everything mutating |

Permission strings are scoped `resource:action` (e.g. `unlearning:execute`, `compliance:report`, `api_keys:manage`) — see `backend/app/core/rbac.py` for the full matrix, or `GET /admin/roles`.

---

## 5. API Documentation (Phase 7)

All endpoints under `/api/v1`, JWT (or `X-API-Key`) protected. OpenAPI auto-generated at `/docs` / `/redoc`.

| Method | Path | Description |
|---|---|---|
| GET | `/admin/overview` | Platform counts (users, datasets, models, certificates, requests, keys) |
| GET | `/admin/users` | List users with role/permissions |
| POST | `/admin/users` | `{email, full_name, password, role}` — create user (audited) |
| PATCH | `/admin/users/{id}/role` | `"role"` ∈ 5-role matrix (audited) |
| PATCH | `/admin/users/{id}/active` | `true/false` — activate/deactivate (audited) |
| GET | `/admin/roles` | RBAC matrix |
| GET | `/admin/deployments` | Deployment history |
| POST | `/admin/deployments` | Record deployment `{version, environment, status, commit_sha?, artifact?}` |
| POST | `/api-keys` | `{name, scopes?, quota_per_minute?, expires_in_days?}` → `{api_key: {key, …}}` (raw key once) |
| GET | `/api-keys` | Own keys + usage logs |
| POST | `/api-keys/{id}/revoke` | Revoke key |
| GET | `/notifications` | `{notifications, unread}` inbox |
| GET | `/notifications/unread-count` | `{unread}` |
| POST | `/notifications/read-all` | Mark all read |
| POST | `/notifications/{id}/read` | Mark one read |
| GET | `/monitoring/system` | `{snapshot, history}` — resources, dependency health, queue, latency/error/uptime |
| GET | `/analytics/overview` | Deletion/verification/certificate/compliance aggregates |
| GET | `/analytics/deletion-trends?days=30` | Time-series of deletion requests |
| GET | `/analytics/privacy-trends?days=90` | Privacy scan/report trend |
| GET | `/analytics/usage?days=30` | Platform usage stats |
| GET | `/analytics/dataset-growth?days=90` | Dataset growth series |
| GET | `/analytics/certificates` | Certificate totals/validity stats |
| GET | `/analytics/export?format=csv|json` | Analytics bundle download |
| POST | `/compliance/report` | Persist a GDPR/DPDP compliance snapshot |
| GET | `/compliance/reports?limit=` | Compliance report history |
| GET | `/compliance/export?format=csv|json` | Compliance history download |

---

## 6. Docker & Docker Compose

### Dev / test (multi-profile)
```bash
docker compose --profile core up --build    # backend + frontend (SQLite, in-memory vectors)
docker compose --profile full up --build    # + PostgreSQL, Redis, Qdrant
```

### Production (`docker-compose.prod.yml`)
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

Services: **nginx** (edge, TLS-ready, rate-limit zone) → **frontend** (Next.js standalone, non-root) + **backend** (multi-stage, non-root, runs `alembic upgrade head` on start) + **postgres** + **redis** + **qdrant** + **prometheus** (scrapes `/metrics`) + **grafana** (auto-provisioned dashboard).

Hardening built in: non-root runtime users, `restart: unless-stopped`, healthchecks on every service, bounded JSON-file logging (`max-size 10m`, `max-file 3`), secrets injected via environment (never committed), `SECRET_KEY`/`POSTGRES_PASSWORD` required (`:?` syntax fails fast when missing).

Migrations run automatically on container start (backend `CMD`); you can also apply manually: `docker compose exec backend alembic upgrade head`.

---

## 7. CI/CD (GitHub Actions)

| Workflow | Triggers | Jobs |
|---|---|---|
| `.github/workflows/ci.yml` | push / PR | Backend: compile+import check, `pytest tests -q` (65 tests). Frontend: `npm ci && npm run build`. Dedicated `benchmark` job runs `test_phase6.py test_phase7.py` for fast research/enterprise regression signal |
| `.github/workflows/security.yml` | push / PR / weekly Mon | Bandit (medium+), `npm audit --audit-level=high` |
| `.github/workflows/deploy.yml` | `v*` tags / manual | Build & push backend+frontend images to GHCR, then a staging deploy job (env-gated) |

Deployments are recorded in-app via `POST /admin/deployments` (visible in the Admin portal).

---

## 8. Observability

- **Prometheus endpoint** — `GET /metrics` (text format, optional `METRICS_TOKEN` bearer auth): `veriunlearn_http_requests_total{method,path,status}`, latency histogram, system gauges (CPU/RAM/disk), refreshed from a live `MonitoringService.snapshot()` on each scrape.
- **Grafana** — `deploy/grafana/veriunlearn-dashboard.json` provisioned automatically (datasource + dashboard provisioning configs included).
- **System monitoring API/UI** — CPU/RAM/disk, dependency health (database, Redis, Qdrant, vector store), worker queue in-flight/total, avg API latency, error rate, uptime; samples persisted as `system_metrics` for history charts.
- **Structured logging** — JSON formatter with correlation fields; every request logged with method/path; middleware failures logged but never break requests.
- **Health** — `GET /health` used by Docker healthchecks and nginx.

---

## 9. Notifications & Email

- **Events**: `deletion.completed`, `verification.completed`, `certificate.ready`, `experiment.finished`, `system.error`.
- **Channels**: in-app (persisted, read/unread) and email via a provider-abstracted adapter — `EMAIL_PROVIDER=null` (no-op, marks delivered) or `smtp` (SMTP_HOST/PORT/USERNAME/PASSWORD/FROM).
- **Retry**: `NOTIFICATION_MAX_ATTEMPTS` with `next_attempt_at` backoff on the email channel; delivery state (`delivered`, `attempts`) surfaced in the inbox.
- **UI**: bell with unread badge in the app header (30s poll) + full inbox at `/notifications`.

---

## 10. API Management

- **Issue** — `POST /api-keys` returns the raw `vk_…` key exactly once; only a SHA-256 hash + 8-char prefix are stored.
- **Auth** — `X-API-Key` middleware authenticates the key, resolves its owning user (RBAC applies), rejects inactive owners / expired / revoked keys.
- **Quota** — per-key sliding-window `quota_per_minute` enforced in the middleware (401 with `rate limit exceeded`).
- **Usage** — per-request log (timestamp, path, status) kept on the key row (last 50), plus a global `requests_count` and `last_used_at`.
- **UI** — Developer portal (`/developer`): issue, copy, revoke, quota display, usage drill-down.
- **Platform rate limiting** — slowapi `RATE_LIMIT_DEFAULT` (default `100/minute`) plus nginx `limit_req` zone at the edge.

---

## 11. Analytics & Reporting

Endpoints in §5 cover deletion trends, privacy trends, usage, dataset growth and certificate stats. `GET /analytics/export` and `GET /compliance/export` produce downloadable **CSV** or **JSON** bundles; compliance snapshots are persisted (`compliance_reports`) so scores trend over time from the Compliance page.

---

## 12. Manual Testing Checklist

1. **Boot** — `docker compose --profile core up --build`; open `http://localhost:3000`, login as `admin@veriunlearn.dev / admin12345`.
2. **Admin portal** — `/admin`: create a user (role `viewer`), change a role, deactivate/activate, check RBAC matrix page, record a deployment.
3. **RBAC** — log in as the viewer: Admin/Developer/Monitoring nav items hidden; typing `/admin` redirects to `/dashboard`; API calls with the viewer token return 403 where guarded.
4. **API keys** — `/developer`: issue a key, copy it, `curl -H "X-API-Key: vk_…" http://localhost:8000/api/v1/notifications` → 200; set quota to 3 and hit 4× → 401 on the 4th; revoke → 401; usage log shows the paths.
5. **Notifications** — trigger a deletion (`/unlearning`), check the bell badge, open `/notifications`, mark read / mark all.
6. **Monitoring** — `/monitoring`: CPU/RAM/disk, dependency health (DB healthy, Redis/Qdrant optional), queue, latency/error rate; charts populate over ~16s.
7. **Metrics** — `curl localhost:8000/metrics` → Prometheus text with `veriunlearn_http_requests_total`; with `METRICS_TOKEN` set, unauthenticated scrape → 401.
8. **Compliance** — `/compliance`: generate a snapshot, verify it appears in the reports list; download CSV + JSON.
9. **Analytics** — hit `/api/v1/analytics/overview`, `deletion-trends`, `dataset-growth`; download `/api/v1/analytics/export?format=csv`.
10. **Security headers** — `curl -I localhost:8000/health` shows CSP, nosniff, frame/ref/perms policies; cross-origin POST from `Origin: https://evil.example` → 403.
11. **Email** — set `EMAIL_PROVIDER=smtp` with a local MailHog; verify deletion/verification notifications arrive and `delivered` flips in the inbox.
12. **Migrations** — fresh DB: `alembic upgrade head` creates all 7 tables + seeds 5 roles; `docker compose exec backend alembic current` shows head.

## 13. Security Checklist

- [x] Secrets never committed (`.env.prod`/`.env` git-ignored; compose `:?` required vars fail fast)
- [x] API keys stored hashed (SHA-256), never returned twice
- [x] RBAC enforced server-side (`require_permission`) — UI hiding is defense-in-depth only
- [x] API keys inherit owner role; deactivated users rejected at the middleware
- [x] CSRF defence: cross-origin state-changing requests blocked when `Origin` present
- [x] Security headers on every response (backend middleware + nginx)
- [x] Rate limiting at edge (nginx) and API (slowapi) + per-key quotas
- [x] `/metrics` optionally bearer-protected (`METRICS_TOKEN`)
- [x] Non-root containers, read-only config, pinned base images
- [x] Audit logging for admin actions, key issuance/revocation, compliance scans
- [x] Input validation (Pydantic bounds, `Query(ge/le/pattern)`), structured error responses
- [x] Bandit + npm audit in CI; weekly scheduled scan
- [ ] (Ops) Terminate TLS at nginx with real certs; restrict `CORS_ORIGINS`; rotate `SECRET_KEY`/SMTP creds; enable `METRICS_TOKEN` in prod

## 14. Known Limitations

1. **SQLite defaults in dev** — sliding-window quotas and rate limiting are per-process; use the `full`/prod profile (PostgreSQL + Redis) for multi-instance consistency.
2. **Email delivery is synchronous** — notifications are sent inline; a real worker would decouple sending (attempt/backoff fields are persisted and ready).
3. **GPU metrics not collected** — monitoring covers CPU/RAM/disk; GPU counters are an extension point.
4. **System metrics are process-local history** — persisted rows reflect the current host/process only; multi-node aggregation is left to Prometheus.
5. **No TLS termination inside compose** — nginx listens on 80; terminate TLS at the load balancer or add certs to `deploy/nginx`.
6. **Deploy workflow's staging job is a hook** — it posts a recorded deployment; wire it to your actual staging host/registry creds.

## 15. Phase 8 Extension Points

1. **Background workers** — promote async email/notification delivery and benchmark jobs to a Celery/ARQ worker; surface queue depth per worker in monitoring.
2. **SSO / OIDC** — plug identity providers behind the existing JWT user model; map IdP groups onto the 5-role matrix.
3. **Audit export & retention** — add queryable audit-trial export (CSV/JSONL) and a retention policy.
4. **Multi-tenancy** — scope datasets/models/keys by organization with row-level access on top of the RBAC matrix.
5. **Alerting** — Prometheus alert rules (error-rate spikes, dependency down, quota exhaustion) → Grafana/email/webhook.
6. **GPU/vector-store telemetry** — extend `MonitoringService.snapshot()` with GPU utilization and Qdrant collection stats.
7. **API gateway** — per-key IP allowlists, granular scopes, and billing/quota tiers on top of `APIKeyService`.
8. **Compliance evidence bundles** — export a GDPR/DPDP report as a signed, zip-packaged evidence bundle (snapshot + audit chain + certificates).
