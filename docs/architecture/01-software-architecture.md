# VeriUnlearn — Software Architecture Document

## Version 1.0.0 — Enterprise Architecture

---

## Table of Contents

1. Executive Summary
2. Architectural Principles
3. System Context
4. Architecture Overview
5. Component Architecture
6. Data Architecture
7. Security Architecture
8. Deployment Architecture
9. Integration Architecture
10. Observability Architecture
11. Research Architecture
12. API Architecture
13. Frontend Architecture
14. ML Pipeline Architecture
15. Cryptographic Proof Architecture
16. Compliance Architecture

---

## 1. Executive Summary

VeriUnlearn is a production-grade enterprise SaaS platform that provides verifiable machine unlearning with cryptographic proofs for GDPR-compliant AI systems. The platform enables organizations to honor the "Right to be Forgotten" while maintaining AI model utility and providing cryptographic guarantees of deletion.

### Key Capabilities

- Multi-model AI chat platform with streaming responses
- Machine unlearning (SISA, Influence Functions, Certified Removal)
- Cryptographic proof generation (Merkle Trees, Ed25519, zkSNARK-ready)
- Complete data lifecycle management
- GDPR/AI Act/DPDP compliance automation
- Immutable audit trails with blockchain readiness
- Enterprise-grade security with privacy attack simulation

### Business Value

- Reduce GDPR compliance cost by ~80%
- Provide legally verifiable deletion proofs
- Enable AI deployment in regulated industries
- Maintain model utility post-unlearning
- Automated compliance reporting

---

## 2. Architectural Principles

### SOLID Principles

| Principle | Application |
|-----------|-------------|
| Single Responsibility | Each service has exactly one domain concern |
| Open/Closed | New AI providers via adapters, never modify core |
| Liskov Substitution | All AI provider implementations are interchangeable |
| Interface Segregation | Minimal, focused interfaces per domain |
| Dependency Inversion | High-level policies depend on abstractions |

### Clean Architecture Layers

```
┌──────────────────────────────────────────────────┐
│                  Presentation Layer               │
│  (API Gateway, Web UI, CLI, Webhooks)             │
├──────────────────────────────────────────────────┤
│                  Application Layer                │
│  (Use Cases, DTOs, Commands, Queries)             │
├──────────────────────────────────────────────────┤
│                  Domain Layer                     │
│  (Entities, Value Objects, Domain Events)         │
├──────────────────────────────────────────────────┤
│                  Infrastructure Layer             │
│  (Repositories, Adapters, External Services)      │
└──────────────────────────────────────────────────┘
```

### Domain-Driven Design

- **Bounded Contexts**: Auth, Chat, AI, RAG, Memory, Unlearning, Verification, Security, Audit, Compliance, Admin, Monitoring
- **Ubiquitous Language**: Shared terminology across all teams
- **Aggregates**: ChatSession, UnlearningJob, ProofCertificate
- **Domain Events**: ConversationDeleted, UnlearningCompleted, ProofGenerated

### Event-Driven Architecture

```
Service A ──publish──> Message Broker ──consume──> Service B
                              │
                              ├──> Event Store (immutable log)
                              ├──> Audit Service
                              └──> Webhook Dispatcher
```

### Security by Design

- Zero-trust architecture
- End-to-end encryption for sensitive data
- Cryptographic proof of deletion
- Immutable audit trails
- Automated security scanning in CI/CD
- Secrets management via Vault

---

## 3. System Context

