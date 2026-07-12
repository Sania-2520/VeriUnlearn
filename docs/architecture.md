# VeriUnlearn — System Architecture

## 1. Architectural Overview

VeriUnlearn follows **Clean Architecture** with layered separation, **Domain-Driven Design** for bounded contexts, and **Event-Driven Architecture** for async operations. The system is decomposed into six bounded contexts:

1. **Identity & Access** — authentication, authorization, user management
2. **Conversational AI** — chat, inference, RAG
3. **Model Lifecycle** — training, versioning, registry
4. **Machine Unlearning** — algorithm selection, execution, verification
5. **Cryptographic Proof** — hashing, merkle trees, signing, certificates
6. **Observability** — metrics, logging, tracing, health

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                    │
│  Workspace │ Privacy Center │ Compliance │ Admin │ Research│
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP/REST + WebSocket
┌──────────────────────▼──────────────────────────────────┐
│                    API Gateway (Nginx)                    │
│              /api/* → Backend :8000                       │
│              /ws/*   → Backend (WebSocket)                │
│              /metrics → Prometheus                        │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                   FastAPI Backend                         │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Auth API │  │ Chat API │  │Training  │  │Unlearning│ │
│  │ /api/v1  │  │ /api/v1  │  │API /v1   │  │API /v1   │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘ │
│       │              │             │              │       │
│  ┌────▼──────────────▼─────────────▼──────────────▼─────┐ │
│  │                  Service Layer                         │ │
│  │  AuthService │ ChatService │ TrainingService │        │ │
│  │  UnlearningService                                    │ │
│  └──────────────────────┬──────────────────────────────┘ │
│                         │                                  │
│  ┌──────────────────────▼──────────────────────────────┐ │
│  │                 Domain Layer                          │ │
│  │  Models (ORM) │ ML Engine │ Crypto Engine │          │ │
│  │  ModelManager │ Trainer   │ SISA                     │ │
│  │  MIAttack     │ Merkle    │ Signing │ Certificate    │ │
│  └──────────────────────┬──────────────────────────────┘ │
│                         │                                  │
│  ┌──────────────────────▼──────────────────────────────┐ │
│  │              Infrastructure Layer                      │ │
│  │  PostgreSQL │ Redis │ Qdrant │ MinIO │ Celery        │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## 2. Layer Architecture

### 2.1 API Layer (`app/api/v1/`)

FastAPI route handlers following thin-controller pattern. Each handler:
- Validates input via Pydantic schemas
- Injects dependencies (DB session, current user)
- Delegates to service layer
- Returns Pydantic response schemas

### 2.2 Service Layer (`app/services/`)

Business logic orchestration:
- `AuthService` — registration, password hashing, JWT management
- `ChatService` — conversation CRUD, inference integration
- `TrainingService` — dataset management, training orchestration
- `UnlearningService` — full deletion lifecycle: capture baseline → run algorithm → verify → crypto proof → audit

### 2.3 Domain Layer (`app/models/`, `app/ml/`, `app/crypto/`)

Core domain logic:
- **Models**: SQLAlchemy ORM with 12 tables, relationships, and type annotations
- **ML**: ModelManager (singleton, model lifecycle), Trainer (LoRA training loop), InferenceEngine (text generation), unlearning algorithms (SISA, Influence, Certified Removal, Adaptive Controller), verification (MIA, Utility)
- **Crypto**: MerkleTree, MerkleTreeBuilder, SigningService (Ed25519), CertificateGenerator (JSON + QR)

### 2.4 Infrastructure Layer (`app/db/`, `app/worker/`)

- **DB**: Async SQLAlchemy engine, session factory, Alembic migrations
- **Worker**: Celery app, async task definitions for training and unlearning
- External services: PostgreSQL, Redis, Qdrant, MinIO

## 3. Data Flow Diagrams

### 3.1 Chat → Training Flow

```
User Message
    │
    ▼
ChatService.create_message()
    │
    ├──► Store message in PostgreSQL
    │
    ▼
InferenceEngine.generate() ← ModelManager (LoRA adapter)
    │
    ├──► Store assistant response
    │
    ▼
TrainingSample created (user_id, conversation_id, shard_id, slice_id, version)
    │
    ▼
Celery task: build_dataset → train_model_task
    │
    ▼
Trainer.train() → new ModelVersion with unique hash
```

### 3.2 Deletion Flow

```
Deletion Request
    │
    ▼
AdaptiveController.select_algorithm()
    ├── certified_removal (≤1% deletion or ≤10 samples)
    ├── influence_functions (≤10% deletion)
    └── sisa (default)
    │
    ▼
Capture baseline (current model version, MIA metrics)
    │
    ▼
Execute algorithm:
    ├── SISA: load shard → filter deleted samples → retrain → save new adapter
    ├── Influence: compute influence scores → adjust weights
    └── Certified: save model copy (placeholder)
    │
    ▼
Run verification:
    ├── MIA before vs after
    └── Utility evaluation
    │
    ▼
Build cryptographic proof:
    ├── Merkle tree from verification data
    ├── Ed25519 signature on Merkle root
    └── Generate certificate (JSON + QR)
    │
    ▼
Log to AuditLedger
    │
    ▼
Return certificate + result
```

## 4. Component Details

### 4.1 ModelManager (Singleton)

```python
class ModelManager:
    _instance: ModelManager | None = None
    _model: PreTrainedModel | None = None
    _tokenizer: PreTrainedTokenizer | None = None
```

Responsibilities:
- Lazy-load base model with 4-bit quantization
- Create LoRA adapters via PEFT
- Load/save adapter weights
- Compute SHA-256 hash of adapter files
- Unload model to free GPU memory

### 4.2 Trainer

Custom PyTorch training loop with:
- AdamW optimizer
- Cosine learning rate scheduler with warmup
- Gradient clipping (max norm: 1.0)
- DataCollatorForLanguageModeling
- Per-epoch and per-step callbacks
- TQDM progress reporting

### 4.3 AdaptiveController

Rule-based algorithm selection:

| Condition | Algorithm | Guarantee |
|---|---|---|
| ≤1% deletion AND ≤1000 samples | Certified Removal | Certified |
| ≤10 samples | Certified Removal | Certified |
| ≤10% deletion | Influence Functions | Approximate |
| Default | SISA | Exact (via retraining) |

### 4.4 SISAUnlearning

- Loads existing shard adapter or creates fresh LoRA
- Filters out training samples marked for deletion
- Retrains on retained samples only
- Returns new adapter path and SHA-256 hash
- Support for "empty" shard (no retained samples)

### 4.5 MIAttack

- Binary classifier distinguishing members from non-members
- Currently returns hardcoded metrics (placeholder for learned attack model)
- Target: shadow model training with held-out data

### 4.6 MerkleTreeBuilder

- Converts ORM records or dicts to Merkle leaves
- 64-byte chunk size for record hashing
- Binary Merkle tree construction
- Root = SHA-256 hash chain

### 4.7 SigningService

- Ed25519 signing via PyNaCl
- Auto-generates persistent key on first run
- Keys stored at `{adapter_storage_dir}/signing_key`
- Exposes: `sign(message) → base64 signature`, `verify(message, signature) → bool`

### 4.8 CertificateGenerator

- Builds JSON certificate with all verification fields
- Signs certificate content with Ed25519
- Generates QR code containing ID, hash, and signature prefix
- Stores certificate in `proofs/certificates/`

## 5. Database Schema

### Entity-Relationship (Simplified)

```
users ──── conversations ──── messages
  │                              │
  │                              ▼
  │──── training_datasets ──── training_samples
  │                              │
  │                              ▼
  │──── model_versions ────── model_shards
  │
  │──── unlearning_requests ── unlearning_samples
          │                      │
          ▼                      │
       unlearning_results ◄─────┘
          │
          ▼
       audit_ledger
```

All tables include `created_at` and `updated_at` timestamps via `TimestampMixin`.

## 6. Async Architecture

```
Client ←→ FastAPI (async handlers)
              │
              ├── PostgreSQL (asyncpg + async SQLAlchemy)
              ├── Redis (async via redis-py)
              │
              ▼
          Celery Worker ←→ Redis (broker)
              │
              ├── Model training (GPU)
              ├── Unlearning execution (GPU)
              └── Dataset building
```

## 7. Deployment Architecture

```
┌─────────────────────────────────────┐
│           Docker Compose             │
│                                      │
│  ┌────────┐  ┌────────┐  ┌────────┐ │
│  │ Nginx  │──│ Backend │──│ Worker │ │
│  │ :80    │  │ :8000   │  │ (celery)│ │
│  └────┬───┘  └──┬─────┘  └────┬───┘ │
│       │         │              │      │
│  ┌────▼───┐  ┌──▼─────┐  ┌────▼───┐ │
│  │Frontend│  │Postgres│  │ Redis  │ │
│  │:3000   │  │:5432   │  │:6379   │ │
│  └────────┘  └────────┘  └────────┘ │
│  ┌────────┐  ┌────────┐             │
│  │ Qdrant │  │ MinIO  │             │
│  │:6333   │  │:9000   │             │
│  └────────┘  └────────┘             │
└─────────────────────────────────────┘
```

## 8. Technology Decisions

| Decision | Rationale |
|---|---|
| FastAPI over Django | Async performance, auto OpenAPI, DI support |
| SQLAlchemy over raw SQL | ORM with async support, migration tooling |
| PyTorch over TensorFlow | LoRA/PEFT ecosystem, research community standard |
| Ed25519 over RSA | Faster signing, smaller signatures, modern standard |
| Qdrant over Pinecone | Self-hosted, cost control, data sovereignty |
| MinIO over S3 | Self-hosted S3-compatible, no cloud dependency |
| Celery over Arq/Broker | Mature ecosystem, monitoring, beat scheduler |
| Next.js over plain React | SSR, file-based routing, Server Actions |
| Docker Compose over k8s (dev) | Simpler local dev; k8s-ready for production |

## 9. Future Architecture Considerations

- **zkSNARK integration**: Replace Merkle tree with zero-knowledge proofs for formal verification without revealing verification data
- **Differential Privacy**: Add DP-SGD during training for formal privacy guarantees
- **Horizontal scaling**: Stateless backend behind load balancer; read replicas for PostgreSQL
- **Federated unlearning**: Cross-organization unlearning with secure multi-party computation
- **HSM key management**: Hardware security module for signing key storage
- **gRPC inference**: Separate inference service for lower latency
