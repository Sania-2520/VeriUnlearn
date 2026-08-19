# Deployment Guide

## 1. Local development

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python -m app.seed                                   # Adult Census + SISA model + demo users
uvicorn app.main:app --reload                        # http://localhost:8000

# frontend
cd frontend
npm install
cp .env.example .env.local                           # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                                          # http://localhost:3000
```

## 2. Docker Compose

```bash
# minimal (backend + frontend, SQLite, in-memory vector store)
docker compose --profile core up --build

# full stack (adds PostgreSQL, Redis, Qdrant)
docker compose --profile full up --build
```

With the `full` profile set in `backend/.env`:

```env
DATABASE_URL=postgresql+asyncpg://veriunlearn:veriunlearn@postgres:5432/veriunlearn
VECTOR_STORE_BACKEND=qdrant
QDRANT_URL=http://qdrant:6333
REDIS_URL=redis://redis:6379/0
```

Apply migrations (first boot): `docker compose exec backend alembic upgrade head`.

### Production (Phase 7)

`docker-compose.prod.yml` runs the full platform behind an NGINX reverse proxy with healthchecks, restart policies, bounded logging, and optional monitoring:

```bash
# 1. Create secrets (never committed)
cp backend/.env.example .env.prod
#    set SECRET_KEY, POSTGRES_PASSWORD, CORS_ORIGINS, METRICS_TOKEN, SMTP_* …

# 2. Build & start
REGISTRY=ghcr.io IMAGE_BACKEND=veriunlearn/backend IMAGE_FRONTEND=veriunlearn/frontend \
  docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

Services: `nginx` (edge proxy + rate-limit zone) → `frontend` (Next.js standalone, non-root) + `backend` (multi-stage, non-root, runs `alembic upgrade head` on start) + `postgres` + `redis` + `qdrant` + `prometheus` (scrapes `/metrics`) + `grafana` (dashboard auto-provisioned from `deploy/grafana/`).

Secrets are injected via environment (required vars fail fast with `:?`). Migrations run automatically on backend start.

## 3. Migrations (Alembic)

```bash
cd backend
alembic revision --autogenerate -m "change description"   # after model changes
alembic upgrade head                                       # apply
```

## 4. Production checklist

1. **Secrets** — generate `SECRET_KEY` (`python -c "import secrets; print(secrets.token_hex(32))"`),
   set `ENV=production`, `DEBUG=false`.
2. **Database** — PostgreSQL via `DATABASE_URL`; run `alembic upgrade head` before deploy.
3. **Vector store** — `VECTOR_STORE_BACKEND=qdrant` + `QDRANT_URL` (or keep `memory` for single-node).
4. **CORS** — set `CORS_ORIGINS` to the exact frontend origin(s).
5. **Rate limiting** — tune `RATE_LIMIT_DEFAULT`; optional Redis-backed limits.
6. **Blockchain** (optional) — deploy `contracts/DeletionRegistry.sol` to a testnet, set
   `BLOCKCHAIN_ENABLED=true`, `BLOCKCHAIN_RPC_URL`, `BLOCKCHAIN_REGISTRY_ADDRESS`,
   `BLOCKCHAIN_PRIVATE_KEY`; install `web3` (`requirements-optional.txt`).
7. **LLM/LoRA** (optional) — install `requirements-optional.txt` on a GPU host; the model registry
   activates the `llm_lora` backend.
8. **Keys** — the server RSA keypair is generated on first boot under `backend/keys/`; back it up
   (certificate verification depends on the public key).
9. **Email (Phase 7)** — set `EMAIL_PROVIDER=smtp` + `SMTP_HOST/PORT/USERNAME/PASSWORD/FROM` to
   deliver notifications; keep `null` for no-op local runs.
10. **Metrics (Phase 7)** — set `METRICS_TOKEN` in production so `/metrics` requires a bearer token
    (match it in `deploy/prometheus/prometheus.yml`).
11. **RBAC (Phase 7)** — `alembic upgrade head` seeds the 5 roles; assign users via the Admin portal
    (or `POST /admin/users`). API keys inherit their owner's role.
12. **API keys (Phase 7)** — tune `API_KEY_DEFAULT_QUOTA` (default 60 req/min) and per-key quotas
    when issuing keys from the Developer portal.

## 5. Render + Vercel

### Backend (Render)
- Service type: **Web Service**; root directory `backend/`
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Env vars: all of `backend/.env.example` (point `DATABASE_URL` at a managed Postgres)

### Frontend (Vercel)
- Root directory `frontend/`; framework preset Next.js
- Env: `NEXT_PUBLIC_API_URL=https://<render-backend-url>`
- Build runs `next build` automatically; API calls go direct to Render (enable CORS in backend).

## 6. Nginx reverse proxy (self-hosted)

The production compose stack ships a ready-made config at `deploy/nginx/nginx.conf` (routes `/api/` → backend, `/` → frontend, healthcheck bypass, `limit_req` zone, security headers, 60 MB upload cap, 300 s proxy read timeout).

Self-hosted equivalent (TLS-terminating):

```nginx
server {
  listen 443 ssl;
  server_name unlearn.example.com;
  # ssl_certificate ...; ssl_certificate_key ...;

  location /api/ { proxy_pass http://127.0.0.1:8000; proxy_set_header Host $host; }
  location /docs { proxy_pass http://127.0.0.1:8000; }
  location /     { proxy_pass http://127.0.0.1:3000; }
}
```

## 7. Monitoring (Prometheus + Grafana, Phase 7)

- Backend exposes `GET /metrics` (Prometheus text). Set `METRICS_TOKEN` to require `Authorization: Bearer <token>`.
- `deploy/prometheus/prometheus.yml` scrapes `backend:8000/metrics` every 15 s; uncomment the `authorization` block when `METRICS_TOKEN` is set.
- `deploy/grafana/veriunlearn-dashboard.json` + `provisioning/` auto-register the datasource and dashboard in the compose `grafana` service (UI on port `3001`, default `admin/admin` — change via `GRAFANA_ADMIN_USER`/`GRAFANA_ADMIN_PASSWORD`).
- In-app system monitoring: `/monitoring` (CPU/RAM/disk, dependency health, worker queue, API latency/error rate, uptime; 8 s refresh) backed by `GET /api/v1/monitoring/system` and persisted `system_metrics`.

## 8. CI/CD

| Workflow | Runs |
|---|---|
| `.github/workflows/ci.yml` | Backend compile+import check + `pytest tests -q` (65 tests); frontend `npm ci && npm run build`; dedicated benchmark job (`test_phase6.py test_phase7.py`) — every push/PR |
| `.github/workflows/security.yml` | Bandit (medium+) + `npm audit --audit-level=high` — push/PR + weekly Monday |
| `.github/workflows/deploy.yml` | Tag `v*` or manual: build & push backend/frontend images to GHCR, then staging deploy job |

Deployments can be recorded in-app (`POST /api/v1/admin/deployments`) and shown in the Admin portal.