```
┌─────────────────────────────────────────────────────────────────────┐
│                         VeriUnlearn System                           │
│                                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐    │
│  │  Users    │  │  Admins  │  │  API     │  │  External Systems │    │
│  │ (Browser) │  │ (Dashboard) │  │  Clients │  │  (OAuth, LLMs)    │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘    │
│       │              │              │                  │              │
│       └──────────────┴──────────────┴──────────────────┘              │
│                              │                                       │
│                      ┌───────┴────────┐                              │
│                      │   API Gateway   │                              │
│                      │ (Rate Limited)  │                              │
│                      └───────┬────────┘                              │
│                              │                                       │
│         ┌────────────────────┼────────────────────┐                  │
│         │                    │                    │                  │
│   ┌─────┴─────┐      ┌──────┴──────┐      ┌─────┴─────┐            │
│   │ Auth       │      │  Chat       │      │  Admin     │            │
│   │ Service    │      │  Service    │      │  Service   │            │
│   └─────┬─────┘      └──────┬──────┘      └─────┬─────┘            │
│         │                    │                    │                  │
│         └────────────────────┼────────────────────┘                  │
│                              │                                       │
│                      ┌───────┴────────┐                              │
│                      │  Message Queue   │                            │
│                      │  (RabbitMQ)      │                            │
│                      └───────┬────────┘                              │
│                              │                                       │
│         ┌────────────────────┼────────────────────┐                  │
│         │                    │                    │                  │
│   ┌─────┴─────┐      ┌──────┴──────┐      ┌─────┴─────┐            │
│   │ Unlearning │      │  Verification │      │  Security  │            │
│   │ Engine     │      │  Engine      │      │  Engine    │            │
│   └─────┬─────┘      └──────┬──────┘      └─────┬─────┘            │
│         │                    │                    │                  │
│         └────────────────────┼────────────────────┘                  │
│                              │                                       │
│                      ┌───────┴────────┐                              │
│                      │   Data Layer     │                            │
│                      │  (PostgreSQL,    │                            │
│                      │   Redis, Qdrant, │                            │
│                      │   MinIO)         │                            │
│                      └────────────────┘                              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Component Architecture

### 4.1 Service Components

#### API Gateway (Traefik/NGINX)
- Rate limiting: 1000 req/min per tenant
- JWT validation at edge
- TLS termination
- Request routing
- WAF protection
- DDoS mitigation

#### Auth Service (FastAPI)
- JWT + refresh token
- OAuth 2.0 (Google, GitHub)
- RBAC with role hierarchy
- Session management via Redis
- Email verification
- Passwordless MFA ready

#### Chat Service (FastAPI)
- Streaming SSE responses
- Conversation management
- File upload processing
- Rich content (Markdown, LaTeX, syntax highlighting)
- Voice I/O via WebSocket
- Export/Import/Share functionality

#### AI Provider Abstraction (Python)
- OpenAI, Anthropic, Google, Azure, Ollama, vLLM, HuggingFace
- One adapter per provider
- Automatic fallback
- Load balancing across providers
- Cost tracking per model

#### RAG Engine (Python)
- Document ingestion pipeline
- Multi-strategy chunking
- Hybrid retrieval (dense + sparse)
- Citation generation
- OCR processing via Tesseract
- Reranking via cross-encoders

#### Memory System (Python)
- Tiered memory architecture
- Session → Conversation → Persistent → User → Workspace
- Configurable retention policies
- Memory consolidation via LLM
- Privacy-aware memory pruning

#### Unlearning Engine (Python)
- SISA (Sharded, Isolated, Sliced, Aggregated)
- Influence function computation
- Certified removal verification
- Approximate unlearning
- Hybrid adaptive controller
- Model versioning and checkpointing
- Deletion queue with prioritization

#### Verification Engine (Python/C++)
- Merkle tree construction
- SHA-256 hashing
- Ed25519 digital signatures
- zkSNARK proof generation (circuit compiler)
- Proof verification API
- Certificate generation (X.509-compatible)
- Model fingerprinting

#### Security Engine (Python)
- Membership inference attack simulation
- Model extraction attack
- Privacy leakage testing
- Model inversion attack
- Automated security scoring
- Attack surface analysis

#### Audit Service (Python)
- Immutable event log
- Merkle chain data structure
- Blockchain anchoring (Ethereum)
- Event sourcing with EventStoreDB
- Model lineage tracking
- Deletion history with proofs

#### Compliance Service (Python)
- GDPR compliance checking
- AI Act risk classification
- DPDP compliance reports
- Risk scoring engine
- Deletion certificate management
- Audit timeline visualization

#### Admin Service (Python)
- User lifecycle management
- GPU cluster monitoring
- Job queue management
- Model registry
- Certificate management
- System health dashboard
- Usage analytics

### 4.2 Component Interaction Diagram

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────┐
│  Browser  │────▶│  Next.js UI   │────▶│  API Gateway  │────▶│  Auth    │
│           │◀────│  (Edge)       │◀────│  (Edge)       │◀────│  Service │
└──────────┘     └──────────────┘     └──────────────┘     └──────────┘
                                               │
                                               ▼
                                        ┌──────────────┐
                                        │  Load Balancer│
                                        └──────┬───────┘
                                               │
                    ┌──────────────────────────┼──────────────────────┐
                    │                          │                      │
              ┌─────┴─────┐            ┌───────┴───────┐      ┌─────┴─────┐
              │ Chat       │            │  Unlearning    │      │ RAG       │
              │ Service    │            │  Engine        │      │ Engine    │
              └─────┬─────┘            └───────┬───────┘      └─────┬─────┘
                    │                          │                      │
                    └──────────────────────────┼──────────────────────┘
                                               │
                                        ┌──────┴──────┐
                                        │  RabbitMQ    │
                                        └──────┬──────┘
                                               │
                    ┌──────────────────────────┼──────────────────────┐
                    │                          │                      │
              ┌─────┴─────┐            ┌───────┴───────┐      ┌─────┴─────┐
              │ Celery     │            │  Verification  │      │ Security  │
              │ Workers    │            │  Engine        │      │ Engine    │
              └─────┬─────┘            └───────┬───────┘      └─────┬─────┘
                    │                          │                      │
                    └──────────────────────────┼──────────────────────┘
                                               │
                                        ┌──────┴──────┐
                                        │   Data Layer │
                                        └─────────────┘
```

