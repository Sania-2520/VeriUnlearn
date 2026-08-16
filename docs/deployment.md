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

## 7. CI

`.github/workflows/ci.yml` runs backend `pytest` and the frontend production build on every push/PR.
