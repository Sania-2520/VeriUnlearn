# VeriUnlearn Architecture Guide

## System Overview

VeriUnlearn employs a **4-layer architecture** — Presentation, Application, Domain, and Infrastructure — designed for verifiable machine unlearning with cryptographic proofs. The system is organized as a set of loosely-coupled services communicating via REST APIs, message queues, and an in-process event bus.

```
┌─────────────────────────────────────────────────────────────┐
│                   PRESENTATION LAYER                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Next.js 15 + React 19 + Tailwind + shadcn/ui        │   │
│  │  Dashboard, User Management, Verification Reports,   │   │
│  │  Benchmark Visualizations, Governance Console         │   │
│  └──────────────┬───────────────────────────────────────┘   │
├─────────────────┼───────────────────────────────────────────┤
│                 │ HTTPS                                     │
│                 ▼                                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Nginx Reverse Proxy (TLS, rate limiting, headers)    │   │
│  └──────────────┬───────────────────────────────────────┘   │
│                 ▼                                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              APPLICATION LAYER                        │   │
│  │  FastAPI Backend (Uvicorn) + Celery Workers           │   │
│  │  28 REST routers (v1 + v2), 55 domain services,      │   │
│  │  Middleware (CORS, rate limiting, observability)      │   │
│  └──────────────┬───────────────────────────────────────┘   │
├─────────────────┼───────────────────────────────────────────┤
│                 │ HTTP + Message Queue                       │
│                 ▼                                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │               DOMAIN LAYER                            │   │
│  │  SQLAlchemy 2.0 models (47+ entities), Pydantic v2    │   │
│  │  Business logic: Unlearning, Verification, Governance,│   │
│  │  Compliance, RBAC, Audit, Crypto (Ed25519/Merkle/zk)  │   │
│  └──────────────┬───────────────────────────────────────┘   │
├─────────────────┼───────────────────────────────────────────┤
│                 │ SQL / HTTP / gRPC                          │
│                 ▼                                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │             INFRASTRUCTURE LAYER                      │   │
│  │  PostgreSQL 16  Redis 7  Qdrant  MinIO  Prometheus    │   │
│  │  Grafana  Loki  Alertmanager  MLflow  RabbitMQ        │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Layer Descriptions

### 1. Presentation Layer

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Web Dashboard | Next.js 15 + React 19 | UI for unlearning requests, verification, governance, benchmarks |
| Component Library | shadcn/ui + Tailwind CSS | Accessible, themeable UI components |
| State Management | Zustand | Client-side state for real-time updates |
| Data Visualization | Recharts, D3 | Trust scores, benchmark comparisons, drift charts |

### 2. Application Layer

**Two API versions** coexist on the FastAPI application:

**v1 (17 routers)** — RESTful CRUD for core entities:
- `auth`, `chat`, `training`, `unlearning`, `documents`, `admin`, `api_keys`
- `gdpr`, `usage`, `webhooks`, `backup`, `registry`, `experiments`, `datasets`
- `training_jobs`, `inference`, `dashboard`

**v2 (5 engine routers)** — Orchestration workflows:
- `unlearning_engine` — Deletion request → algorithm selection → execution → verification
- `verification_engine` — Cryptographic proof generation, certificate issuance, trust scoring
- `governance_engine` — Consent lifecycle, policy evaluation, compliance, approvals, risk
- `mlops_engine` — Experiment tracking, model serving, observability
- `research_engine` — Benchmarks, algorithm registry, privacy attacks, leaderboards

**Celery Workers** handle asynchronous tasks:
- `execute_unlearning` — Long-running unlearning operations
- `generate_deletion_proof` — Cryptographic proof computation
- `webhook_delivery` — Retry-capable webhook dispatch
- `audit.anchor_chains` — Periodic blockchain anchoring (every 6 hours)

### 3. Domain Layer

The domain layer encapsulates business logic across 55+ services organized by domain:

| Domain | Key Services | Responsibilities |
|--------|-------------|------------------|
| Auth & Identity | `AuthService`, `ApiKeyService` | Registration, JWT, OAuth, MFA, API key management |
| Training & Models | `TrainingService`, `ModelRegistryService`, `InferenceService` | LoRA training, model versioning, inference |
| Unlearning | `UnlearningService`, `UnlearningPipeline`, `CheckpointService` | Algorithm orchestration, checkpoints, rollback |
| Verification | `VerificationService`, `CertificateService`, `TrustScoreService` | Proof generation, certificate signing, scoring |
| Governance | `ConsentService`, `PolicyService`, `ComplianceService`, `ApprovalService` | Consent lifecycle, policy engine, regulatory workflows |
| Audit | `AuditService`, `EnhancedAuditService` | Tamper-evident hash chain, blockchain anchoring |
| Research | `BenchmarkService`, `LeaderboardService`, `PrivacyAttackService` | Algorithm comparison, MIA simulation, leaderboards |

### 4. Infrastructure Layer

| Component | Role | Deployment |
|-----------|------|-----------|
| PostgreSQL 16 | Primary data store | Container or managed RDS |
| Redis 7 | Cache, Celery broker, rate limiter | Container or ElastiCache |
| Qdrant | Vector store for RAG embeddings | Container or Qdrant Cloud |
| MinIO | Object store (models, proofs, certificates) | Container or S3-compatible |
| Prometheus + Grafana + Loki | Metrics, dashboards, log aggregation | Container or Grafana Cloud |
| MLflow | Experiment tracking | Embedded in ML Engine |
| RabbitMQ | Alternative message broker | Container |

---

## Data Flow

### End-to-End Unlearning & Verification Flow

```
User/Frontend → Backend API → Celery Worker → ML Engine → Verification → Certificate
     │              │              │               │             │              │
     │  1. POST /unlearning/requests               │             │              │
     │─────────────────►                            │             │              │
     │                  │ 2. Validate target        │             │              │
     │                  │ 3. Create checkpoint      │             │              │
     │                  │ 4. Enqueue task           │             │              │
     │                  │──────────►                │             │              │
     │                                 │ 5. Select algorithm    │              │
     │                                 │ 6. POST /unlearn       │              │
     │                                 │──────────►              │              │
     │                                 │            │ 7. Execute │              │
     │                                 │            │ 8. Return  │              │
     │                                 │◄───────────              │              │
     │                                 │ 9. Trigger verification │              │
     │                                 │────────────────────────►│              │
     │                                 │              │ 10. Run 5 strategies    │
     │                                 │              │ 11. Compute trust score │
     │                                 │              │ 12. Sign certificate    │
     │                                 │              │──────────►              │
     │                                 │              │              │ 13. Store │
     │ 14. Poll/Webhook result         │              │              │           │
     │◄────────────────────────────────│              │              │           │
     │ 15. Display certificate         │              │              │           │