---

## 5. Data Architecture

### 5.1 Database Strategy

| Database | Purpose | Scaling Strategy |
|----------|---------|-----------------|
| PostgreSQL | Primary relational data | Read replicas, sharding by tenant |
| Redis | Cache, sessions, rate limits | Redis Cluster |
| Qdrant | Vector embeddings | Horizontal sharding |
| MinIO | Object storage (files, models) | Distributed mode |
| EventStoreDB | Event sourcing / audit log | Cluster mode |

### 5.2 ER Diagram (Core Entities)

See `02-database-schema.md` for detailed schema.

```
┌───────────────────┐       ┌────────────────────┐
│      Tenant        │       │      User           │
│───────────────────│       │────────────────────│
│ id (PK)           │──1:N──│ id (PK)             │
│ name               │       │ tenant_id (FK)      │
│ domain             │       │ email               │
│ plan               │       │ password_hash       │
│ settings (JSONB)   │       │ role                │
│ created_at         │       │ created_at          │
└───────────────────┘       └────────────────────┘
                                    │
                                    │ 1:N
                                    ▼
                            ┌───────────────────┐       ┌────────────────────┐
                            │  ChatSession       │       │  AIProvider         │
                            │───────────────────│       │────────────────────│
                            │ id (PK)            │──M:1──│ id (PK)             │
                            │ user_id (FK)       │       │ name                │
                            │ title              │       │ provider_type       │
                            │ folder_id (FK)     │       │ api_endpoint        │
                            │ is_pinned          │       │ is_active           │
                            │ created_at         │       └────────────────────┘
                            └────────┬──────────┘
                                     │ 1:N
                                     ▼
                            ┌───────────────────┐       ┌────────────────────┐
                            │  Message           │       │  File               │
                            │───────────────────│       │────────────────────│
                            │ id (PK)            │──M:1──│ id (PK)             │
                            │ session_id (FK)    │       │ message_id (FK)     │
                            │ role               │       │ filename            │
                            │ content (JSONB)    │       │ file_type           │
                            │ metadata (JSONB)   │       │ size                │
                            │ created_at         │       │ storage_path        │
                            └───────────────────┘       └────────────────────┘

┌───────────────────┐       ┌────────────────────┐      ┌────────────────────┐
│  Document          │       │  Embedding          │      │  VectorEntry        │
│───────────────────│       │────────────────────│      │────────────────────│
│ id (PK)            │──1:N──│ id (PK)             │      │ id (UUID)           │
│ tenant_id (FK)     │       │ document_id (FK)    │      │ embedding (vector)  │
│ filename           │       │ chunk_index         │      │ content             │
│ file_type          │       │ content             │      │ metadata (JSONB)    │
│ content            │       │ embedding (vector)  │      │ collection          │
│ status             │       │ created_at          │      └────────────────────┘
│ created_at         │       └────────────────────┘
└───────────────────┘

┌───────────────────┐       ┌────────────────────┐      ┌────────────────────┐
│  UnlearningJob     │       │  DeletionProof      │      │  AuditLog           │
│───────────────────│       │────────────────────│      │────────────────────│
│ id (PK)            │──1:1──│ id (PK)             │──N:1─│ id (PK)             │
│ request_id (FK)    │       │ job_id (FK)         │      │ event_type          │
│ user_id (FK)       │       │ merkle_root         │      │ actor_id            │
│ target_type        │       │ tree_depth          │      │ resource_type       │
│ target_id          │       │ signature           │      │ resource_id         │
│ algorithm          │       │ public_key          │      │ metadata (JSONB)    │
│ status             │       │ zk_proof (JSONB)    │      │ timestamp           │
│ created_at         │       │ certificate         │      │ merkle_proof        │
│ completed_at       │       │ created_at          │      └────────────────────┘
└───────────────────┘       └────────────────────┘

┌───────────────────┐       ┌────────────────────┐      ┌────────────────────┐
│  MemoryEntry       │       │  ModelVersion       │      │  SecurityReport     │
│───────────────────│       │────────────────────│      │────────────────────│
│ id (PK)            │       │ id (PK)             │      │ id (PK)             │
│ user_id (FK)       │       │ model_id (FK)       │      │ model_version_id    │
│ type               │       │ version             │      │ mi_attack_score     │
│ content (JSONB)    │       │ checkpoint_path     │      │ extraction_score    │
│ importance         │       │ metrics (JSONB)     │      │ inversion_score     │
│ expires_at         │       │ parent_version_id   │      │ overall_score       │
│ created_at         │       │ created_at          │      │ recommendations     │
└───────────────────┘       └────────────────────┘      └────────────────────┘
```

