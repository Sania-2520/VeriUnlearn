# VeriUnlearn

**An End-to-End Framework for Verifiable Machine Unlearning with Cryptographic Proofs for Privacy-Preserving Conversational AI**

VeriUnlearn is an AI Privacy Operating System that enables organizations to deploy conversational AI while providing mathematically measurable evidence that deleted user information no longer influences machine learning models. It combines LoRA-adapted language models, SISA and influence-based unlearning, membership inference attacks, Merkle tree verification, and Ed25519-signed compliance certificates.

---

## Quick Start

### Prerequisites

- Python 3.13+
- Node.js 22+
- Docker & Docker Compose (for production services)
- NVIDIA GPU with CUDA (recommended, CPU fallback supported)

### Development Setup

```bash
# Clone and enter the repo
git clone https://github.com/mantexia/veriunlearn.git
cd veriunlearn

# Install dependencies
make install

# Start infrastructure (PostgreSQL, Redis, Qdrant, MinIO)
docker compose up -d postgres redis qdrant minio

# Run database migrations
make db-migrate

# Start backend (FastAPI on :8000)
make dev-backend

# Start frontend (Next.js on :3000, in another terminal)
make dev-frontend
```

### Full Stack with Docker

```bash
docker compose up --build
```

Access:
- Frontend: http://localhost:3000
- API: http://localhost:8000/api/docs
- Metrics: http://localhost:8000/metrics

---

## Architecture

VeriUnlearn follows Clean Architecture with six bounded contexts:

```
Frontend (Next.js) ──→ Nginx ──→ FastAPI Backend
                                      │
                          ┌───────────┼───────────┐
                          │           │           │
                     PostgreSQL    Redis      Qdrant
                          │           │           │
                     MinIO (models)   │           │
                                      │
                                 Celery Worker
                                      │
                               PyTorch + LoRA
```

See [docs/architecture.md](docs/architecture.md) for full details.

---

## Core Capabilities

### Conversational AI
- Chat interface with LoRA-adapted language models
- RAG with Qdrant vector store
- Streaming responses

### Machine Unlearning
- **SISA**: Sharded retraining with exact removal guarantees
- **Influence Functions**: Approximate removal for medium-scale deletions
- **Certified Removal**: Formal guarantees for small deletions
- **Adaptive Controller**: Automatic algorithm selection

### Verification
- Membership Inference Attacks (before vs. after deletion)
- Utility retention evaluation
- Weight distance, gradient distance, cosine similarity analysis

### Cryptographic Proofs
- SHA-256 Merkle tree of verification data
- Ed25519 digital signature
- Signed compliance certificates with QR codes
- Immutable audit ledger

### Compliance Dashboard
- Deletion request lifecycle tracking
- MIA metric comparison
- Certificate download
- Audit trail

---

## Project Structure

```
veriunlearn/
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── api/v1/       # Route handlers
│   │   ├── core/         # Config, security, logging
│   │   ├── crypto/       # Merkle, signing, certificates
│   │   ├── db/           # Database session, base models
│   │   ├── ml/           # ModelManager, Trainer, Inference
│   │   │   ├── unlearning/   # SISA, Influence, Certified, Adaptive
│   │   │   └── verification/ # MIA, Utility evaluation
│   │   ├── models/       # SQLAlchemy ORM (12 tables)
│   │   ├── schemas/      # Pydantic request/response
│   │   ├── services/     # Business logic
│   │   ├── tests/        # Unit & integration tests
│   │   └── worker/       # Celery task definitions
│   └── alembic/          # Database migrations
├── frontend/             # Next.js application
│   ├── app/              # Pages (workspace, compliance, privacy)
│   ├── lib/              # API client with token refresh
│   └── store/            # Zustand auth store
├── config/               # YAML system settings
├── docs/                 # Architecture, risks, requirements
├── nginx/                # Reverse proxy configuration
├── proofs/               # Compliance certificates
└── docker-compose.yml    # Multi-service orchestration
```

---

## API Overview

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/auth/register` | Create account |
| `POST /api/v1/auth/login` | Authenticate |
| `POST /api/v1/chat/conversations` | Start conversation |
| `POST /api/v1/chat/conversations/{id}/messages` | Send message |
| `POST /api/v1/training/datasets` | Create training dataset |
| `POST /api/v1/training/start` | Start LoRA training |
| `POST /api/v1/unlearning/requests` | Request data deletion |
| `GET /api/v1/unlearning/requests/{id}/result` | Get verification result |

Full API documentation at `/api/docs` when the backend is running.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui, TanStack Query, Zustand, Framer Motion |
| Backend | FastAPI, Python 3.13, SQLAlchemy 2.0, Celery |
| Database | PostgreSQL 16, Redis 7, Qdrant, MinIO |
| ML | PyTorch, Transformers, PEFT, LoRA, Sentence Transformers, scikit-learn |
| Crypto | PyNaCl (Ed25519), SHA-256, Merkle Tree |
| Observability | Prometheus, Grafana, OpenTelemetry, Loguru |
| Infrastructure | Docker, Docker Compose, Nginx |

---

## Development

```bash
make help         # Available commands
make install      # Install all dependencies
make dev          # Start full development environment
make test         # Run all tests
make lint         # Lint all code
make db-migrate   # Run database migrations
make build        # Build Docker images
```

---

## Testing

```bash
make test          # Run full test suite
make test-unit     # Unit tests only
make test-int      # Integration tests only
```

Tests cover authentication, chat, and end-to-end unlearning flows. ML validation tests verify model training and unlearning integrity.

---

## Documentation

| Document | Description |
|---|---|
| [docs/requirements.md](docs/requirements.md) | Functional and non-functional requirements |
| [docs/architecture.md](docs/architecture.md) | System architecture and design decisions |
| [docs/risks.md](docs/risks.md) | Risk identification and mitigation |
| `config/settings.yaml` | System configuration |

---

## Deployment

```bash
docker compose -f docker-compose.yml up --build -d
```

For Kubernetes, see `k8s/` directory (coming soon).

Supported cloud providers: AWS, Azure, GCP (Terraform modules coming soon).

---

## License

Proprietary — Mantexia Solutions. All rights reserved.

---

## Research

VeriUnlearn is designed for academic reproducibility. All experiments can be reproduced using:
1. The `backend/app/ml/unlearning/` algorithm implementations
2. The verification pipeline in `backend/app/services/unlearning_service.py`
3. The cryptographic proof system in `backend/app/crypto/`

Metrics collected per unlearning operation include accuracy, precision, recall, F1, loss, weight distance, gradient distance, cosine similarity, influence score, MIA attack success rate, and privacy leakage.
