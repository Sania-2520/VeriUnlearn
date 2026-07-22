# VeriUnlearn Architecture

## System Overview

VeriUnlearn is a research-grade machine unlearning platform with enterprise governance, providing an end-to-end framework for verifiable data deletion from machine learning models with cryptographic proofs.

- **Current Version**: 6.0 (Phases 1-6 complete)
- **Status**: ~100% complete — 242 tests passing across backend (173) and ML engine (69)
- **Technology Stack**: Python 3.13, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, Next.js 15, React 19, Zustand, Celery + Redis, PostgreSQL, PyTorch, Libsodium (Ed25519)

---

## Architecture Layers

### 1. API Layer

Two API versions coexist on the FastAPI application:

**v1 Routers** (17 routers, mounted at `/api/v1`):

| Router | Module | Responsibility |
|--------|--------|----------------|
| `auth` | `app.api.v1.auth` | Registration, login, JWT, OAuth, email verify, password reset |
| `chat` | `app.api.v1.chat` | Conversational AI with RAG retrieval and streaming |
| `training` | `app.api.v1.training` | Dataset upload, model training, LoRA adapter lifecycle |
| `unlearning` | `app.api.v1.unlearning` | Machine unlearning requests and status |
| `documents` | `app.api.v1.documents` | Document upload and RAG indexing |
| `admin` | `app.api.v1.admin` | User management, platform overview |
| `api_keys` | `app.api.v1.api_keys` | API key CRUD with SHA-384 hashing |
| `gdpr` | `app.api.v1.gdpr` | Data export and account deletion rights |
| `usage` | `app.api.v1.usage` | Usage quotas and rate limits |
| `webhooks` | `app.api.v1.webhooks` | Event notification endpoints |
| `backup` | `app.api.v1.backup` | Backup and restore operations |
| `registry` | `app.api.v1.registry` | Model version registry |
| `experiments` | `app.api.v1.experiments` | Experiment tracking |
| `datasets` | `app.api.v1.datasets` | Dataset versioning and management |
| `training_jobs` | `app.api.v1.training_jobs` | Async training job lifecycle |
| `inference` | `app.api.v1.inference` | Model inference with logging |
| `dashboard` | `app.api.v1.dashboard` | Dashboard statistics |

**v2 Engine Routers** (5 routers, mounted at `/api`):

| Router | Module | Responsibility |
|--------|--------|----------------|
| `unlearning_engine` | `app.api.v2.unlearning_engine` | Deletion request → unlearning → verification workflow |
| `verification_engine` | `app.api.v2.verification_engine` | Cryptographic verification, certificates, trust scores, reports |
| `governance_engine` | `app.api.v2.governance_engine` | Consent, policy engine, compliance workflows, risk, lineage |
| `mlops_engine` | `app.api.v2.mlops_engine` | Experiment tracking, pipelines, observability, model serving |
| `research_engine` | `app.api.v2.research_engine` | Benchmarks, algorithm registry, privacy attacks, leaderboards |

### 2. Service Layer

55 services, all constructed per-request with `db: AsyncSession` via FastAPI dependency injection. No service holds state across requests.

