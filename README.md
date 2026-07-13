# VeriUnlearn

[![CI](https://github.com/Sania-2520/VeriUnlearn/actions/workflows/ci.yml/badge.svg)](https://github.com/Sania-2520/VeriUnlearn/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.13%2B-blue)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.12%2B-red)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688)](https://fastapi.tiangolo.com/)
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

## Quick Start

```bash
git clone https://github.com/Sania-2520/VeriUnlearn.git
cd VeriUnlearn
make install
docker compose up -d postgres redis qdrant minio
make db-migrate
make dev-backend    # Terminal 1 — FastAPI on :8000
make dev-frontend   # Terminal 2 — Next.js on :3000
make worker         # Terminal 3 — Celery
```

Or with Docker:
```bash
docker compose up --build
```

### Seed Demo Data
```bash
make seed
# Or: python infra/scripts/seed_demo_data.py
```

---

## Project Structure

```
veriunlearn/
├── packages/
│   ├── backend/              # FastAPI + Celery + SQLAlchemy
│   │   ├── app/
│   │   │   ├── api/v1/       # 18 route handlers
│   │   │   ├── core/         # Config, security, cache
│   │   │   ├── domain/       # Business logic (DDD)
│   │   │   └── infrastructure/ # DB, external clients
│   │   └── tests/            # 154+ tests
│   ├── ml-engine/           # PyTorch + PEFT + MLflow
│   │   ├── unlearning/       # 4 algorithms + hybrid controller
│   │   ├── training/         # LoRA, CL, benchmarks
│   │   ├── explainability/   # SHAP, LIME, IG, CF, embeddings
│   │   ├── verification/     # Merkle, zk-SNARKs, signatures
│   │   └── tests/            # 178+ tests
│   └── frontend/            # Next.js + React + Tailwind
├── infra/
│   ├── docker/              # Docker Compose (dev)
│   ├── k8s/                 # Kubernetes Helm chart
│   ├── monitoring/          # Prometheus, Grafana, Loki
│   ├── scripts/             # Benchmark, seed, graphs
│   └── terraform/           # AWS EKS provisioning
├── docs/                    # Comprehensive documentation
└── nginx/                   # Reverse proxy with security headers
```

---

## Documentation

| Guide | Description |
|---|---|
| [Architecture](docs/architecture.md) | System architecture and design decisions |
| [API Reference](docs/api-reference.md) | Full API documentation |
| [Developer Guide](docs/developer-guide.md) | Development setup and workflows |
| [Deployment Guide](docs/production-deployment.md) | Production deployment instructions |
| [Security Guide](docs/security-guide.md) | Threat model and security practices |
| [User Manual](docs/user-manual.md) | End-user documentation |
| [Contributing](docs/contributing.md) | How to contribute |
| [Troubleshooting](docs/troubleshooting-guide.md) | Common issues and solutions |
| [Research](docs/research/) | IEEE paper structure and contributions |

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

Full docs at `/api/docs` (backend running) or [docs/api-reference.md](docs/api-reference.md).

---

## Testing

```bash
make test                # All tests
cd packages/backend && pytest -v --cov=app
cd packages/ml-engine && python -m pytest tests/ -v
pytest -v -m load        # Load/performance tests
```

- **Backend**: 154 tests (auth, RBAC, audit, compliance, unlearning, verification, blockchain, security, E2E)
- **ML Engine**: 178+ tests (algorithms, lifecycle, continual learning, explainability, model registry, signatures, zk-SNARKs)
- **Coverage**: 88% overall

---

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui, Recharts |
| Backend | FastAPI, Python 3.13, SQLAlchemy 2.0, Celery, Redis |
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