---

## 6. Security Architecture

### 6.1 Threat Model

| Threat | Mitigation |
|--------|------------|
| Unauthorized API access | JWT + OAuth 2.0 + API keys |
| Data breach at rest | AES-256 encryption, Vault |
| Data breach in transit | TLS 1.3, mTLS for services |
| Model inversion attack | Differential privacy, unlearning |
| Membership inference | Certified removal guarantees |
| Replay attacks | Nonce + timestamp validation |
| CSRF | SameSite cookies, CSRF tokens |
| XSS | Content-Security-Policy, sanitized output |
| SSRF | Network policies, URL allowlist |
| Broken authentication | Rate limiting, account lockout |
| Injection attacks | Parameterized queries, input validation |
| Insufficient logging | Immutable audit trail |

### 6.2 Security Layers

```
Layer 1: Edge (CloudFront/Cloudflare)
  - WAF
  - DDoS protection
  - TLS termination
  - Rate limiting

Layer 2: API Gateway
  - JWT validation
  - Request validation
  - API key verification
  - RBAC enforcement

Layer 3: Application
  - Input sanitization
  - Authorization checks
  - CSRF protection
  - Rate limiting per user

Layer 4: Data
  - Encryption at rest (AES-256)
  - Encryption in transit (TLS 1.3)
  - Column-level encryption (PGP)
  - Vault for secrets

Layer 5: Audit
  - Immutable logging
  - Real-time alerting
  - Anomaly detection
  - Forensic readiness
```