| # | Service | Responsibility |
|---|---------|----------------|
| 1 | `auth_service.py` | User registration, login, JWT tokens, password hashing |
| 2 | `api_key_service.py` | API key generation with `vu_` prefix, SHA-384 hashing |
| 3 | `training_service.py` | LoRA adapter training, model training orchestration |
| 4 | `training_job_service.py` | Async training job lifecycle, progress tracking, rollback |
| 5 | `dataset_service.py` | Dataset upload, versioning, schema validation |
| 6 | `unlearning_service.py` | Core unlearning orchestration, sample deletion |
| 7 | `unlearning_job_service.py` | Extended unlearning job lifecycle, retry, checkpointing |
| 8 | `unlearning_pipeline.py` | Multi-step unlearning pipeline execution |
| 9 | `unlearning_benchmark_service.py` | Unlearning-specific benchmarking |
| 10 | `verification_service.py` | Orchestrates verification strategies, trust scoring |
| 11 | `proof_verification_service.py` | Merkle proof and hash chain verification |
| 12 | `certificate_service.py` | Cryptographic certificate generation and validation |
| 13 | `trust_score_service.py` | Aggregate trust score computation |
| 14 | `model_registry_service.py` | Model versioning, routing, rollback, canary deployment |
| 15 | `model_comparison_service.py` | Before/after model weight and metric comparison |
| 16 | `model_serving_service.py` | Model serving and inference endpoint management |
| 17 | `inference_service.py` | Model inference with latency/token logging |
| 18 | `chat_service.py` | Conversational AI with RAG retrieval |
| 19 | `rag_service.py` | Retrieval-augmented generation from document chunks |
| 20 | `document_service.py` | Document upload, chunking, embedding |
| 21 | `consent_service.py` | Consent record lifecycle, withdrawal, expiration |
| 22 | `policy_service.py` | Policy evaluation against datasets and models |
| 23 | `compliance_service.py` | Compliance workflow orchestration |
| 24 | `approval_service.py` | Multi-level approval requests with escalation |
| 25 | `gdpr_service.py` | GDPR data export, account deletion |
| 26 | `retention_service.py` | Data retention policy enforcement and purging |
| 27 | `data_lineage_service.py` | Full traceability: dataset → model → deletion → certificate |
| 28 | `risk_service.py` | AI model risk assessment (privacy, compliance, exposure) |
| 29 | `governance_dashboard_service.py` | Aggregate governance score computation |
| 30 | `notification_service.py` | In-app notifications for governance events |
| 31 | `deletion_request_service.py` | Deletion request creation and tracking |
| 32 | `report_service.py` | Report generation for verification and governance |
| 33 | `report_generator_service.py` | Template-based report rendering |
| 34 | `audit_service.py` | Tamper-evident audit logging with SHA-256 hash chain |
| 35 | `enhanced_audit_service.py` | Extended audit with blockchain anchoring |
| 36 | `webhook_service.py` | Webhook registration, HMAC-SHA256 dispatch |
| 37 | `usage_service.py` | Usage quota tracking and enforcement |
| 38 | `backup_service.py` | Database backup and restore |
| 39 | `admin_service.py` | Admin panel statistics and user management |
| 40 | `auth_service.py` | Authentication and authorization |
| 41 | `experiment_service.py` | Experiment tracking with runs, metrics, artifacts |
| 42 | `pipeline_service.py` | Reusable pipeline definitions and execution |
| 43 | `benchmark_service.py` | Benchmark experiment configuration and execution |
| 44 | `algorithm_registry_service.py` | Algorithm registration, seeding, dynamic class loading |
| 45 | `leaderboard_service.py` | Algorithm ranking across benchmarks |
| 46 | `comparison_service.py` | Cross-algorithm comparison analysis |
| 47 | `metrics_engine.py` | Custom metric computation engine |
| 48 | `metrics_tracker.py` | Prometheus metrics tracking |
| 49 | `privacy_attack_service.py` | Membership inference attack simulation |
| 50 | `reproducibility_service.py` | Experiment environment capture for reproducibility |
| 51 | `export_service.py` | Data and report export (CSV, JSON, PDF) |
| 52 | `plugin_manager_service.py` | Plugin registration, loading via `importlib` |
| 53 | `validation_engine.py` | Pre-unlearning data validation |
| 54 | `checkpoint_service.py` | Pre-unlearning model snapshots for rollback |
| 55 | `observability_service.py` | System health metrics and tracing |

### 3. Domain Layer

47+ SQLAlchemy models across 16 model files, using SQLAlchemy 2.0 `Mapped` declarative style with async support.

