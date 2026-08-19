# VeriUnlearn — Configuration Guide

Every environment variable, what it controls, and recommended values. The backend reads
`.env` (see `backend/.env.example`); the frontend reads `frontend/.env.local`.

---

## 1. Backend (`backend/.env`)

### Core

| Variable | Default | Purpose |
|---|---|---|
| `ENV` | `development` | `production` enables prod behaviors |
| `DEBUG` | `true` | verbose logging; set `false` in production |
| `SECRET_KEY` | `dev-secret` | JWT signing secret — **must** be a long random value in prod |
| `APP_NAME` | `VeriUnlearn` | service name (health/docs branding) |
| `API_V1_PREFIX` | `/api/v1` | API prefix |
| `CORS_ORIGINS` | `http://localhost:3000` | comma-separated allowed origins (CSRF + CORS) |
| `RATE_LIMIT_DEFAULT` | `100/minute` | slowapi platform rate limit |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT lifetime |

### Database & vector store

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./veriunlearn.db` | SQLAlchemy async URL (Postgres: `postgresql+asyncpg://user:pass@host:5432/db`) |
| `VECTOR_STORE_BACKEND` | `memory` | `memory` (dev) or `qdrant` |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant endpoint when `qdrant` backend |
| `REDIS_URL` | *(empty)* | optional Redis (rate limiting, future queues) |

### Security / crypto

| Variable | Default | Purpose |
|---|---|---|
| `KEY_DIR` | `keys/` | RSA keypair directory (back this up) |
| `METRICS_TOKEN` | *(empty)* | if set, `/metrics` requires `Authorization: Bearer <token>` |
| `BLOCKCHAIN_ENABLED` | `false` | optional Solidity registry anchoring |
| `BLOCKCHAIN_RPC_URL` / `BLOCKCHAIN_REGISTRY_ADDRESS` / `BLOCKCHAIN_PRIVATE_KEY` | *(empty)* | blockchain config |

### Notifications & email

| Variable | Default | Purpose |
|---|---|---|
| `EMAIL_PROVIDER` | `null` | `null` (no-op) or `smtp` |
| `SMTP_HOST` / `SMTP_PORT` | empty / `587` | SMTP endpoint |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | empty | SMTP auth |
| `SMTP_FROM` | `noreply@veriunlearn.dev` | sender address |
| `NOTIFICATION_MAX_ATTEMPTS` | `5` | email retry cap |

### API keys

| Variable | Default | Purpose |
|---|---|---|
| `API_KEY_DEFAULT_QUOTA` | `60` | default per-minute quota for issued keys |

## 2. Frontend (`frontend/.env.local`)

| Variable | Default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | backend base URL the browser calls |

## 3. Production (`docker-compose.prod.yml` / `.env.prod`)

Compose passes: `SECRET_KEY`, `POSTGRES_PASSWORD`, `CORS_ORIGINS`, `METRICS_TOKEN`,
`EMAIL_PROVIDER`, `SMTP_*`, `RATE_LIMIT_DEFAULT`, `QDRANT_URL`, `NEXT_PUBLIC_API_URL`,
`GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD`, and image names
(`REGISTRY`, `IMAGE_BACKEND`, `IMAGE_FRONTEND`, `TAG`).

Required (compose fails fast with `:?` if missing): `SECRET_KEY`, `POSTGRES_PASSWORD`.

## 4. Secrets hygiene

- Never commit real `.env`/`.env.prod` files (they are git-ignored).
- Generate secrets: `python -c "import secrets; print(secrets.token_hex(32))"`.
- Rotate `SECRET_KEY` and SMTP credentials on personnel change or suspected leak —
  rotation invalidates existing JWTs (users re-login) and API keys must be re-issued.
- In production, prefer a secret manager (env injection) over files.

## 5. Validation

- Invalid values fail fast at startup where required (`:?` compose syntax, Pydantic
  settings validation in `app/core/config.py`).
- After changing `.env`, restart the backend (uvicorn does **not** hot-reload env).