---

## 7. Deployment Architecture

### 7.1 Production Architecture (Kubernetes)

```
┌────────────────────────────────────────────────────────────────┐
│                        Kubernetes Cluster                        │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │  Namespace:    │    │  Namespace:   │    │  Namespace:   │       │
│  │  veriunlearn-app│    │  veriunlearn-ml│    │  veriunlearn-infra│    │
│  │                │    │                │    │                │       │
│  │  - api-gateway │    │  - unlearning  │    │  - postgresql  │       │
│  │  - auth-svc    │    │    - worker    │    │  - redis       │       │
│  │  - chat-svc    │    │  - verification│    │  - qdrant      │       │
│  │  - rag-engine  │    │  - security    │    │  - minio       │       │
│  │  - memory-svc  │    │  - mlflow     │    │  - rabbitmq    │       │
│  │  - admin-svc   │    │                │    │  - eventstore  │       │
│  │  - compliance  │    │                │    │  - prometheus  │       │
│  │  - frontend    │    │                │    │  - grafana     │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                                                                  │
│  Ingress Controller (Traefik/NGINX)                              │
│  Cert-Manager (Let's Encrypt)                                    │
│  External Secrets (AWS Secrets Manager / Vault)                  │
│  Horizontal Pod Autoscaler                                       │
└────────────────────────────────────────────────────────────────┘
```

### 7.2 Multi-Cloud Strategy

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   AWS        │    │   GCP        │    │   Azure      │
│──────────────│    │──────────────│    │──────────────│
│  - EKS       │    │  - GKE       │    │  - AKS       │
│  - RDS       │    │  - Cloud SQL │    │  - Azure SQL │
│  - ElastiCache│   │  - Memorystore│   │  - Redis Cache│
│  - S3        │    │  - GCS       │    │  - Blob      │
│  - Route53   │    │  - Cloud DNS │    │  - DNS       │
└──────────────┘    └──────────────┘    └──────────────┘
         │                  │                   │
         └──────────────────┼───────────────────┘
                            │
                    ┌───────┴───────┐
                    │  Terraform     │
                    │  Crossplane    │
                    └───────────────┘
