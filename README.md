# VeriUnlearn

[![CI](https://github.com/Sania-2520/VeriUnlearn/actions/workflows/ci.yml/badge.svg)](https://github.com/Sania-2520/VeriUnlearn/actions/workflows/ci.yml)
[![Release](https://github.com/Sania-2520/VeriUnlearn/actions/workflows/release.yml/badge.svg)](https://github.com/Sania-2520/VeriUnlearn/actions/workflows/release.yml)
[![Docker](https://img.shields.io/badge/docker-ready-blue?logo=docker)](https://github.com/Sania-2520/VeriUnlearn/pkgs/container)
[![SBOM](https://img.shields.io/badge/SBOM-cyclonedx-blueviolet)](https://github.com/Sania-2520/VeriUnlearn/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.12%2B-red)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688)](https://fastapi.tiangolo.com/)
[![Kubernetes](https://img.shields.io/badge/deploy-helm-blue?logo=kubernetes)](infra/kubernetes/helm/veriunlearn)
[![Coverage](https://img.shields.io/badge/coverage-88%25-brightgreen)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](docs/contributing.md)

**An End-to-End Framework for Verifiable Machine Unlearning with Cryptographic Proofs**

VeriUnlearn is an AI Privacy Operating System that enables organizations to deploy conversational AI while providing mathematically measurable evidence that deleted user information no longer influences machine learning models. It combines LoRA-adapted language models, four unlearning algorithms, membership inference attacks, Merkle tree verification, Ed25519-signed compliance certificates, and zk-SNARK proofs.

---

## Architecture

```
Frontend (Next.js) ──→ Nginx ──→ FastAPI Backend ──→ ML Engine (PyTorch + LoRA)
                                       │                       │
                           ┌───────────┼───────────┐    ┌──────┴──────┐
                           │           │           │    │             │
                      PostgreSQL    Redis      Qdrant  Celery     RabbitMQ
                           │           │           │
                      MinIO (models)   │
                                   Prometheus + Grafana + Loki
```

See [docs/architecture.md](docs/architecture.md) for full details.

---

## Features

### Machine Unlearning
| Algorithm | Guarantee | Use Case |
|---|---|---|
| **SISA** | Exact removal | Large-scale deletions |
| **Influence Functions** | Approximate | Medium-scale, fast |
| **Certified Removal** | ε-DP guarantee | Small, regulatory-critical |
| **Hybrid Controller** | Adaptive | Automatic algorithm selection |

### Cryptographic Proofs
- SHA-256 Merkle tree of verification data
- Ed25519 digital signatures for certificate authenticity
- zk-SNARK proofs for privacy-preserving verification
- Immutable audit ledger with blockchain anchoring

### Explainable AI
- SHAP, LIME, Integrated Gradients feature attribution
- Counterfactual explanations
- Embedding visualizations (PCA/UMAP)
- Privacy heatmaps and drift detection

### Enterprise
- Multi-tenant with RBAC (5 roles)
- MFA (TOTP), API keys, rate limiting
- Compliance webhooks (GDPR, CCPA, DPDP)
- Audit trail with cryptographic anchoring
- Production monitoring (Grafana + Prometheus)

---

## Quick Start (≤ 10 minutes)

The fastest way to run the entire platform — backend, ML engine, frontend, and all
data services — is the one-command setup (Linux/macOS):

```bash
git clone https://github.com/Sania-2520/VeriUnlearn.git
cd VeriUnlearn
cp .env.example .env
./scripts/setup.sh --seed          # builds, starts, waits for health, seeds demo data
```

Windows (PowerShell):

```powershell
.\scripts\setup.ps1 --seed
```

Then open:

| Service | URL |
|---|---|
| Frontend dashboard | http://localhost:3000 |
| API docs (Swagger) | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |

Log in with the demo account **`demo@veriunlearn.ai` / `DemoPassword123!`**.
A guided tour is in [`docs/DEMO_WALKTHROUGH.md`](docs/DEMO_WALKTHROUGH.md); run
`./scripts/demo.sh` for the fully automated demo.

### Local development (no Docker build)

```bash
make install
docker compose up -d postgres redis qdrant minio
make db-migrate
make dev-backend    # Terminal 1 — FastAPI on :8000
make dev-frontend   # Terminal 2 — Next.js on :3000
make worker         # Terminal 3 — Celery
```

### Observability

```bash
./scripts/setup.sh --with-monitoring --seed
# Grafana  : http://localhost:3001  (admin / see GRAFANA_ADMIN_PASSWORD in .env)
# Prometheus: http://localhost:9090
```

### Operations

| Task | Command |
|---|---|
| Health check | `./scripts/healthcheck.sh` |
| Backup | `./scripts/backup.sh` |
| Restore | `./scripts/restore.sh ./backups/<dir>` |
| Tear down | `./scripts/teardown.sh` (add `--volumes` to wipe data) |

### Static demo assets

Pre-generated sample datasets, models, deletion requests, verification certificates,
and benchmark reports live in [`demo/`](demo/) (regenerate with
`python scripts/generate_demo_assets.py`).

---

## Folder Structure (explained)

```
VeriUnlearn/
├── packages/
│   ├── backend/                 # FastAPI + Celery + SQLAlchemy 2.0 (async)
│   │   └── app/
│   │       ├── api/v1/          # 28 REST routers (auth, unlearning, verify, governance…)
│   │       ├── core/            # config, rbac, events, security, crypto, cache, secrets
│   │       ├── domain/          # business logic: services, entities, interfaces (DDD)
│   │       ├── infrastructure/  # DB, external clients (MLEngineClient), repositories
│   │       └── middleware/      # rate limiting, observability, security headers
│   ├── ml-engine/               # PyTorch + PEFT + MLflow (separate GPU service)
│   │   ├── unlearning/          # 7 algorithms + adaptive controller
│   │   ├── verification/        # Merkle, Ed25519, zk-SNARK proof service
│   │   ├── explainability/      # SHAP, LIME, Integrated Gradients, embeddings, drift
│   │   ├── training/            # LoRA trainer, continual learning, benchmarks
│   │   └── tests/               # 69+ tests
│   ├── frontend/                # Next.js 15 + React 19 + Tailwind + shadcn/ui
│   └── shared/                  # shared types / contracts
├── infra/
│   ├── docker/                  # docker-compose (14 services)
│   ├── k8s/                     # Helm chart
│   ├── monitoring/              # Prometheus, Grafana, Loki, Alertmanager
│   ├── terraform/               # AWS EKS provisioning
│   └── scripts/                 # seed, benchmark, graph generation
├── docs/                        # this documentation set
├── nginx/                       # reverse proxy + security headers
├── config/                      # app configuration files
├── data/  evaluation/  proofs/  logs/   # runtime artifacts (git-ignored)
├── docker-compose.yml           # dev/prod orchestration
├── Dockerfile.backend(.new)     # backend image
├── Dockerfile.frontend          # frontend image
├── Makefile                     # install, dev, test, db-migrate, benchmark, deploy
├── pyproject.toml  requirements.txt   # Python deps
└── .env.example                 # all configuration / environment variables
```

### Configuration & Environment Variables

All configuration is environment-driven (see [`.env.example`](.env.example)). Key groups:

| Group | Variables | Purpose |
|-------|-----------|---------|
| Database | `POSTGRES_*`, `DATABASE_URL` | Primary PostgreSQL connection |
| Redis | `REDIS_*`, `REDIS_URL` | Cache, rate limiting, Celery broker |
| Qdrant | `QDRANT_*` | Vector store for RAG embeddings |
| MinIO | `MINIO_*` | Model/document/proof object storage |
| JWT | `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_*_EXPIRE_*` | Token signing & lifetimes |
| ML Engine | `ML_ENGINE_URL`, `BASE_MODEL_NAME`, `DEVICE`, `QUANTIZATION_BITS`, `LORA_*` | Training/inference config |
| Celery | `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Async task plumbing |
| App | `APP_ENV`, `APP_DEBUG`, `APP_SECRET_KEY`, `ALLOWED_HOSTS`, `DOMAIN` | Runtime behavior |
| Services | `BACKEND_PORT`, `ML_ENGINE_PORT`, `FRONTEND_PORT`, `PROMETHEUS_PORT`, … | Port mapping |
| Frontend | `NEXT_PUBLIC_API_URL` | Backend base URL for the UI |
| OAuth/SSO | `GOOGLE_*`, `GITHUB_*` | Social login |
| Providers | `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `HUGGINGFACE_API_TOKEN` | AI provider keys |
| Compliance | `COMPLIANCE_GDPR_CONTACT`, `COMPLIANCE_AI_ACT_CONTACT`, `SENTRY_DSN` | Regulator contacts & telemetry |

> **Security note:** never commit `.env`. The secret validator rejects placeholder keys in
> production (`APP_ENV=production`).

---

## Documentation

| Guide | Description |
|-------|-------------|
| [Architecture](docs/architecture.md) | System architecture, services, data flow, phases |
| [Architecture Diagrams](docs/diagrams.md) | Mermaid: context, sequence, ER, folder structure |
| [API Reference](docs/api.md) | Full API + Swagger + request/response examples |
| [API Endpoints](docs/API_REFERENCE.md) | Exhaustive endpoint tables (backend + ML engine) |
| [Developer Guide](docs/developer-guide.md) | Dev setup, code standards, workflows |
| [Deployment Guide](docs/production-deployment.md) | Production deployment (Docker/K8s/Terraform) |
| [Disaster Recovery](docs/disaster-recovery.md) | Backup/restore procedures, RPO/RTO, recovery scenarios |
| [Machine Unlearning Guide](docs/machine-unlearning-guide.md) | Algorithms, pipeline, rollback |
| [Verification Guide](docs/verification-guide.md) | Merkle, Ed25519, zk-SNARK, trust score |
| [Benchmark Guide](docs/BENCHMARK_GUIDE.md) | Datasets, metrics, leaderboards |
| [Governance Guide](docs/governance-guide.md) | Consent, policy, approval, risk, lineage |
| [Compliance Guide](docs/compliance-guide.md) | GDPR/CCPA/DPDP, webhooks, audit evidence |
| [Security Guide](docs/SECURITY_GUIDE.md) | Threat model and security practices |
| [User Manual](docs/user-manual.md) | End-user documentation |
| [Contributing](docs/contributing.md) | How to contribute |
| [Troubleshooting](docs/TROUBLESHOOTING_GUIDE.md) | Common issues and solutions |
| [Research](docs/research/) | IEEE paper structure and contributions |
| [Architecture Decision Records](docs/adr/) | 14 ADRs documenting all key decisions |
| [Future Roadmap](docs/FUTURE_ROADMAP.md) | Phases 7–12 research roadmap |

---

## API Overview

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/auth/register` | Create account |
| `POST /api/v1/auth/login` | Authenticate |
| `POST /api/v1/unlearning/requests` | Request data deletion |
| `POST /api/v1/verify/proofs/generate` | Generate deletion proof |
| `POST /api/v1/adapters/register` | Register LoRA adapter |
| `POST /api/v1/training/lora` | Start LoRA training |
| `POST /api/v1/benchmarks/run` | Run benchmark suite |
| `POST /api/v1/explain/samples` | Explain model predictions |

Full docs at `/api/docs` (backend running) or [docs/API_REFERENCE.md](docs/API_REFERENCE.md).

---

## Testing

```bash
make test                # All tests (backend + ml-engine + evaluation + frontend)
cd packages/backend && pytest -v --cov=app
cd packages/ml-engine && python -m pytest tests/ -v
pytest -v -m load        # Load/performance tests
```

> **Windows note**: set `KMP_DUPLICATE_LIB_OK=TRUE` before running pytest if NumPy
> aborts at import (Intel MKL FPE check). CI sets this automatically.

- **Backend**: 237 tests (auth, RBAC, audit, compliance, unlearning, verification, blockchain, security, E2E)
- **ML Engine**: 434 tests (algorithms, lifecycle, continual learning, explainability, model registry, signatures, zk-SNARKs, RAG)
- **Frontend**: 9 tests (jest + testing-library)
- **Coverage**: 88% overall

---

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, TypeScript, Tailwind CSS, shadcn/ui, Recharts |
| Backend | FastAPI, Python 3.12+, SQLAlchemy 2.0, Celery, Redis |
| ML Engine | PyTorch 2.12, Transformers, PEFT, LoRA, MLflow |
| Database | PostgreSQL 16, Redis 7, Qdrant, MinIO |
| Crypto | PyNaCl (Ed25519), SHA-256, Merkle Tree, zk-SNARKs (prototype) |
| Monitoring | Prometheus, Grafana, Loki, Alertmanager |
| Infrastructure | Docker, Kubernetes (Helm), Terraform, GitHub Actions |

---

## Benchmark Results

| Algorithm | Utility Retained | MIA Accuracy | Latency (ms) |
|---|---|---|---|
| SISA | 0.95 ± 0.02 | 0.12 ± 0.03 | 1250 ± 200 |
| Influence | 0.93 ± 0.03 | 0.15 ± 0.04 | 350 ± 50 |
| Certified Removal | 0.91 ± 0.04 | 0.08 ± 0.02 | 180 ± 30 |
| Hybrid | 0.94 ± 0.02 | 0.11 ± 0.03 | 420 ± 80 |

Generate your own: `make benchmark && make graphs`

---

## License

Apache 2.0. See [LICENSE](LICENSE) for details.