```

### Data Flow by Phase

| Phase | Input | Process | Output |
|-------|-------|---------|--------|
| Dataset Upload | Raw data files | Chunking, embedding, versioning | Stored dataset + vector index |
| Training | Dataset + base model | LoRA fine-tuning (Celery) | Adapter + model hash + metrics |
| Unlearning | Target IDs + algorithm choice | Adaptive selection → execution | Before/after model hashes, new adapter |
| Verification | Model hashes + artifacts | 5 strategies + trust aggregation | Trust score + certificate |
| Governance | Consent + policy rules | Event-driven evaluation | Compliance report + audit record |
| Benchmark | Dataset + algorithm config | N trials × metrics | Leaderboard + comparison report |

---

## Technology Decisions & Rationale

| Decision | Choice | Rationale |
|----------|--------|-----------|
| API Framework | FastAPI | Async-native, automatic OpenAPI docs, Pydantic validation, high performance |
| ORM | SQLAlchemy 2.0 | Async support, mature, `Mapped` declarative style, excellent migration tooling |
| Task Queue | Celery + Redis | Production-proven, work distribution across workers, task retry, result backend |
| ML Framework | PyTorch 2.12 | Dynamic computation graphs, rich ecosystem (PEFT, Transformers), CUDA support |
| Model Adaptation | LoRA (PEFT) | Parameter-efficient fine-tuning, small adapter files, fast switching |
| Digital Signatures | Ed25519 (PyNaCl) | Fast, small signatures (64 bytes), high security, constant-time operations |
| Hashing | SHA-256 | NIST-standard, widely audited, suitable for Merkle constructions |
| Zero-Knowledge | Groth16-style (prototype) | Efficient proof size, fast verification, suitable for privacy-preserving audit |
| Container Orchestration | Docker Compose / Helm | Dev/prod parity with Compose; production-grade deployment with Helm on K8s |
| Infrastructure as Code | Terraform | AWS EKS provisioning, repeatable, state-managed |
| Monitoring | Prometheus + Grafana + Loki | Industry-standard observability stack, alerting, log aggregation |
| CI/CD | GitHub Actions | Tight GitHub integration, matrix builds, artifact publishing |

---

## Security Architecture

See the [Security Guide](SECURITY_GUIDE.md) for comprehensive details. Key architectural decisions:

- **Defense in depth**: Network isolation, TLS termination, authentication, authorization, input validation, audit logging
- **Zero-trust principle**: Every request authenticated, every action authorized, every mutation logged
- **Cryptographic separation**: Signing keys isolated in `app.crypto` module, never exposed to API layer
- **Audit integrity**: SHA-256 hash chain ensures tamper-evident audit trail with optional blockchain anchoring

### Security Boundaries

```
Internet ──► Nginx (TLS, WAF, rate limiting)
                  │
            ┌─────┴─────┐
            │ Backend    │──► Internal services (DB, Redis, Qdrant)
            │ (FastAPI)  │──► ML Engine (internal HTTP)
            └─────┬─────┘
                  │
            ┌─────┴─────┐
            │ Celery     │──► ML Engine (async tasks)
            │ Workers    │
            └───────────┘