```

---

## 8. Technology Stack

### 8.1 Frontend
| Technology | Purpose |
|------------|---------|
| Next.js 15 (App Router) | Meta-framework |
| React 19 | UI library |
| TypeScript 5 | Type safety |
| TailwindCSS v4 | Styling |
| Shadcn UI | Component library |
| Framer Motion | Animations |
| React Query (TanStack Query v5) | Server state |
| Zustand | Client state |
| React Hook Form + Zod | Forms + validation |
| Lucide Icons | Icon library |
| React Markdown + Rehype | Markdown rendering |
| KaTeX | LaTeX rendering |
| Code Hike / Prism | Syntax highlighting |
| WebRTC / WebSockets | Voice I/O |

### 8.2 Backend
| Technology | Purpose |
|------------|---------|
| FastAPI | REST API framework |
| SQLAlchemy 2.0 | ORM |
| Alembic | Migrations |
| Pydantic v2 | Validation |
| Celery | Task queue |
| RabbitMQ | Message broker |
| Redis | Cache + pub/sub |
| PostgreSQL 16 | Primary database |
| Opentelemetry | Distributed tracing |

### 8.3 Machine Learning
| Technology | Purpose |
|------------|---------|
| Python 3.12 | Runtime |
| PyTorch 2.x | Deep learning |
| Transformers | LLM integration |
| Sentence Transformers | Embeddings |
| PEFT | Efficient fine-tuning |
| Accelerate | Distributed training |
| MLflow | Experiment tracking |
| SISA Implementation | Unlearning algorithm |
| Influence Functions | Data influence computation |

### 8.4 Security & Cryptography
| Technology | Purpose |
|------------|---------|
| PyCryptodome | Cryptographic primitives |
| ed25519 | Digital signatures |
| MerkleTools | Merkle tree implementation |
| snarkjs / circom | zkSNARK (circuit compilation) |
| python-jose | JWT |
| passlib + bcrypt | Password hashing |
| OWASP ZAP | Security scanning |

### 8.5 Infrastructure
| Technology | Purpose |
|------------|---------|
| Docker | Containerization |
| Kubernetes | Orchestration |
| Terraform | IaC |
| Helm | Package management |
| Prometheus + Grafana | Monitoring |
| Loki | Log aggregation |
| Tempo | Tracing |
| GitHub Actions | CI/CD |
| Trivy | Container scanning |

---

## 9. API Architecture

### 9.1 Design Principles

- RESTful for CRUD operations
- SSE for streaming chat responses
- WebSocket for real-time notifications
- GraphQL for admin dashboards (optional)
- OpenAPI 3.1 specification
- Versioned via URL prefix (/api/v1/)

### 9.2 API Domains

| Domain | Base Path | Service |
|--------|-----------|---------|
| Authentication | /api/v1/auth | Auth Service |
| Users | /api/v1/users | Auth Service |
| Chat | /api/v1/chat | Chat Service |
| Conversations | /api/v1/conversations | Chat Service |
| Messages | /api/v1/messages | Chat Service |
| AI Providers | /api/v1/providers | AI Service |
| RAG | /api/v1/rag | RAG Engine |
| Documents | /api/v1/documents | RAG Engine |
| Memory | /api/v1/memory | Memory Service |
| Unlearning | /api/v1/unlearning | Unlearning Engine |
| Verification | /api/v1/verify | Verification Engine |
| Security | /api/v1/security | Security Engine |
| Audit | /api/v1/audit | Audit Service |
| Compliance | /api/v1/compliance | Compliance Service |
| Admin | /api/v1/admin | Admin Service |
| Health | /api/v1/health | All Services |

### 9.3 Authentication Flow

```
Client                    API Gateway              Auth Service
  │                          │                        │
  │── POST /auth/login ─────▶│── POST /auth/login ──▶│
  │                          │                        │
  │                          │◀── {access, refresh} ─│
  │◀── {access, refresh} ────│                        │
  │                          │                        │
  │── GET /chat (Bearer) ───▶│── Validate JWT ──────▶│
  │                          │◀── Valid ─────────────│
  │                          │── Proxy to Chat ─────▶│
  │◀── 200 OK ──────────────│                        │
```

### 9.4 Streaming Architecture

```
Client                    API Gateway              Chat Service
  │                          │                        │
  │── POST /chat/stream ────▶│── POST /stream ──────▶│
  │                          │                        │
  │                          │     AI Provider        │
  │                          │         │              │
  │                          │◀──── SSE stream ──────│
  │◀── SSE: event: token ────│                        │
  │◀── SSE: event: done ─────│                        │
  │◀── SSE: event: error ────│                        │
