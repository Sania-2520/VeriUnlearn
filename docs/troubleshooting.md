# VeriUnlearn — Troubleshooting Guide

Common problems, their causes, and fixes. Organized by area; each entry lists symptoms
first, then the resolution.

---

## 1. Installation & startup

### `ModuleNotFoundError: No module named 'slowapi'` (or any package)
- **Cause**: the wrong Python interpreter is active (system Python instead of the venv).
- **Fix**: use the project venv — `cd backend && ../.venv/Scripts/python -m uvicorn app.main:app` (Windows) or activate the venv first; or reinstall: `pip install -r requirements.txt`.

### Backend starts but `/health` 404s / docs blank
- **Fix**: confirm you are on `http://localhost:8000/health` and the app bound
  `0.0.0.0:8000`; check for port conflicts (`uvicorn` logs the bind error).

### Migrations fail: `Table 'roles' already exists` / `No such table`
- **Cause**: DB partially migrated or missing `alembic upgrade head`.
- **Fix**: run `alembic upgrade head`; for a broken local SQLite DB, delete the dev DB
  file and re-migrate (dev only — never for production).

## 2. Authentication & RBAC

### `401 Unauthorized` on every request after login
- **Cause**: expired token or wrong `SECRET_KEY` (e.g. key changed between restarts).
- **Fix**: log in again; keep `SECRET_KEY` stable across restarts in production.

### Logged in but pages redirect to `/dashboard`
- **Cause**: RBAC page guard — your role cannot access that route.
- **Fix**: that's expected for `viewer` on admin/monitoring pages; request a role change
  from an administrator.

### API returns 403 for a valid call
- **Cause**: `require_permission` denied the action for your role.
- **Fix**: verify the role matrix (`GET /admin/roles` or `docs/administrator-guide.md`).

## 3. API keys

### Valid key returns 401
- **Causes**: key revoked, expired (`expires_in_days`), owner deactivated, or the
  per-minute `quota_per_minute` sliding window is exhausted.
- **Fix**: check the Developer portal status dot (green = active); issue a new key or
  raise the quota; ensure the owner account is active.

### Key works in the UI but a script gets 401
- **Fix**: send the key as `X-API-Key: <key>` (not `Authorization: Bearer`), and make sure
  you copied the full `vk_…` value (it's shown only once at issuance).

## 4. Unlearning & verification

### Deletion request stuck in `pending`
- **Fix**: check the request via `GET /api/v1/unlearning/requests/{id}`; most jobs finish
  in seconds at research scale. A `failed` status usually means the dataset/model was
  deleted mid-flight — re-run after re-seeding.

### Certificate verification fails
- **Causes**: server RSA keypair regenerated (keys not backed up), DB replaced, or audit
  chain tampered.
- **Fix**: restore the original `keys/` directory + DB backup; re-verify. A tampered audit
  chain is detected and reported by `GET /audit/verify`.

### `certified` method rejected with >200 records
- **Cause**: hard cap for the certified (Newton-step) method.
- **Fix**: split into batches of ≤200 records.

## 5. Frontend

### Pages load but data never appears
- **Fix**: open DevTools → Network; confirm requests reach the backend and `NEXT_PUBLIC_API_URL`
  matches the backend origin. CORS errors mean `CORS_ORIGINS` on the backend doesn't include
  the frontend origin.

### Stale data after an action
- **Fix**: TanStack Query caches are invalidated on mutation success; hard-refresh
  (Ctrl/Cmd+Shift+R) if a page looks stale.

## 6. Docker / deployment

### Container restarts in a loop
- **Fix**: `docker compose logs backend` — most often a missing required env var
  (`SECRET_KEY`/`POSTGRES_PASSWORD` fail fast), a failed migration, or DB unreachable.
  Verify Postgres health with `docker compose ps`.

### Frontend container exits after build
- **Fix**: the image runs the Next.js standalone server on port 3000; check
  `NEXT_PUBLIC_API_URL` was set at build time (`docker compose build --no-cache frontend`).

### Prometheus can't scrape `/metrics`
- **Fix**: if `METRICS_TOKEN` is set on the backend, uncomment the `authorization` block
  in `deploy/prometheus/prometheus.yml` with the same token.

## 7. Performance

### Benchmark / attack calls are slow
- **Cause**: SISA + MIA probes are O(shards × eval_size); very large eval sizes are
  memory-bound (cap 2000).
- **Fix**: reduce `eval_size`/`n_delete`; run on a machine with adequate RAM; use the
  `full`/prod profile (Postgres + Qdrant) instead of SQLite.

### High memory usage during retrain
- **Fix**: reduce shard count for huge datasets; each shard is trained independently —
  the process holds one model at a time per shard.

## 8. Getting more help

- Search the repository docs (`docs/`) — every deliverable phase has a dedicated guide.
- Open an issue with: version, environment, steps to reproduce, and the relevant log lines
  (see [`CONTRIBUTING.md`](../CONTRIBUTING.md) and [`SECURITY.md`](../SECURITY.md)).
