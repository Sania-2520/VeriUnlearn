# VeriUnlearn

![Version](https://img.shields.io/badge/version-1.0.0-22d3ee)
![Tests](https://img.shields.io/badge/tests-65%20passed-34d399)
![Coverage](https://img.shields.io/badge/coverage-78%25-34d399)
![Python](https://img.shields.io/badge/python-3.12-3776AB)
![Next.js](https://img.shields.io/badge/next.js-15-000000)
![License](https://img.shields.io/badge/license-MIT-blue)

> **VeriUnlearn** — Verifiable Machine Unlearning Framework for Privacy-Compliant AI
> (v1.0.0, Phases 1–7 complete · IEEE publication · MIT licensed)

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
  app/core/         config, security, RBAC, middleware, logging, exceptions
  app/db/           SQLAlchemy async models + session
  app/repositories/ data access layer
  app/services/     crypto, SISA, certified removal, unlearning, privacy, verification,
                    attacks, benchmark, compliance, admin, analytics, api_keys, notifications, monitoring
  app/api/v1/       REST modules (auth … admin)
  app/schemas/      Pydantic validation
  tests/            pytest suite (65 tests, one file per phase)
  alembic/          migrations (8 additive)
frontend/           Next.js 15 dashboard (20+ pages)
deploy/             nginx.conf · prometheus.yml · grafana dashboard + provisioning
contracts/          DeletionRegistry.sol (Ethereum, optional)
docs/               full guide set, IEEE paper, project report, diagrams, reports
.github/            CI/CD workflows + issue/PR templates
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
2. **Privacy Auditor** — search an identity (name, email, phone, Aadhaar, PAN,
   record/chat id; structured filters supported), scan all datasets for a
   persisted privacy report (severity + category), open any record's viewer
3. **Identity Footprint** — clusters, neurons, embeddings, influence scores,
   sensitivity, deletion eligibility
4. **Surgical Unlearning** — select records / a conversation / a dataset →
   impact analysis (affected shards, embeddings, est. retrain time) →
   embedding removal + SISA shard retraining → before/after comparison →
   deletion report persisted in unlearning history
5. **Deletion pipeline** — watch tombstoning → shard scrub → Merkle roots → certificate
6. **Verify** — signature + hash + root + audit-chain checks, download JSON/PDF
7. **Audit Trail** — hash-chained event log with tamper verification
8. **Attack Lab / Benchmark** — residual-leakage probes and method comparison
9. **Research Hub** — 6-method benchmark (Original / Full Retrain / SISA / Influence /
   Certified / VeriUnlearn) with persisted rows + CSV/JSON/Excel exports, versioned
   experiments (seeds, environment snapshots, side-by-side comparison), full attack
   suite (MIA, inversion, extraction, poisoning), research metrics (forget quality,
   privacy gain, retention, verification overhead, compliance readiness) and a live
   performance monitor

## Tests

```bash
cd backend
python -m pytest tests -q          # 65 tests, ~78% coverage — full report: docs/testing-report.md
ruff check app tests --select F,E9 # lint (clean)
cd ../frontend && npm run build    # frontend type-check + production build
```

CI runs the full suite + a dedicated benchmark job on every push/PR (`security.yml` adds
Bandit + npm audit).

## Documentation

### Guides

| Guide | Contents |
|---|---|
| [`docs/installation.md`](docs/installation.md) | Local, Docker, and production install steps |
| [`docs/configuration.md`](docs/configuration.md) | Every environment variable and recommended value |
| [`docs/developer-guide.md`](docs/developer-guide.md) | Conventions, adding endpoints/tables, testing |
| [`docs/user-manual.md`](docs/user-manual.md) | End-user walkthrough (search, unlearn, verify, export) |
| [`docs/administrator-guide.md`](docs/administrator-guide.md) | Roles, API keys, compliance evidence, backups, ops |
| [`docs/troubleshooting.md`](docs/troubleshooting.md) | Symptoms → causes → fixes |
| [`docs/faq.md`](docs/faq.md) · [`docs/glossary.md`](docs/glossary.md) | Questions and terminology |
| [`docs/best-practices.md`](docs/best-practices.md) | Security, data, ops, research practices |

### Reference & deliverables

| Document | Contents |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | System design, component/sequence/ER/deployment diagrams |
| [`docs/api.md`](docs/api.md) | Full REST endpoint reference (OpenAPI at `/docs`) |
| [`docs/deployment.md`](docs/deployment.md) | Local, Docker, production (Render/Vercel/Nginx) |
| [`docs/ieee-paper.md`](docs/ieee-paper.md) | Publication-ready IEEE paper |
| [`docs/project-report.md`](docs/project-report.md) | Academic major-project report |
| [`docs/presentation-outline.md`](docs/presentation-outline.md) | 18-slide deck with speaker notes |
| [`docs/diagrams.md`](docs/diagrams.md) | Editable Mermaid diagrams (architecture, ER, DFD, UML…) |
| [`docs/testing-report.md`](docs/testing-report.md) | 65 tests, coverage breakdown, CI status |
| [`docs/load-test-report.md`](docs/load-test-report.md) | Concurrency-ramp load test results (`backend/scripts/load_test.py`) |
| [`docs/performance-report.md`](docs/performance-report.md) | Latency, unlearning cost, optimizations |
| [`docs/research-contributions.md`](docs/research-contributions.md) | The four research contributions |
| [`docs/demo-scripts.md`](docs/demo-scripts.md) · [`docs/viva-guide.md`](docs/viva-guide.md) | 5/10/15-min demos + viva prep |
| [`docs/resume-portfolio.md`](docs/resume-portfolio.md) | Resume bullets, LinkedIn, case study |
| [`docs/release-1.0.0.md`](docs/release-1.0.0.md) | Release notes, migration notes, roadmap |
| [`docs/final-completion-summary.md`](docs/final-completion-summary.md) | Readiness checklist + deliverable index |
| [`docs/phase3-4-deliverables.md`](docs/phase3-4-deliverables.md) | Privacy Auditor + Surgical Unlearning deliverables |
| [`docs/phase5-deliverables.md`](docs/phase5-deliverables.md) | Verifiable Machine Unlearning deliverables |
| [`docs/phase6-deliverables.md`](docs/phase6-deliverables.md) | Security evaluation, benchmarking & research suite deliverables |
| [`docs/phase7-deliverables.md`](docs/phase7-deliverables.md) | Enterprise platform deliverables (admin, RBAC, monitoring, notifications, API keys, CI/CD) |

## Research Contributions

1. **Verifiable LoRA Adapter Unlearning** — per-identity adapters removed independently
   (Llama/Mistral/Phi/TinyLlama/Qwen path, optional deps)
2. **Merkle-tree Audit Verification** — tombstoned leaves make deletion roots provable
3. **Blockchain-backed Compliance Certificates** — on-chain hash anchoring (testnet)
4. **Poisoning-resistant Unlearning** — backdoor persistence evaluated before/after deletion

## Community

- [Contributing](CONTRIBUTING.md) · [Code of Conduct](CODE_OF_CONDUCT.md) · [Security Policy](SECURITY.md)
- [Changelog](CHANGELOG.md) · [License](LICENSE) (MIT)

## License

MIT — see [LICENSE](LICENSE). Research / evaluation use for the unlearning science; see
`docs/` for the IEEE paper and architecture rationale.