| Model File | Models | Key Entities |
|------------|--------|-------------|
| `user.py` | `User` | Authentication, RBAC role assignment |
| `dataset.py` | `Dataset`, `DatasetVersion` | Uploaded datasets with versioning and schema info |
| `training.py` | `TrainingDataset`, `TrainingSample`, `ModelVersion`, `ModelShard` | Training data, sample-level shard/slice tracking, model versions with hash |
| `training_job.py` | `TrainingJob` | Async training job with Celery task tracking |
| `unlearning.py` | `UnlearningRequest`, `UnlearningSample`, `UnlearningResult`, `AuditLedger` | Deletion requests, per-sample deletion, before/after MIA metrics |
| `unlearning_job.py` | `UnlearningJob`, `Checkpoint` | Extended job lifecycle, pre-deletion model snapshots |
| `verification.py` | `VerificationJob`, `VerificationResult`, `VerificationCertificate`, `HashRecord`, `TrustScore`, `ComparisonRecord`, `ProofRecord` | Full verification pipeline with cryptographic artifacts |
| `governance.py` | `ConsentRecord`, `ConsentHistory`, `LifecycleEvent`, `Policy`, `PolicyViolation`, `RegulationConfig`, `ComplianceWorkflow`, `ComplianceReport`, `ApprovalRequest`, `ApprovalAction`, `RiskAssessment`, `GovernanceScore`, `RetentionPolicy`, `Notification`, `DataLineage` | Complete governance and compliance framework |
| `conversation.py` | `Conversation`, `Message` | Chat history and RAG context |
| `document.py` | `Document`, `DocumentChunk` | Document storage with chunked embeddings |
| `inference_log.py` | `InferenceLog` | Model inference audit trail |
| `experiment.py` | `Experiment`, `ExperimentRun`, `ExperimentMetric`, `ExperimentArtifact` | Experiment tracking (MLflow-style) |
| `pipeline.py` | `Pipeline`, `PipelineStep`, `PipelineRun`, `PipelineStepRun` | Reusable pipeline definitions and execution |
| `research.py` | `AlgorithmEntry`, `Benchmark`, `BenchmarkRun`, `BenchmarkMetric`, `Leaderboard`, `LeaderboardEntry`, `AttackResult`, `PublicationReport`, `ExperimentReproducibility`, `PluginEntry`, `ComparisonRecord` | Research and benchmarking suite |
| `api_key.py` | `ApiKey` | API key management with expiry |
| `conversation.py` | `Conversation`, `Message` | Conversational context |

### 4. ML Layer

Located in `app.ml/`, this layer contains the core machine learning logic.

**Unlearning Algorithms** (`app.ml.unlearning/`):

| Algorithm | Class | Paper | Complexity | Description |
|-----------|-------|-------|------------|-------------|
| SISA | `SISAUnlearning` | SISA Sharded, Isolated, Sliced, and Aggregated Unlearning | Medium | Splits model into shards; retrains affected slices independently |
| Influence Functions | `InfluenceUnlearning` | Influence Functions in Deep Learning | High | Gauss-Newton Hessian + Newton step for per-sample influence estimation |
| Certified Removal | `CertifiedRemoval` | Certified Data Removal from ML Models | High | Differential privacy certified guarantees (ε,δ)-DP noise injection |
| Bad Teacher | `BadTeacherUnlearning` | Bad Teacher: How Unnecessary Knowledge Hurts Unlearning | Medium | Gradient ascent via adversarial teacher for targeted forgetting |
| Catastrophic Forgetting | `CatastrophicForgetting` | Weight Perturbation for Unlearning | Low | Targeted weight perturbation to induce forgetting |
| ReLU Erasure | `ReLUErasure` | ReLU-based forgetting | Medium | Neuron activation manipulation for selective forgetting |
| Adaptive Controller | `AdaptiveController` | Meta-controller | — | Policy engine: 1-20 samples → Influence, 20-500 → Hybrid, >500 → SISA |

**Verification Strategies** (`app.ml.verification/`):