```

---

## 10. Folder Structure

```
veriunlearn/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml
│   │   ├── cd.yml
│   │   ├── security-scan.yml
│   │   └── release.yml
│   ├── CODEOWNERS
│   └── dependabot.yml
│
├── packages/
│   ├── backend/
│   │   ├── alembic/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   │   ├── v1/
│   │   │   │   │   ├── auth.py
│   │   │   │   │   ├── chat.py
│   │   │   │   │   ├── rag.py
│   │   │   │   │   ├── memory.py
│   │   │   │   │   ├── unlearning.py
│   │   │   │   │   ├── verification.py
│   │   │   │   │   ├── security.py
│   │   │   │   │   ├── audit.py
│   │   │   │   │   ├── compliance.py
│   │   │   │   │   └── admin.py
│   │   │   │   └── deps.py
│   │   │   ├── core/
│   │   │   │   ├── config.py
│   │   │   │   ├── security.py
│   │   │   │   ├── database.py
│   │   │   │   ├── cache.py
│   │   │   │   ├── storage.py
│   │   │   │   ├── events.py
│   │   │   │   ├── exceptions.py
│   │   │   │   ├── middleware.py
│   │   │   │   └── logging.py
│   │   │   ├── domain/
│   │   │   │   ├── auth/
│   │   │   │   ├── chat/
│   │   │   │   ├── rag/
│   │   │   │   ├── memory/
│   │   │   │   ├── unlearning/
│   │   │   │   ├── verification/
│   │   │   │   ├── security/
│   │   │   │   ├── audit/
│   │   │   │   └── compliance/
│   │   │   │       ├── entities.py
│   │   │   │       ├── events.py
│   │   │   │       ├── repositories.py
│   │   │   │       ├── services.py
│   │   │   │       └── interfaces.py
│   │   │   ├── infrastructure/
│   │   │   │   ├── database/
│   │   │   │   ├── cache/
│   │   │   │   ├── queue/
│   │   │   │   ├── storage/
│   │   │   │   └── external/
│   │   │   └── main.py
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── pyproject.toml
│   │
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── (auth)/
│   │   │   │   ├── (dashboard)/
│   │   │   │   ├── (chat)/
│   │   │   │   └── (admin)/
│   │   │   ├── components/
│   │   │   │   ├── ui/
│   │   │   │   ├── chat/
│   │   │   │   ├── auth/
│   │   │   │   ├── rag/
│   │   │   │   ├── memory/
│   │   │   │   ├── unlearning/
│   │   │   │   ├── verification/
│   │   │   │   ├── security/
│   │   │   │   ├── audit/
│   │   │   │   ├── compliance/
│   │   │   │   └── admin/
│   │   │   ├── hooks/
│   │   │   ├── lib/
│   │   │   ├── stores/
│   │   │   ├── types/
│   │   │   └── providers/
│   │   ├── public/
│   │   ├── Dockerfile
│   │   ├── next.config.js
│   │   ├── tailwind.config.ts
│   │   └── package.json
│   │
│   ├── ml-engine/
│   │   ├── unlearning/
│   │   │   ├── algorithms/
│   │   │   ├── influence/
│   │   │   ├── sisa/
│   │   │   ├── certified_removal/
│   │   │   └── approximate/
│   │   ├── verification/
│   │   │   ├── merkle_tree.py
│   │   │   ├── signatures.py
│   │   │   ├── zksnark/
│   │   │   └── certificates.py
│   │   ├── security/
│   │   │   ├── attacks/
│   │   │   └── scoring.py
│   │   ├── models/
│   │   ├── training/
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   │
│   └── shared/
│       ├── types/
│       ├── validators/
│       └── constants/
│
├── infra/
│   ├── terraform/
│   │   ├── modules/
│   │   ├── environments/
│   │   │   ├── dev/
│   │   │   ├── staging/
│   │   │   └── production/
│   │   └── main.tf
│   ├── kubernetes/
│   │   ├── base/
│   │   ├── overlays/
│   │   └── helm/
│   ├── docker/
│   │   ├── docker-compose.yml
│   │   ├── docker-compose.prod.yml
│   │   └── docker-compose.monitoring.yml
│   ├── monitoring/
│   │   ├── prometheus/
│   │   ├── grafana/
│   │   └── loki/
│   └── scripts/
│
├── docs/
│   ├── architecture/
│   ├── api/
│   ├── deployment/
│   ├── security/
│   └── research/
│
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── README.md
├── LICENSE
└── pyproject.toml
```

---

## 11. Observability Architecture

### 11.1 Three Pillars

```
                         ┌──────────────────┐
                         │   Observability   │
                         └────────┬─────────┘
                                  │
            ┌─────────────────────┼─────────────────────┐
            │                     │                     │
     ┌──────┴──────┐      ┌──────┴──────┐      ┌──────┴──────┐
     │  Logging     │      │  Metrics     │      │  Tracing     │
     │  (Loki)      │      │  (Prometheus) │      │  (Tempo)     │
     └──────┬──────┘      └──────┬──────┘      └──────┬──────┘
            │                     │                     │
            └─────────────────────┼─────────────────────┘
                                  │
                         ┌────────┴────────┐
                         │     Grafana      │
                         └─────────────────┘
