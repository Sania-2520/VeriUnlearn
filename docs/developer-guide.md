# Developer Guide — VeriUnlearn

## Prerequisites

- Python 3.13+ (backend)
- Node.js 22+ (frontend)
- Docker Desktop 4.30+ with WSL2
- NVIDIA GPU with CUDA 12.4+ (ML Engine)
- Git 2.40+

## Quick Start

```bash
# Clone and enter
git clone https://github.com/Sania-2520/VeriUnlearn.git
cd VeriUnlearn

# Install dependencies
make install

# Start infrastructure
docker compose up -d postgres redis qdrant minio

# Run database migrations
make db-migrate

# Start backend (terminal 1)
make dev-backend

# Start frontend (terminal 2)
make dev-frontend

# Start Celery worker (terminal 3)
make worker
```

## Project Structure

```
veriunlearn/
├── packages/
│   ├── backend/          # FastAPI + Celery + SQLAlchemy
│   │   ├── app/
│   │   │   ├── api/      # API routes (v1)
│   │   │   ├── core/     # Config, security, cache
│   │   │   ├── domain/   # Business logic (DDD)
│   │   │   └── infrastructure/  # DB, external clients
│   │   └── tests/        # Pytest test suite
│   ├── ml-engine/        # PyTorch + PEFT + MLflow
│   │   ├── explainability/
│   │   ├── training/     # LoRA, CL, benchmarks
│   │   ├── unlearning/   # SISA, Influence, Certified
│   │   ├── verification/ # Merkle, zk-SNARKs
│   │   └── tests/
│   └── frontend/         # Next.js + React
├── infra/
│   ├── docker/           # Docker Compose files
│   ├── k8s/              # Kubernetes manifests
│   ├── monitoring/       # Prometheus, Grafana, Loki
│   ├── scripts/          # Benchmark, seed, graph
│   └── terraform/        # AWS EKS provisioning
├── docs/                 # Documentation
└── nginx/                # Reverse proxy config
```

## Code Standards

- **Python**: Follow PEP 8, use type hints everywhere, use `ruff` for linting
- **TypeScript**: Use strict mode, prefer interfaces over types
- **Imports**: Group as stdlib → third-party → local, no wildcard imports
- **Error handling**: Use custom exception classes, always log with context
- **Async**: Use async/await for I/O, `asyncio.to_thread` for CPU-bound work
- **Testing**: Write tests first (TDD), aim for 90%+ coverage
- **Logging**: Use `get_logger(__name__)` from `app.core.logging`

## Running Tests

```bash
# Backend tests
cd packages/backend
pytest -v --tb=short

# ML Engine tests
cd packages/ml-engine
python -m pytest tests/ -v

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Load tests
pytest -v -m load
```

## Adding a New API Endpoint

1. Create or extend a router in `packages/backend/app/api/v1/`
2. Register it in `__init__.py`
3. Add Pydantic models for request/response
4. Add the corresponding method in the ML engine client (if proxying)
5. Add tests in `packages/backend/tests/`
6. Run lint + typecheck + tests

## Adding a New ML Engine Module

1. Create the module under `packages/ml-engine/` (e.g., `training/new_module.py`)
2. Add to `api.py` with a lazy singleton factory
3. Register FastAPI endpoints
4. Add tests in `packages/ml-engine/tests/`
5. Run the ML engine test suite

## Commit Convention

```
<type>: <description>

Types: feat, fix, refactor, test, docs, chore, perf, security
```

## CI/CD Pipeline

- **CI** (`.github/workflows/ci.yml`): Lint → TypeCheck → Test (backend + ML engine + frontend) → Docker Build → Security Scan
- **CD** (`.github/workflows/cd.yml`): Deploy to EKS on main merge