| Strategy | Class | Description |
|----------|-------|-------------|
| Hash Verification | `HashVerificationStrategy` | SHA-256 artifact hash comparison |
| Merkle Verification | `MerkleVerificationStrategy` | Merkle tree root and inclusion proof verification |
| Influence Verification | `InfluenceVerificationStrategy` | Influence function-based deletion verification |
| Membership Inference | `MembershipInferenceStrategy` | MIA-based before/after privacy comparison |
| Forget Quality | `ForgetQualityStrategy` | Model utility retention assessment |

**Additional ML Components**:

| Module | Description |
|--------|-------------|
| `explainable_unlearning.py` | Explainable AI: feature importance, attention analysis, weight change attribution, algorithm reasoning |
| `adaptive_controller.py` | Meta-controller for algorithm selection based on dataset size and deletion count |
| `inference.py` | Model inference pipeline |
| `trainer.py` | LoRA adapter training |
| `model_manager.py` | Model versioning and lifecycle |
| `embeddings.py` | Text embedding generation |
| `continual_learning.py` | EWC, replay buffer, drift detection |
| `mlflow_tracker.py` | MLflow experiment tracking |
| `governance/` | Governance provider interfaces |

### 5. Infrastructure Layer

| Component | Location | Description |
|-----------|----------|-------------|
| **Event Bus** | `app.core.events` | In-process async pub/sub singleton with 44 named events, wildcard handlers, history buffer (500 events) |
| **Plugin System** | `PluginManagerService` + `PluginEntry` | DB-backed plugin registry with dynamic `importlib.import_module()` loading |
| **RBAC** | `app.core.rbac` | 8 roles (admin, user, auditor, ml_engineer, researcher, compliance_officer, legal_team, viewer) with 24 fine-grained permissions |
| **Crypto: Signing** | `app.crypto.signing` | Ed25519 digital signatures via Libsodium (`nacl`) |
| **Crypto: Merkle** | `app.crypto.merkle` | SHA-256 Merkle tree construction and proof generation |
| **Crypto: Hashing** | `app.crypto.hashing` | SHA-256 artifact fingerprinting |
| **Crypto: Certificate** | `app.crypto.certificate` | X.509-style verification certificate generation |
| **Dependencies** | `app.core.dependencies` | FastAPI `Depends()` with `Annotated` type aliases (`DatabaseDep`, `CurrentUser`) |
| **Rate Limiter** | `app.middleware.rate_limit` | Redis sliding window rate limiting |
| **Observability** | `app.middleware.observability` | Request tracing middleware |
| **Celery Workers** | `app.worker/` | Async task execution: training, unlearning, webhook retry, audit anchoring |

---

## Key Design Patterns

### Strategy Pattern

Two parallel strategy registries enable pluggable algorithms and verification:

**Unlearning Strategy** (`app.ml.unlearning.strategy`):
```
UnlearningStrategy (ABC)
├── name: str
├── description: str
├── guarantees: str
├── estimate_cost(dataset_size, num_deleted) → AlgorithmDecision
├── execute(retained_samples, deleted_samples) → UnlearningResult
└── can_handle(dataset_size, num_deleted) → bool

AlgorithmRegistry
├── register(strategy)
├── get(name) → UnlearningStrategy | None
├── all() → dict[str, UnlearningStrategy]
└── list_names() → list[str]
```

**Verification Strategy** (`app.ml.verification.strategy`):
```
VerificationStrategy (ABC)
├── name: str
├── description: str
├── verify(context) → VerificationOutput
└── required_context_keys() → list[str]

VerificationRegistry
├── register(strategy)
├── get(name) → VerificationStrategy | None
├── all() → dict[str, VerificationStrategy]
└── list_names() → list[str]
```

### Event-Driven Architecture

`EventBus` singleton (`app.core.events`) provides in-process async pub/sub:

- **44 named events** covering the full lifecycle (deletion, validation, unlearning, verification, governance, consent, approval, risk, retention)
- **Wildcard handlers** (`*` subscription receives all events)
- **Concurrent dispatch** via `asyncio.gather` with per-handler error isolation
- **Event history buffer** (last 500 events) for debugging and audit
- **Lifespan wiring** in `main.py`: auto-verification on `UNLEARNING_COMPLETED`, policy evaluation on `CONSENT_EXPIRED`, approval creation on `POLICY_VIOLATION_DETECTED`, deletion trigger on `APPROVAL_GRANTED`