```

### 11.2 Metrics Collection

| Metric Type | Examples | Collection |
|-------------|----------|------------|
| RED Metrics | Request rate, errors, duration | OpenTelemetry |
| USE Metrics | CPU, memory, disk, network | Node Exporter |
| Business Metrics | Chats created, unlearning jobs, proofs generated | Custom |
| ML Metrics | Model accuracy, unlearning latency, proof time | MLflow |

### 11.3 Alerting Rules

- P0: Service down, data loss detected
- P1: Latency > 2s p99, error rate > 1%
- P2: Disk usage > 80%, CPU > 90%
- P3: Warning thresholds, non-critical

---

## 12. Research Architecture

### 12.1 Research Contributions

1. **Hybrid Adaptive Unlearning Controller**
   - Novel combination of SISA + Influence Functions + Certified Removal
   - Adaptive algorithm selection based on data characteristics
   - Theoretical guarantees on unlearning completeness

2. **Verifiable Deletion Proof System**
   - Merkle tree-based deletion certification
   - Ed25519 signatures for non-repudiation
   - zkSNARK integration for privacy-preserving verification
   - Formal verification of deletion guarantees

3. **Privacy-Preserving Audit Trail**
   - Merkle chain-based immutable log
   - Blockchain anchoring for decentralized verification
   - Zero-knowledge proofs for selective disclosure

4. **Unlearning-Aware Model Architecture**
   - SISA-inspired model partitioning
   - Influence function pre-computation
   - Efficient checkpoint management

### 12.2 Evaluation Metrics

| Metric | Target |
|--------|--------|
| Unlearning Latency | < 1s per data point |
| Model Utility Retention | > 95% |
| Proof Generation Time | < 100ms |
| False Positive Rate (MIA) | < 0.01 |
| Audit Log Throughput | > 10K events/sec |
| System Availability | 99.99% |

---

## 13. CI/CD Architecture

### Pipeline Stages

```
┌─────────┐   ┌──────────┐   ┌─────────┐   ┌─────────┐   ┌──────────┐
│  Lint   │──▶│   Test   │──▶│  Build  │──▶│  Scan   │──▶│  Deploy   │
│  & Type │   │  Unit    │   │  Docker │   │  Trivy  │   │  K8s      │
│  Check  │   │  + Int   │   │  Images │   │  + ZAP  │   │  + Helm   │
└─────────┘   └──────────┘   └─────────┘   └─────────┘   └──────────┘
                                                              │
                                                              ▼
                                                    ┌──────────────────┐
                                                    │  Smoke Tests     │
                                                    │  + Integration   │
                                                    │  + Performance   │
                                                    └──────────────────┘
```

### Branch Strategy

- `main` — Production-ready code
- `develop` — Integration branch
- `feature/*` — Feature branches
- `release/*` — Release candidates
- `hotfix/*` — Emergency fixes

---

## 14. Future-Proofing

- **Plugin Architecture** for third-party extensions
- **Multi-tenancy** with tenant isolation
- **White-label** support for enterprise customers
- **On-premise** deployment option
- **Air-gapped** deployment for classified environments
- **Federated learning** integration roadmap

---

*This document is the authoritative architectural reference for the VeriUnlearn platform. All implementation must conform to these architectural decisions.*
