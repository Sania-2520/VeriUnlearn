# VeriUnlearn — Requirements Analysis

## 1. Executive Summary

VeriUnlearn is an end-to-end framework for verifiable machine unlearning with cryptographic proofs, targeting privacy-preserving conversational AI. The platform enables organizations to deploy conversational AI while providing mathematically measurable evidence that deleted user information no longer influences machine learning models.

## 2. Stakeholders

| Stakeholder | Role | Key Concerns |
|---|---|---|
| End Users | Chat with AI assistant | Privacy, data deletion guarantees |
| Data Protection Officers (DPOs) | Regulatory compliance | GDPR/CCPA right-to-deletion, audit trails |
| ML Engineers | Model training & unlearning | Model quality, retraining cost, versioning |
| Security Engineers | Cryptographic verification | Proof integrity, non-repudiation |
| Enterprise Customers | Deployment & operations | SLA, scalability, audit readiness |
| Regulators | Oversight | Verifiable deletion, transparency |
| Researchers | Reproducibility | Open methodology, measurable claims |

## 3. Functional Requirements

### 3.1 Authentication & User Management

FR-001: Users shall register with username, email, and password.
FR-002: Users shall authenticate via JWT access/refresh token pairs.
FR-003: Users shall have roles (user, admin, researcher).
FR-004: Passwords shall be hashed with bcrypt.
FR-005: Administrators shall manage user accounts.

### 3.2 Conversational AI

FR-010: Users shall create and manage conversations.
FR-011: Users shall send messages and receive AI-generated responses.
FR-012: Conversations shall persist across sessions.
FR-013: Inference shall use a LoRA-adapted language model.
FR-014: Conversations shall produce training samples for model fine-tuning.

### 3.3 Document Ingestion & RAG

FR-020: Users shall upload documents (PDF, TXT, MD).
FR-021: Documents shall be chunked, embedded, and stored in a vector database.
FR-022: Chat context shall retrieve relevant document chunks via semantic search.
FR-023: Embeddings shall be associated with the uploading user for granular deletion.

### 3.4 Model Registry & Versioning

FR-030: The system shall maintain a registry of all model versions.
FR-031: Each version shall include: base model ID, adapter path, SHA-256 hash, parent version, training config, and metrics.
FR-032: No checkpoint shall ever be overwritten; every retraining produces a new version.
FR-033: Previous model versions shall remain archived and queryable.

### 3.5 Training Pipeline

FR-040: Training shall use conversation data to create LoRA adapters.
FR-041: Only LoRA adapter weights shall be updated; the base model shall remain frozen.
FR-042: Each training sample shall include: user_id, conversation_id, sample_id, shard_id, slice_id, timestamp, and version.
FR-043: Training shall be async via Celery task queue.
FR-044: Training metrics (loss, learning rate, epoch) shall be tracked.

### 3.6 Machine Unlearning

FR-050: Deletion of a user's data must trigger measurable changes to the model.
FR-051: Supported algorithms: SISA, Influence Functions, Certified Removal.
FR-052: An Adaptive Hybrid Controller shall select the optimal algorithm based on: dataset size, deletion count, privacy sensitivity, latency budget, and model type.
FR-053: SISA shall retrain only the affected shard after filtering deleted samples.
FR-054: Influence Functions shall approximate removal via influence score adjustment.
FR-055: Certified Removal shall provide formal guarantees for small deletions.
FR-056: The unlearning pipeline must log every operation to the audit ledger.
FR-057: Every unlearning operation must produce a new model version.

### 3.7 Verification Pipeline

FR-060: Membership Inference Attacks (MIA) shall run before and after each deletion.
FR-061: Utility evaluation shall measure model quality retention after deletion.
FR-062: Deletion is successful only if MIA effectiveness decreases while utility remains above threshold.
FR-063: Metrics collected: accuracy, precision, recall, F1, loss, weight distance, gradient distance, cosine similarity, influence score.

### 3.8 Cryptographic Proof Generation

FR-070: Each unlearning result shall produce a SHA-256 Merkle tree of verification data.
FR-071: The Merkle root shall be signed with Ed25519 digital signature.
FR-072: A signed certificate shall be generated per deletion request.
FR-073: Certificates shall include: certificate ID, timestamp, algorithm, version before/after, hashes, Merkle root, signature, MIA results, utility retention, QR code.
FR-074: Architecture shall support future zkSNARK integration.

### 3.9 Compliance Dashboard

FR-080: Display all unlearning requests and their status.
FR-081: Show MIA metrics before vs. after for each deletion.
FR-082: Show utility retention percentage.
FR-083: Display cryptographic proof details (Merkle root, signature, certificate).
FR-084: Allow certificate download for audit purposes.

### 3.10 Research Dashboard

FR-090: Compare unlearning algorithms across deletion scenarios.
FR-091: Visualize privacy-utility tradeoff curves.
FR-092: Export experiment data for publication.

### 3.11 Monitoring & Observability

