# VeriUnlearn

![Version](https://img.shields.io/badge/version-1.0.0-22d3ee)
![Python](https://img.shields.io/badge/python-3.12-3776AB)
![Next.js](https://img.shields.io/badge/next.js-15-000000)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688)
![License](https://img.shields.io/badge/license-MIT-blue)

> **Verifiable Machine Unlearning for Privacy-Compliant AI**

VeriUnlearn is a production-grade framework that lets AI models **selectively forget** user data
while generating **cryptographic proof that the deletion actually happened** — built for
**GDPR Article 17 (Right to be Forgotten)** and **DPDP Act 2023** compliance.

Instead of retraining an entire model for every deletion request, VeriUnlearn combines
**SISA training**, **influence functions**, and **certified removal** into a single pipeline,
then anchors every deletion with **Merkle-tree proofs, RSA-signed certificates, and an immutable
hash-chained audit trail** — with optional Ethereum testnet registration.

The repository ships a fully runnable application: **ingest → train sharded model → audit an
identity → selectively unlearn → certificate → verify → compliance dashboard.** No placeholders —
every API is real, tested, and documented.

---

## About

VeriUnlearn addresses a real compliance problem: when a user asks to be forgotten, you must
prove the data is gone. The platform provides a complete, auditable answer.

**Core capabilities**

- **SISA Engine** — stratified sharding, per-shard models, soft-voting aggregation, shard-only retraining
- **Influence Functions** — exact Hessian-based influence scores for every record
- **Certified Removal** — Newton-step removal (Guo et al., ICML 2020) with a provable drift bound
- **Verifiable Proofs** — Merkle deletion roots, RSA-SHA256 certificates (JSON + PDF), ZK-style commitments
- **Immutable Audit Trail** — hash-chained event log with end-to-end tamper detection
- **Privacy Auditor** — search any identity across all shards, view its footprint, and surgically prune it
- **Assistant Chat** — permanent per-user chat history with sensitive-data detection and one-click pruning
- **Compliance Dashboard** — live GDPR/DPDP scores, risk scoring, request tracking, certificate integrity

**Tech stack**

- **Backend** — FastAPI (async), SQLAlchemy 2 (async), Alembic, PyJWT + bcrypt, AES-GCM/RSA
  cryptography, slowapi rate limiting, structured JSON logging
- **Machine Learning** — scikit-learn, NumPy, with an optional PEFT LoRA adapter backend
- **Frontend** — Next.js 15 (App Router, TypeScript), Tailwind CSS, Framer Motion, React Query, Recharts
- **Data** — SQLite for zero-config development; PostgreSQL, Redis, and Qdrant for production

---

## Installation

### Prerequisites

- **Python 3.12+**
- **Node.js 22+**
- **Docker + Docker Compose** (Docker method only)
- **Git**

### Option 1 — Local installation

#### Backend

```bash
# 1. Clone the repository
git clone https://github.com/Sania-2520/VeriUnlearn.git
cd VeriUnlearn

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install Python dependencies
pip install -r backend/requirements.txt

# 4. Configure the environment
cd backend
cp .env.example .env        # Windows: copy .env.example .env
# Optionally edit .env — set LLM_BASE_URL, LLM_API_KEY, LLM_MODEL to enable the chat assistant
```

#### Frontend

```bash
# In a new terminal, from the project root
cd frontend
npm install
```

### Option 2 — Docker installation

```bash
git clone https://github.com/Sania-2520/VeriUnlearn.git
cd VeriUnlearn

# Configure the backend environment
cd backend && cp .env.example .env && cd ..

# Build and start the stack (backend on :8000, frontend on :3000)
docker compose up --build
```

The Docker images run database migrations automatically on startup and expose:

- Frontend → http://localhost:3000
- Backend API → http://localhost:8000
- Interactive API docs → http://localhost:8000/docs

---

## How to Run

### 1. Start the backend

```bash
cd backend
alembic upgrade head     # apply database migrations
python -m app.seed       # download demo data + train a 4-shard SISA model
uvicorn app.main:app --reload
```

The API is now live at http://localhost:8000 with interactive docs at http://localhost:8000/docs.

### 2. Start the frontend

```bash
cd frontend
npm run dev
```

Open http://localhost:3000 in your browser.

### 3. Log in

Use one of the seeded demo accounts:

| Role     | Email                      | Password      |
|----------|----------------------------|---------------|
| Admin    | `admin@veriunlearn.dev`    | `admin12345`  |
| Operator | `operator@veriunlearn.dev` | `operator123` |
| Auditor  | `auditor@veriunlearn.dev`  | `auditor123`  |

> **Note:** The Assistant chat requires an OpenAI-compatible LLM provider. Set
> `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` in `backend/.env`. Without it,
> the rest of the platform runs normally; only live chat streaming is disabled.

---

## Get Involved

We'd love to hear from you — whether you have a question, found a bug, want to discuss the
research, or would like to contribute.

- **Questions & feedback** — open an [issue](https://github.com/Sania-2520/VeriUnlearn/issues)
- **Contributions** — fork the repo and open a [pull request](https://github.com/Sania-2520/VeriUnlearn/pulls)
- **Security concerns** — please review our [Security Policy](SECURITY.md) before reporting
- **Code of conduct** — see [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- **License** — MIT, see [LICENSE](LICENSE)

Happy unlearning! 🧠🔒