### Plugin Architecture

- **Database-backed**: `PluginEntry` model stores name, type, version, entry point, config, enabled flag
- **Dynamic loading**: `importlib.import_module(entry_point)` loads plugin modules at runtime
- **8 plugin types**: Algorithm, Metric, Report, Dashboard, Verification, Policy, DataSource, Visualization
- **SDK interfaces** (`app.future.sdk.interfaces`): `PluginBase` ABC with `initialize()`, `shutdown()`, `health_check()` lifecycle hooks

### Dependency Injection

FastAPI `Depends()` with `Annotated` type aliases:
```python
DatabaseDep = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
```
Services are constructed per-request with the injected `db: AsyncSession`, ensuring no cross-request state leakage.

### Repository Pattern

Services encapsulate all data access via SQLAlchemy queries. No raw SQL appears in route handlers. Each service receives `db: AsyncSession` and constructs queries using `select()`, `await db.execute()`, and `await db.commit()`.

---

## Data Flow

The complete end-to-end workflow:

```
Dataset Upload
    ↓
Training (LoRA adapter training via Celery)
    ↓
Model Registry (versioning, hash, metrics)
    ↓
Inference (prediction with logging)
    ↓
Machine Unlearning Request
    ├── Validation Engine (data integrity checks)
    ├── Checkpoint Service (pre-deletion snapshot)
    ├── Algorithm Selection (AdaptiveController or manual)
    ├── Unlearning Execution (SISA / Influence / Certified / etc.)
    │   ├── Before model hash
    │   ├── After model hash
    │   └── Adapter path + metadata
    ├── Verification (5 strategies run in sequence)
    │   ├── Hash Verification
    │   ├── Merkle Verification
    │   ├── Influence Verification
    │   ├── Membership Inference Attack
    │   └── Forget Quality Assessment
    ├── Trust Score Computation (weighted aggregate)
    ├── Certificate Generation (Ed25519 signed, Merkle rooted)
    └── Audit Logging (hash-chained)
    ↓
Governance (consent → policy → approval → compliance)
    ↓
Benchmark (algorithm comparison across datasets)
    ↓
Evaluation (privacy attacks, utility metrics)
    ↓
Comparison (cross-algorithm analysis)
    ↓
Publication Report (research-ready markdown)
    ↓
Leaderboard (algorithm ranking)
    ↓
Research Dashboard (aggregate statistics)
```

---

## Phase Architecture

### Phase 1: Core Platform

**Models**: `User`, `Conversation`, `Message`, `Document`, `DocumentChunk`, `TrainingDataset`, `TrainingSample`, `ModelVersion`, `ModelShard`, `InferenceLog`, `ApiKey`

**Services**: `AuthService`, `ChatService`, `RagService`, `TrainingService`, `InferenceService`, `DocumentService`, `DatasetService`, `ModelRegistryService`, `ModelServingService`, `ApiKeyService`, `UsageService`, `DashboardService`, `ValidationEngine`

**Routers** (v1): `auth`, `chat`, `training`, `inference`, `documents`, `datasets`, `registry`, `dashboard`, `api_keys`, `usage`

**Capabilities**: User auth (JWT, OAuth), conversational AI with RAG, LoRA training, model registry, inference API, document upload, RBAC (8 roles, 24 permissions)

### Phase 2: Machine Unlearning

**Models**: `UnlearningRequest`, `UnlearningSample`, `UnlearningResult`, `AuditLedger`, `UnlearningJob`, `Checkpoint`, `TrainingJob`

**Services**: `UnlearningService`, `UnlearningJobService`, `UnlearningPipeline`, `CheckpointService`, `ValidationEngine`, `AuditService`