FR-100: Prometheus metrics for API latency, request count, error rate.
FR-101: Structured logging with loguru.
FR-102: OpenTelemetry distributed tracing.
FR-103: Health check endpoints.

## 4. Non-Functional Requirements

### 4.1 Performance

NFR-001: Chat response latency < 2 seconds (P95).
NFR-002: SISA shard retraining < 10 minutes for 10k-sample shard.
NFR-003: MIA execution < 30 seconds per evaluation.
NFR-004: Certificate generation < 2 seconds.

### 4.2 Scalability

NFR-010: Support 100+ concurrent chat users.
NFR-011: Support datasets up to 1M training samples.
NFR-012: Support SISA sharding up to 64 shards.
NFR-013: Horizontal scaling via Docker Compose / Kubernetes.

### 4.3 Security

NFR-020: Passwords hashed with bcrypt (cost factor >= 12).
NFR-021: JWT access tokens expire in 30 minutes; refresh tokens in 7 days.
NFR-022: Signing keys stored with 0600 permissions.
NFR-023: API endpoints rate-limited.
NFR-024: CORS restricted in production.

### 4.4 Reliability

NFR-030: Database connection pooling with retry logic (tenacity).
NFR-031: Celery task retry on failure.
NFR-032: Graceful shutdown handling.
NFR-033: Health checks for all services.

### 4.5 Maintainability

NFR-040: Clean Architecture with layered separation (API → Services → Models → ML/Crypto).
NFR-041: Dependency injection via FastAPI dependencies.
NFR-042: Repository pattern for data access.
NFR-043: Full test coverage for core paths.
NFR-044: Alembic migrations for database schema.

## 5. System Constraints

- Base model must remain frozen; only LoRA adapters trainable.
- No database row deletion may substitute for machine unlearning.
- All generated proofs must be independently verifiable.
- Certificates must be self-contained for offline audit.
- Platform must be cloud-deployable (AWS, Azure, GCP).

## 6. Technology Stack

| Layer | Technology | Justification |
|---|---|---|
| Frontend | Next.js 15, TypeScript, Tailwind CSS, shadcn/ui | SSR, type safety, utility-first styling |
| Backend | FastAPI, Python 3.13 | Async, auto OpenAPI, modern Python |
| Database | PostgreSQL 16, SQLAlchemy 2.0 | ACID compliance, async ORM |
| Cache/Queue | Redis 7, Celery 5 | Task queue, result backend |
| Vector Store | Qdrant | ANN search, filterable payloads |
| Object Store | MinIO | S3-compatible, self-hosted |
| ML | PyTorch, Transformers, PEFT, LoRA | Industry-standard, LoRA support |
| Crypto | PyNaCl (Ed25519), SHA-256, Merkle | Standards-based, auditable |
| Observability | Prometheus, Grafana, OpenTelemetry | Metrics, tracing, alerting |
| CI/CD | GitHub Actions | Standard CI pipeline |
| Container | Docker, Docker Compose | Portable deployment |

## 7. Data Model Overview

12 SQLAlchemy ORM tables:
- `users` — accounts with roles and SISA shard assignment
- `conversations` — chat threads
- `messages` — individual chat turns
- `training_datasets` — named datasets
- `training_samples` — individual training records (versioned)
- `model_versions` — immutable version history
- `model_shards` — SISA shard state per version
- `unlearning_requests` — deletion request lifecycle
- `unlearning_samples` — mapping requests to deleted samples
- `unlearning_results` — verification metrics + cryptographic proofs
- `audit_ledger` — immutable event log

## 8. API Surface

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | User registration |
| POST | `/api/v1/auth/login` | Authentication |
| POST | `/api/v1/auth/refresh` | Token refresh |
| GET | `/api/v1/auth/me` | Current user |
| POST | `/api/v1/chat/conversations` | Create conversation |
| GET | `/api/v1/chat/conversations` | List conversations |
| GET | `/api/v1/chat/conversations/{id}/messages` | Get messages |
| POST | `/api/v1/chat/conversations/{id}/messages` | Send message |
| POST | `/api/v1/training/datasets` | Create dataset |
| POST | `/api/v1/training/start` | Start training |
| GET | `/api/v1/training/versions` | List model versions |
| POST | `/api/v1/unlearning/requests` | Create unlearning request |
| GET | `/api/v1/unlearning/requests` | List requests |
| POST | `/api/v1/unlearning/requests/{id}/execute` | Execute unlearning |
| GET | `/api/v1/unlearning/requests/{id}/result` | Get result |

## 9. Acceptance Criteria

AC-001: User can register, login, and receive JWT tokens.
AC-002: User can send messages and receive AI responses.
AC-003: Conversations are stored and retrievable.
AC-004: Training pipeline produces new model versions with unique hashes.
AC-005: SISA retraining produces a measurably different adapter (different hash).
AC-006: MIA shows decreased attack accuracy after deletion.
AC-007: Utility retention exceeds 80% after deletion.
AC-008: Certificate includes Merkle root and valid Ed25519 signature.
AC-009: Certificate signature is independently verifiable.
AC-010: Audit ledger records every unlearning operation.