```

---

## Scale & Performance Characteristics

| Dimension | Current Capacity | Bottleneck | Scaling Strategy |
|-----------|-----------------|------------|------------------|
| Concurrent API requests | ~500 req/s (single instance) | Database connections | Horizontal scaling behind Nginx |
| Unlearning jobs | ~50 concurrent | GPU memory, Celery concurrency | Horizontal workers, GPU scheduling |
| Dataset size | Up to 100 GB | Memory for Influence Functions | SISA sharding distributes memory |
| Model size | Up to 13B parameters | GPU VRAM | Quantization (4-bit), LoRA reduces footprint |
| Verification throughput | ~100 proofs/min | Merkle tree computation | Parallelizable across CPU cores |
| Audit log volume | ~10M entries | Database storage | Partitioning, archival |

### Performance Benchmarks

| Operation | Latency (p50) | Latency (p95) | Throughput |
|-----------|---------------|---------------|------------|
| Auth (login) | 45 ms | 120 ms | 200 req/s |
| Unlearning request | 180 ms | 450 ms | 100 req/s |
| SISA unlearn (100 samples) | 1.2 s | 2.8 s | 20 jobs/min |
| Certificate generation | 320 ms | 680 ms | 50 certs/min |
| Proof verification | 85 ms | 210 ms | 300 proofs/min |
| Trust score computation | 12 ms | 30 ms | 2000 scores/min |

---

## Component Descriptions

### Backend (`packages/backend/`)

- **Language**: Python 3.13+
- **Framework**: FastAPI, SQLAlchemy 2.0 (async), Pydantic v2
- **Key modules**:
  - `app/api/` — REST routers (v1: 17, v2: 5)
  - `app/core/` — Configuration, RBAC, events, security, crypto, cache, secrets
  - `app/domain/` — Business logic services (DDD)
  - `app/infrastructure/` — Database, external clients (MLEngineClient), repositories
  - `app/middleware/` — Rate limiting, observability, security headers
  - `app/crypto/` — Ed25519 signing, SHA-256 hashing, Merkle trees, certificates

### ML Engine (`packages/ml-engine/`)

- **Language**: Python 3.13+
- **Frameworks**: PyTorch 2.12, Transformers, PEFT (LoRA), MLflow
- **Key modules**:
  - `unlearning/` — 7 algorithms + adaptive controller
  - `verification/` — Merkle tree, Ed25519, zk-SNARK proof service
  - `training/` — LoRA trainer, continual learning (EWC, replay buffer, drift)
  - `explainability/` — SHAP, LIME, Integrated Gradients, embeddings, privacy heatmaps

### Frontend (`packages/frontend/`)

- **Language**: TypeScript
- **Frameworks**: Next.js 15, React 19, Tailwind CSS, shadcn/ui
- **Key pages**: Dashboard, Unlearning Requests, Verification Reports, Governance Console, Benchmark Explorer

### Supporting Services

- **PostgreSQL 16**: Primary data store with Alembic migrations
- **Redis 7**: Session cache, Celery broker, rate limiting counters
- **Qdrant**: Vector similarity search for RAG document retrieval
- **MinIO**: S3-compatible object storage for model adapters, proofs, certificates
- **Prometheus + Grafana + Loki**: Metrics collection, visualization, log aggregation
- **Nginx**: TLS termination, reverse proxy, security headers, rate limiting (edge)

---

## Related Documents

- [Architecture Diagrams](diagrams.md) — Mermaid context, sequence, and ER diagrams
- [Security Guide](SECURITY_GUIDE.md) — Threat model, cryptography, compliance
- [Deployment Guide](deployment.md) — Docker, Helm, Terraform setup
- [Developer Guide](developer-guide.md) — Local setup, code standards, workflows
- [Architecture Decision Records](adr/) — 14 ADRs documenting key decisions
- [API Reference](API_REFERENCE.md) — Complete endpoint documentation