**ML Algorithms**: SISA, Influence Functions, Certified Removal, Bad Teacher, Catastrophic Forgetting, ReLU Erasure, Adaptive Controller

**Routers** (v1 + v2): `unlearning` (v1), `unlearning_engine` (v2), `training_jobs`

**Capabilities**: 7 unlearning algorithms with adaptive selection, pre-deletion checkpointing, rollback support, async job execution via Celery, hash-chained audit logging

### Phase 3: Cryptographic Verification

**Models**: `VerificationJob`, `VerificationResult`, `VerificationCertificate`, `HashRecord`, `TrustScore`, `ComparisonRecord`, `ProofRecord`

**Services**: `VerificationService`, `ProofVerificationService`, `CertificateService`, `TrustScoreService`, `ReportService`

**Verification Strategies**: Hash, Merkle, Influence, Membership Inference, Forget Quality

**Crypto**: Ed25519 signing, Merkle tree (SHA-256), artifact hashing

**Routers** (v2): `verification_engine`

**Capabilities**: 5 verification strategies, cryptographic certificates with QR codes, trust score aggregation, tamper-evident proofs, model before/after comparison

### Phase 4: Governance & Compliance

**Models**: `ConsentRecord`, `ConsentHistory`, `LifecycleEvent`, `Policy`, `PolicyViolation`, `RegulationConfig`, `ComplianceWorkflow`, `ComplianceReport`, `ApprovalRequest`, `ApprovalAction`, `RiskAssessment`, `GovernanceScore`, `RetentionPolicy`, `Notification`, `DataLineage`

**Services**: `ConsentService`, `PolicyService`, `ComplianceService`, `ApprovalService`, `GdprService`, `RetentionService`, `DataLineageService`, `RiskService`, `GovernanceDashboardService`, `NotificationService`, `DeletionRequestService`

**Routers** (v2): `governance_engine`

**Capabilities**: Consent lifecycle with immutable history, configurable policy engine, GDPR/CCPA compliance workflows, multi-level approval with escalation, data retention enforcement, full data lineage tracing, risk assessment, governance scoring

### Phase 5: MLOps & Platform Engineering

**Models**: `Experiment`, `ExperimentRun`, `ExperimentMetric`, `ExperimentArtifact`, `Pipeline`, `PipelineStep`, `PipelineRun`, `PipelineStepRun`

**Services**: `ExperimentService`, `PipelineService`, `ObservabilityService`, `ModelServingService`, `MetricsTracker`, `MetricsEngine`, `ExportService`

**Routers** (v1 + v2): `experiments` (v1), `mlops_engine` (v2)

**Capabilities**: MLflow-style experiment tracking, reusable pipeline engine with step dependencies, Prometheus/Grafana observability, model serving with health checks, operational dashboard

### Phase 6: Research & Benchmark Suite

**Models**: `AlgorithmEntry`, `Benchmark`, `BenchmarkRun`, `BenchmarkMetric`, `Leaderboard`, `LeaderboardEntry`, `AttackResult`, `PublicationReport`, `ExperimentReproducibility`, `PluginEntry`, `ComparisonRecord` (research)

**Services**: `AlgorithmRegistryService`, `BenchmarkService`, `LeaderboardService`, `ComparisonService`, `PrivacyAttackService`, `ReportGeneratorService`, `ReproducibilityService`, `PluginManagerService`, `UnlearningBenchmarkService`

**Routers** (v2): `research_engine`

**Capabilities**: Algorithm registry with 8 built-in algorithms, automated benchmarking, privacy attack simulation (MIA), algorithm leaderboards, cross-algorithm comparison, publication-ready report generation, experiment reproducibility capture, plugin system for extensibility

---

## Future Architecture (Phase 7)

Phase 7 defines interfaces (ABCs) for all future modules in `app.future.*`. No implementations exist yet — these are interface-only contracts designed to enable future development without breaking changes.

### Federated ML Unlearning (`app.future.federated`)

