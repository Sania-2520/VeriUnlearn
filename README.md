# VeriUnlearn — Verifiable Machine Unlearning Framework

**Cryptographic Proofs for GDPR-Compliant AI Systems**

[![CI Pipeline](https://github.com/veriunlearn/veriunlearn/actions/workflows/ci.yml/badge.svg)](https://github.com/veriunlearn/veriunlearn/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com/)

---

## Overview

VeriUnlearn is a production-grade enterprise platform that enables organizations to honor the **GDPR "Right to be Forgotten"** with **cryptographic guarantees**. When a user deletes data, VeriUnlearn ensures every trace is removed — from databases and vector stores to ML model influence — and generates a **verifiable cryptographic proof** of deletion.

### Key Capabilities

| Capability | Description |
|---|---|
| **Multi-Model AI Chat** | Streaming chat with OpenAI, Anthropic, Google, Azure, Ollama, vLLM, HuggingFace |
| **Machine Unlearning** | SISA, Influence Functions, Certified Removal, Hybrid Adaptive Controller |
| **Verifiable Deletion** | Merkle trees, Ed25519 signatures, zkSNARK-ready proof generation |
| **RAG Engine** | Multi-format document ingestion, hybrid retrieval, citation generation |
| **Memory System** | Tiered memory (session/persistent/user/workspace), configurable retention |
| **Security Engine** | Membership inference, model extraction, privacy leakage testing |
| **Immutable Audit** | Merkle chain audit log, blockchain-ready anchoring |
| **Compliance Dashboard** | GDPR, AI Act, DPDP compliance reports and risk scoring |

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   VeriUnlearn Platform                        │
│                                                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │ Chat      │  │ Unlearning│  │ Verification│  │ Compliance   │ │
│  │ Service   │  │ Engine   │  │ Engine     │  │ Dashboard    │ │
│  └────┬─────┘  └────┬─────┘  └─────┬──────┘  └──────┬───────┘ │
│       │              │              │                  │         │
│  ┌────┴──────────────┴──────────────┴──────────────────┴──────┐ │
│  │                    Data Layer                                │ │
│  │  PostgreSQL | Redis | Qdrant | MinIO | EventStoreDB        │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+
- Node.js 22+
- Make (optional)

### Development Setup

```bash
# Clone and enter the repository
git clone https://github.com/veriunlearn/veriunlearn.git
cd veriunlearn

# Copy environment variables
cp .env.example .env

# Start all services
docker compose -f infra/docker/docker-compose.yml up -d

# Apply database migrations
docker compose exec backend alembic upgrade head

# Access the platform
# Frontend: http://localhost:3000
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Grafana: http://localhost:3001 (admin/admin)
```

### Manual Setup

```bash
# Backend
cd packages/backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend
cd packages/frontend
npm install
npm run dev

# ML Engine
cd packages/ml-engine
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn api:app --reload --port 8001
```

---

## Project Structure

```
veriunlearn/
├── packages/
│   ├── backend/           # FastAPI REST API
│   │   ├── app/
│   │   │   ├── api/       # Route handlers (v1/)
│   │   │   ├── core/      # Config, security, database, cache
│   │   │   ├── domain/    # Business entities, interfaces, services
│   │   │   ├── infrastructure/ # DB models, external adapters
│   │   │   └── workers/   # Celery async tasks
│   │   ├── alembic/       # Database migrations
│   │   └── tests/
│   ├── frontend/          # Next.js 15 / React 19 UI
│   │   ├── src/
│   │   │   ├── app/       # App router pages
│   │   │   ├── components/ # UI, chat, admin components
│   │   │   └── lib/       # API client, utilities, types
│   │   └── public/
│   └── ml-engine/         # Python ML + cryptography
│       ├── unlearning/    # SISA, influence, certified removal, HAUC
│       ├── verification/  # Merkle trees, Ed25519, zkSNARK
│       ├── security/      # Privacy attack simulations
│       └── tests/
├── infra/
│   ├── docker/            # Docker Compose configuration
│   ├── kubernetes/        # K8s manifests + Helm charts
│   ├── terraform/         # IaC for AWS/GCP/Azure
│   └── monitoring/        # Prometheus, Grafana, Loki configs
├── docs/
│   ├── architecture/      # System architecture, database schema
│   ├── api/              # API contracts and documentation
│   ├── deployment/       # Deployment guides
│   ├── security/         # Threat model, security policies
│   └── research/         # Research contributions
└── .github/workflows/    # CI/CD pipelines
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 15, React 19, TypeScript, TailwindCSS, Shadcn UI, Framer Motion |
| **Backend** | FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2 |
| **ML Engine** | PyTorch, Transformers, Sentence Transformers, PEFT, Scikit-learn |
| **Databases** | PostgreSQL 16, Redis 7, Qdrant, MinIO |
| **Queue** | Celery, RabbitMQ |
| **Auth** | JWT (RS256), OAuth 2.0 (Google, GitHub), bcrypt |
| **Cryptography** | Merkle Trees (SHA-256), Ed25519, zkSNARK-ready |
| **Observability** | Prometheus, Grafana, Loki, OpenTelemetry, Sentry |
| **Infrastructure** | Docker, Kubernetes, Terraform, Helm |
| **CI/CD** | GitHub Actions, Trivy, Semgrep, Gitleaks |

---

## API Overview

| Domain | Base Path | Description |
|---|---|---|
| Auth | `/api/v1/auth` | Login, register, OAuth, email verification |
| Chat | `/api/v1/chat` | Conversations, streaming, folders, export |
| AI Providers | `/api/v1/providers` | Multi-model provider management |
| RAG | `/api/v1/rag` | Document upload, search, chunking |
| Memory | `/api/v1/memory` | Tiered memory management |
| Unlearning | `/api/v1/unlearning` | Deletion requests, queue, algorithms |
| Verification | `/api/v1/verify` | Proof generation and verification |
| Security | `/api/v1/security` | Privacy attack assessments |
| Audit | `/api/v1/audit` | Immutable event log |
| Compliance | `/api/v1/compliance` | GDPR/AI Act reports, certificates |
| Admin | `/api/v1/admin` | User management, monitoring, analytics |

---

## Machine Unlearning

VeriUnlearn implements four unlearning strategies plus a hybrid adaptive controller:

1. **SISA** (Sharded, Isolated, Sliced, Aggregated) — Exact unlearning with shard retraining
2. **Influence Functions** — Fast approximate unlearning via Hessian-based influence estimation
3. **Certified Removal** — (ε, δ)-differential privacy guarantee
4. **Approximate Unlearning** — Efficient gradient-based approximate removal
5. **Hybrid Adaptive Controller** — Dynamically selects optimal strategy based on context

---

## Verification & Proofs

Every deletion operation generates a **Verifiable Deletion Proof**:

1. **Merkle Tree** — Cryptographic commitment to all deletion steps
2. **Ed25519 Signature** — Non-repudiation of deletion
3. **Deletion Certificate** — X.509-style certificate for legal evidence
4. **zkSNARK (optional)** — Privacy-preserving proof verification

---

## Deployment

### Production (Kubernetes)

```bash
# Set up infrastructure
kubectl create namespace veriunlearn-production
helm install postgresql bitnami/postgresql --namespace veriunlearn-production
helm install redis bitnami/redis --namespace veriunlearn-production

# Deploy VeriUnlearn
helm upgrade --install veriunlearn ./infra/kubernetes/helm \
  --namespace veriunlearn-production \
  --values ./infra/kubernetes/helm/values/production.yaml
```

### Cloud Providers

- **AWS**: EKS, RDS, ElastiCache, S3 (Terraform modules in `infra/terraform/`)
- **GCP**: GKE, Cloud SQL, Memorystore, GCS
- **Azure**: AKS, Azure SQL, Redis Cache, Blob Storage

---

## Security

- **Zero-trust architecture** with mTLS between services
- **AES-256 encryption** at rest, TLS 1.3 in transit
- **JWT + OAuth 2.0** authentication with short-lived tokens
- **RBAC** with role hierarchy (admin, compliance, auditor, member, viewer)
- **Immutable audit trail** with Merkle chain verification
- **Automated security scanning** (SAST, DAST, dependency, container)
- **Incident response plan** with defined severity levels

---

## License

Apache 2.0 — See [LICENSE](LICENSE) for details.

---

## Research

VeriUnlearn contributes four novel research directions:

1. **Hybrid Adaptive Unlearning Controller** — Dynamic strategy selection
2. **Verifiable Deletion Proof System** — Multi-layer cryptographic proofs
3. **Privacy-Preserving Audit Trail** — Merkle chain + blockchain anchoring
4. **Unlearning-Aware Model Architecture** — Efficient SISA sharding + influence pre-computation

---

## Team

- **Research**: ICML, IEEE S&P, CCS, MLSys (publications planned 2026)
- **Engineering**: Production-grade SaaS platform
- **Compliance**: GDPR, AI Act, DPDP, SOC 2, ISO 27001

---

*Built for enterprises that take privacy seriously.*
