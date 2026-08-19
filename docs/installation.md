# VeriUnlearn — Installation Guide

Install VeriUnlearn locally (dev), with Docker, or for production. Prerequisites,
step-by-step commands, and verification checks for each path.

---

## 1. Prerequisites

| Component | Version | Notes |
|---|---|---|
| Python | 3.12+ | 3.13 works (used in dev); 3.12 is the CI target |
| Node.js | 20/22 | Next.js 15 (App Router) |
| npm | 10+ | ships with Node |
| Docker | 24+ | only needed for the Docker paths |
| Git | any | clone the repository |

Optional for the full stack: PostgreSQL 16, Redis 7, Qdrant (all provided by Docker
Compose `full` / prod profiles).

## 2. Clone

```bash
git clone <repository-url> veriunlearn
cd veriunlearn
```

## 3. Local development install

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # defaults work for local SQLite
alembic upgrade head                 # create + migrate the DB
python -m app.seed                   # optional: Adult Census dataset + demo users
uvicorn app.main:app --reload        # http://localhost:8000
```

Verify: `curl http://localhost:8000/health` → `{"status":"ok",…}` and
`http://localhost:8000/docs` shows the OpenAPI UI.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local           # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                          # http://localhost:3000
```

Verify: open `http://localhost:3000`, log in with a seeded demo account
(`admin@veriunlearn.dev / admin12345`).

## 4. Docker (dev / test)

```bash
# Minimal: backend + frontend (SQLite, in-memory vector store)
docker compose --profile core up --build

# Full stack: + PostgreSQL, Redis, Qdrant
docker compose --profile full up --build
```

Services: backend `:8000`, frontend `:3000`. Migrations:
`docker compose exec backend alembic upgrade head` (prod containers run this on boot).

## 5. Production install (Docker Compose)

See [`deployment.md`](deployment.md) §2 for the full production profile. Summary:

```bash
cp backend/.env.example .env.prod    # then set SECRET_KEY, POSTGRES_PASSWORD, CORS_ORIGINS…
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

Stack: nginx → frontend + backend + postgres + redis + qdrant + prometheus + grafana.
Migrations run automatically on backend start; healthchecks on every service.

## 6. Verify the installation

1. **Backend health** — `curl http://localhost:8000/health` → 200 `ok`.
2. **Frontend** — `http://localhost:3000` loads the login page.
3. **Auth** — log in with a seeded account; the dashboard loads.
4. **Privacy flow** — search an identity (e.g. `maya` after seeding), open a footprint.
5. **Unlearning** — run impact analysis + a small SISA deletion; a certificate is issued.
6. **Verification** — verify the certificate; download PDF.
7. **Tests** — `cd backend && python -m pytest tests -q` → 65 passed.
8. **Metrics** — `curl http://localhost:8000/metrics` shows Prometheus text.

## 7. Troubleshooting installs

| Problem | Likely cause / fix |
|---|---|
| `slowapi` import error | using the wrong interpreter — activate the project venv |
| Frontend blank page / API 404 | `NEXT_PUBLIC_API_URL` mismatch; set it to the backend origin |
| Migrations fail on Postgres | DB user lacks privileges; run `alembic upgrade head` as the DB owner |
| Ports in use | change `8000`/`3000` in compose or run with `--port` |

See [`troubleshooting.md`](troubleshooting.md) for more.
