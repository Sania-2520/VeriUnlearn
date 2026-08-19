# VeriUnlearn — Developer Guide

How to set up, extend, and contribute to the VeriUnlearn codebase. Companion to
[`installation.md`](installation.md) (environment setup), [`configuration.md`](configuration.md)
(all settings), and [`architecture.md`](architecture.md) (system design).

---

## 1. Repository layout

```
veriunlearn/
├── backend/                  # FastAPI + SQLAlchemy (async) + research/ML services
│   ├── alembic/              # Migration scripts (one per phase, strictly additive)
│   ├── app/
│   │   ├── api/              # Routers (v1), deps, serializers
│   │   ├── core/             # config, security, exceptions, RBAC, middleware, logging
│   │   ├── db/               # models, session
│   │   ├── repositories/     # Data access layer (per domain)
│   │   ├── schemas/          # Pydantic request/response models
│   │   ├── services/         # Business logic (crypto, SISA, verification, …)
│   │   └── workers/          # Background task helpers
│   └── tests/                # pytest suite (65 tests, one file per phase)
├── frontend/                 # Next.js 15 (App Router) + TanStack Query + Tailwind
│   └── app/(app)/            # Authenticated pages (dashboard, privacy, research, admin…)
├── deploy/                   # nginx.conf, prometheus.yml, grafana dashboard + provisioning
├── docs/                     # All project documentation (this guide included)
├── contracts/                # Solidity DeletionRegistry (optional blockchain anchoring)
├── docker-compose.yml        # dev profiles: core / full
└── docker-compose.prod.yml   # production: nginx + backend + frontend + postgres + redis + qdrant + prometheus + grafana
```

## 2. Development environment

```bash
# Backend
cd backend
../.venv/Scripts/python -m pip install -r requirements.txt   # Windows venv; adjust for your OS
cp .env.example .env
../.venv/Scripts/python -m alembic upgrade head              # create + migrate DB
../.venv/Scripts/python -m app.seed                          # optional demo data
../.venv/Scripts/python -m uvicorn app.main:app --reload     # http://localhost:8000

# Frontend
cd frontend
npm install
cp .env.example .env.local                                   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                                                  # http://localhost:3000
```

## 3. Conventions

- **Python**: Python 3.12, `from __future__ import annotations`, async everywhere,
  type hints on all public signatures, SQLAlchemy 2.0 style (`session.get`, `select`).
- **Layering**: `api` (HTTP) → `services` (logic) → `repositories` (DB). Routers must
  not touch ORM objects directly beyond what serializers handle.
- **Validation**: every request is validated with Pydantic schemas in `app/schemas/`;
  bounds via `Field(ge=…, le=…)` / `Query(ge=…, le=…)`; reject invalid input early.
- **Errors**: raise `app.core.exceptions.*` (`NotFoundError`, `ValidationFailedError`,
  `ForbiddenError`, `UnauthorizedError`); handlers return the standard
  `{error, message, details}` envelope.
- **Audit**: mutating operations log an audit event via `AuditService.log(...)`.
- **Frontend**: Next.js App Router, `"use client"` pages with TanStack Query hooks,
  `@/lib/api` for fetch + error handling, `@/components/ui/*` for shared UI,
  Tailwind dark theme, role-gated nav in `(app)/layout.tsx`.

### Lint / format (backend)

```bash
cd backend
../.venv/Scripts/python -m ruff check app tests     # F, E9 clean (65 items fixed in the 1.0.0 pass)
```

## 4. Adding an API endpoint

1. **Schema** — add request/response models in `app/schemas/<domain>.py` and export from `app/schemas/__init__.py`.
2. **Service** — put business logic in `app/services/<domain>.py` (testable without HTTP).
3. **Repository** (if it touches the DB) — add to `app/repositories/`.
4. **Router** — add the route in `app/api/v1/<domain>.py`, wire auth via
   `CurrentUser`/`AdminUser`/`require_permission("resource:action")`.
5. **Register** — include the router in `app/api/v1/router.py`.
6. **Tests** — add a `test_phaseN.py` case (unit for service, `AsyncClient` for API).
7. **Docs** — add the row to `docs/api.md`.

## 5. Adding a database table

1. Add the ORM model in `app/db/models.py`.
2. Generate a migration: `alembic revision --autogenerate -m "describe change"` — verify it
   only contains intended operations.
3. Apply: `alembic upgrade head`; add a downgrade that drops exactly what you added.
4. Follow the phase pattern: migrations are strictly additive and chained in order.

## 6. Background jobs

Deletion, verification, and benchmark work run inside request handlers (fast enough at
research scale). `app/workers/tasks.py` holds reusable async task helpers. For production
scale, promote heavy work to a queue — see "Phase 8 extension points" in
[`phase7-deliverables.md`](phase7-deliverables.md).

## 7. Testing

```bash
cd backend
../.venv/Scripts/python -m pytest tests -q                       # full suite (65 tests)
../.venv/Scripts/python -m pytest tests -q --cov=app             # coverage (~78%)
../.venv/Scripts/python -m pytest tests/test_phase7.py -q        # one phase file
cd frontend && npm run build                                     # type-check + production build
```

CI runs the same commands (see `.github/workflows/ci.yml`). See
[`testing-report.md`](testing-report.md) for coverage details.

## 8. Troubleshooting quick hits

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: slowapi` | activate the project venv (`../.venv/Scripts/python`) or `pip install -r requirements.txt` |
| DB tables missing | `alembic upgrade head` (or restart the prod container — it migrates on boot) |
| 403 on cross-origin requests | set `CORS_ORIGINS` to the exact frontend origin |
| 401 from a valid API key | check key owner is active; quota `quota_per_minute` may be exhausted |
| Frontend can't reach API | `NEXT_PUBLIC_API_URL` must match the backend origin (see `frontend/.env.example`) |

See [`troubleshooting.md`](troubleshooting.md) for the full guide.