- `FederatedNodeProvider` — Node registration, heartbeat, dispatching unlearning requests
- `FederatedCoordinator` — Cross-node orchestration and result aggregation
- `CrossOrganizationDeleter` — GDPR-compliant deletion across organizational boundaries
- `FederatedVerificationStrategy` — Cross-model verification

### Continual/Streaming ML Unlearning (`app.future.continual`)

- `StreamingDatasetProvider` — Kafka/MQTT/SSE adapter abstraction
- `IncrementalForgetter` — Real-time forgetting as streaming events arrive
- `OnlineRetrainer` — Delta-based model updates after partial unlearning
- `AdaptiveVerificationStrategy` — Dynamic verification frequency based on stream activity

### Multi-Tenant Platform (`app.future.multitenant`)

- `TenantProvider` — Tenant lifecycle management (CRUD, tiers, quotas)
- `TenantIsolationProvider` — Per-tenant database URLs, storage paths, quota enforcement
- `ProjectManager` — Project grouping within tenants, team management

### ZKP Integration (`app.future.zkp`)

- `ZKProofProvider` — Trusted setup, proof generation, verification (Groth16, PLONK, STARK, Bulletproofs)
- `RecursiveProofProvider` — Multi-proof composition and aggregation

### Blockchain Backends (`app.future.blockchain`)

- `BlockchainProvider` — Multi-chain abstraction (Ethereum, Polygon, Hyperledger, private chains)
- `PrivateChainProvider` — Extended interface for permissioned chains with channel management and smart contracts

### Confidential Computing (`app.future.confidential`)

- `TEEProvider` — Trusted Execution Environment lifecycle (Intel SGX, AMD SEV, TrustZone)
- `AttestationService` — Remote attestation report generation and verification
- `ConfidentialComputingOrchestrator` — Multi-enclave task routing and migration

### AI Governance Copilot (`app.future.copilot`)

- `GovernanceCopilot` — Natural-language governance queries, certificate explanation, risk explanation
- `PolicyRecommender` — AI-powered policy suggestions from data profiles
- `ComplianceAssistant` — Automated compliance monitoring, reporting, remediation suggestions

### Intelligent Policy Engine (`app.future.intelligent_policy`)

- `IntelligentPolicyEngine` — AI-generated policies from data profiles, adaptive policy management
- `RiskPredictor` — ML-based compliance risk prediction
- `RetentionOptimizer` — Automatic retention policy optimization
- `CompliancePatternDetector` — Behavioral pattern detection for proactive compliance

### Autonomous Agents (`app.future.agents`)

- `BaseAgent` — Event subscription, task processing, health monitoring
- `AgentOrchestrator` — Agent registry, event fan-out, orchestration status
- `TrainingAgent` — Training lifecycle monitoring, hyperparameter suggestions
- `VerificationAgent` — Auto-verification, strategy selection, scheduling
- `ComplianceAgent` — Policy monitoring, auto-enforcement, audit generation
- `MonitoringAgent` — Metrics collection, incident detection, alerting
- `BenchmarkAgent` — Automated benchmarking, leaderboard maintenance

### Plugin SDK (`app.future.sdk`)

- `PluginBase` — Root interface with `initialize()`, `shutdown()`, `health_check()`
- `AlgorithmPlugin`, `MetricPlugin`, `ReportPlugin`, `DashboardPlugin`, `VerificationPlugin`, `PolicyPlugin`, `DataSourcePlugin`, `VisualizationPlugin`
- `PluginRegistry` — Central plugin discovery and loading

### Future Data Sources (`app.future.datasources`)

- `DataSourceConnector` — Uniform API for Snowflake, HuggingFace, OpenAI, Anthropic
- `MLPlatformConnector` — Extended interface for Databricks, Azure AI, SageMaker, Vertex AI

---

## Middleware Stack

