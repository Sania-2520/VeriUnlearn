# VeriUnlearn

**Verifiable Machine Unlearning Framework for Privacy-Compliant AI**

A production-grade research platform that lets AI models *selectively forget* user data while
generating **cryptographic proof that the deletion actually occurred** — built for
**GDPR Article 17 (Right to be Forgotten)** and **DPDP Act 2023** compliance.

Instead of retraining a full model per deletion request, VeriUnlearn combines **SISA training**,
**influence functions**, and **certified removal** into one pipeline, then anchors every deletion
with **Merkle-tree proofs, RSA-signed certificates, ZK-style commitments, an immutable hash-chained
audit trail**, and optional **Ethereum testnet registration**.

> This repository ships a **fully runnable vertical slice**: ingest → train sharded model → audit
> identity → selective unlearn → certificate → verify → compliance dashboard. No placeholders —
> every API is real, tested, and documented.

---

## Highlights

| Capability | What it does |
|---|---|
| **SISA Engine** | Stratified sharding, per-shard models, soft-voting aggregation, shard-only retraining |
| **Influence Functions** | Exact Hessian-based influence scores for every record (footprint + prioritised deletion) |
| **Certified Removal** | Newton-step removal (Guo et al., ICML 2020) with a provable bound on prediction drift |
| **Merkle Deletion Proofs** | Pre/post dataset roots over tombstoned record leaves |
| **Signed Certificates** | RSA-SHA256 certificates (JSON + PDF) binding roots, model state, and deleted hashes |
| **ZK-style Proofs** | Commitment-based deletion proofs that reveal hashes, never weights or data |
| **Immutable Audit Trail** | Hash-chained event log with end-to-end tamper detection |
| **Blockchain (optional)** | Certificate hashes registered to an Ethereum registry contract (`contracts/`) |
| **Attack Lab** | Membership inference, backdoor persistence, model inversion — before/after deletion |
| **Benchmark** | Original vs SISA retrain vs certified removal vs influence scrub on one holdout |
| **Compliance** | Live GDPR/DPDP scores, risk score, request tracking, certificate integrity |

## Tech Stack

- **Backend**: FastAPI (async), SQLAlchemy 2 (async), Alembic, PyJWT + bcrypt + `cryptography`
  (AES-GCM, RSA), slowapi rate limiting, structured JSON logging
- **ML**: scikit-learn (logistic regression), NumPy, with a **PEFT LoRA adapter backend** for
  Llama/Mistral/Phi/TinyLlama/Qwen behind a model registry (optional deps)
- **Databases**: SQLite (dev, zero-config) · PostgreSQL · Redis · Qdrant (config-driven)
- **Frontend**: Next.js 15 (App Router, TypeScript), Tailwind, shadcn-style UI, Framer Motion,
  React Query, Recharts, Three.js
- **Deployment**: Docker / Docker Compose, GitHub Actions CI, Render + Vercel guides, Nginx

## Repository Layout

```
backend/            FastAPI application
  app/core/         config, security, logging, exceptions
  app/db/           SQLAlchemy async models + session + repositories
  app/services/     crypto, SISA, influence, certified removal, unlearning, privacy, attacks, compliance
  app/api/v1/       REST modules (auth … admin)
  app/workers/      background unlearning runner
  tests/            pytest suite (crypto, SISA, unlearning flow, API)
  alembic/          migrations
frontend/           Next.js dashboard
contracts/          DeletionRegistry.sol (Ethereum)
docs/               architecture, API reference, deployment, IEEE paper draft
```

## Quickstart (local)

Prerequisites: Python 3.12+, Node 22+.

```bash
# 1. Backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt

# 2. Seed demo data (downloads Adult Census, trains a 4-shard SISA model)
cd backend
python -m app.seed

# 3. Run API
uvicorn app.main:app --reload        # http://localhost:8000  ·  /docs

# 4. Frontend (new terminal)
cd frontend
npm install
npm run dev                          # http://localhost:3000
```

Demo logins (created by the seed): `admin@veriunlearn.dev / admin12345`,
`operator@veriunlearn.dev / operator123`, `auditor@veriunlearn.dev / auditor123`.

### Walk the demo flow

1. **Dashboard** — compliance scores, request volume, certificate integrity
2. **Privacy Auditor** — search an identity (e.g. `maya`), open its footprint
   (clusters, neurons, embeddings, influence scores), choose a method and delete
3. **Deletion pipeline** — watch tombstoning → shard scrub → Merkle roots → certificate
4. **Verify** — signature + hash + root + audit-chain checks, download JSON/PDF
5. **Audit Trail** — hash-chained event log with tamper verification
6. **Attack Lab / Benchmark** — residual-leakage probes and method comparison

## Tests

```bash
cd backend
python -m pytest tests -q        # 15 tests: crypto, SISA, unlearning flows, API, attacks, benchmark
```

## Documentation

| Document | Contents |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | System design, component/sequence/ER/deployment diagrams |
| [`docs/api.md`](docs/api.md) | Full REST endpoint reference |
| [`docs/deployment.md`](docs/deployment.md) | Local, Docker, production (Render/Vercel/Nginx) |
| [`docs/ieee-paper.md`](docs/ieee-paper.md) | IEEE-style paper draft |
| [`docs/research-contributions.md`](docs/research-contributions.md) | The four research contributions |

## Research Contributions

1. **Verifiable LoRA Adapter Unlearning** — per-identity adapters removed independently
   (Llama/Mistral/Phi/TinyLlama/Qwen path, optional deps)
2. **Merkle-tree Audit Verification** — tombstoned leaves make deletion roots provable
3. **Blockchain-backed Compliance Certificates** — on-chain hash anchoring (testnet)
4. **Poisoning-resistant Unlearning** — backdoor persistence evaluated before/after deletion

## License

Research / evaluation use. See `docs/` for the IEEE paper draft and architecture rationale.