| Middleware | Module | Function |
|-----------|--------|----------|
| CORS | FastAPI built-in | Cross-origin requests (allow all origins) |
| Rate Limiting | `app.middleware.rate_limit` | Redis sliding window, per-IP and per-tenant |
| Observability | `app.middleware.observability` | Request tracing, latency metrics |
| Version Headers | `app.main` | `X-API-Version`, `X-API-Deprecated` response headers |
| Global Exception | `app.main` | Unhandled exception → 500 JSON response |

---

## Event Catalog

The `EventBus` defines 44 named events across four domains:

**Unlearning Lifecycle** (14 events):
`deletion.requested`, `validation.started`, `validation.completed`, `validation.failed`, `checkpoint.created`, `unlearning.started`, `unlearning.completed`, `unlearning.failed`, `algorithm.selected`, `model.updated`, `job.created`, `job.status.changed`, `job.cancelled`, `job.retrying`

**Verification & Trust** (8 events):
`verification.requested`, `verification.completed`, `audit.logged`, `rollback.triggered`, `certificate.generated`, `certificate.validated`, `trust_score.computed`, `proof.stored`

**Research & Reporting** (3 events):
`report.generated`, `model.compared`, `report.generated.governance`

**Governance & Consent** (19 events):
`consent.granted`, `consent.withdrawn`, `consent.updated`, `consent.expired`, `policy.violation.detected`, `policy.violation.resolved`, `workflow.initiated`, `workflow.completed`, `workflow.advanced`, `approval.requested`, `approval.granted`, `approval.rejected`, `approval.escalated`, `risk.assessed`, `retention.enforced`, `data.retained`, `data.purged`, `deletion.triggered`, `notification.sent`

---

## RBAC Permission Model

8 roles with 24 permissions:

| Role | Key Permissions |
|------|----------------|
| `admin` | All 24 permissions |
| `user` | Training R/W, Unlearning R/W/Execute, Documents R/W/D, Consent R/W, Governance R |
| `ml_engineer` | Training R/W, Unlearning R/W/Execute, Documents R/W, Risk R, Lineage R |
| `researcher` | Training R, Unlearning R, Documents R, Lineage R (read-only) |
| `compliance_officer` | Consent R/W, Policy R/W, Compliance R/W/Approve, Governance R/W, Retention R/W, Audit Log |
| `legal_team` | Consent R/W, Compliance R/Approve, Governance R, Lineage R |
| `auditor` | Unlearning R, Audit Log, Documents R, Policy R, Compliance R, Governance R, Lineage R |
| `viewer` | Read-only: Users, Training, Unlearning, Documents, Consent, Governance, Lineage |

---

## Cryptography

| Component | Algorithm | Library | Purpose |
|-----------|-----------|---------|---------|
| Digital Signatures | Ed25519 | Libsodium (`nacl`) | Sign/verify certificates and proof artifacts |
| Hashing | SHA-256 | `hashlib` | Artifact fingerprinting, audit chain links |
| Merkle Trees | SHA-256 | Custom implementation | Batch proof generation and verification |
| Certificate Signing | Ed25519 | Libsodium (`nacl`) | Verification certificate signing with key management |
| API Key Hashing | SHA-384 | `hashlib` | Secure storage of API keys (prefix `vu_`) |
| Audit Chain | SHA-256 | `hashlib` | Tamper-evident audit log chain |

---

## Deployment Architecture

| Component | Technology | Role |
|-----------|-----------|------|
| Backend API | FastAPI + Uvicorn | REST API server |
| ML Engine | FastAPI + PyTorch | Model training and inference |
| Frontend | Next.js 15 + React 19 | Web dashboard |
| Database | PostgreSQL (async via SQLAlchemy) | Primary data store |
| Cache/Queue | Redis | Rate limiting, Celery broker |
| Task Queue | Celery | Async job execution (training, unlearning, webhooks) |
| Monitoring | Prometheus + Grafana + Loki | Metrics, dashboards, logs |
| Reverse Proxy | Nginx | TLS termination, security headers |
| Container | Docker + Docker Compose | Service orchestration |
| CI/CD | GitHub Actions | Lint, typecheck, test, build |
