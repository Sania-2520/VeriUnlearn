# VeriUnlearn — Architecture Diagrams

All diagrams use [Mermaid](https://mermaid.js.org/). They render on GitHub and in most
Markdown viewers. Companion prose: [architecture.md](architecture.md),
[database schema](architecture/02-database-schema.md).

---

## 1. System Context (C4 — Level 1)

```mermaid
flowchart TB
    U[Data Protection Officer / Engineer] -->|HTTPS| FE[Next.js Frontend :3000]
    FE -->|/api/v1| NG[Nginx Reverse Proxy]
    NG --> BE[FastAPI Backend :8000]
    BE -->|HTTP| ML[ML Engine :8001]
    BE --> PG[(PostgreSQL 16)]
    BE --> RD[(Redis 7)]
    ML --> QD[(Qdrant)]
    ML --> MI[(MinIO)]
    BE --> CW[Celery Worker]
    RD --> CW
    subgraph Observability
      PR[PROMETHEUS] --> GR[Grafana]
      LO[Loki] --> GR
    end
    BE --> PR
```

---

## 2. Container / Deployment Topology

```mermaid
flowchart LR
    subgraph Edge
      FE
    end
    subgraph App
      NG --> BE
      BE --> ML
      BE --> CW
    end
    subgraph Data
      PG
      RD
      QD
      MI
    end
    subgraph Ops
      PR
      GR
      LO
      AL[Alertmanager]
    end
```

---

## 3. Layered Architecture

```mermaid
flowchart TD
    API[API Layer\n28 routers v1+v2] --> SVC[Service Layer\n55 services]
    SVC --> DOM[Domain Layer\n47+ SQLAlchemy models]
    SVC --> ML[ML Layer\napp.ml.*]
    SVC --> INF[Infrastructure\nEventBus, RBAC, Crypto, Cache]
    DOM --> PG
    ML --> RD
    ML --> QD
    INF --> RD
    INF --> MI
```

---

## 4. Unlearning + Verification Sequence

```mermaid
sequenceDiagram
    autonumber
    actor User as DPO
    participant API as Backend API
    participant Val as ValidationEngine
    participant CK as CheckpointService
    participant Worker as Celery Worker
    participant Ctrl as AdaptiveController
    participant Engine as ML Engine
    participant Ver as VerificationService
    participant Audit as AuditService

    User->>API: POST /unlearning/requests
    API->>Val: validate target
    Val-->>API: OK
    API->>CK: snapshot pre-deletion model
    CK-->>API: checkpoint_id
    API->>Worker: execute_unlearning (async)
    Worker->>Ctrl: select algorithm
    Ctrl->>Engine: POST /unlearn
    Engine-->>Worker: before/after hash, metrics
    Worker->>API: UnlearningResult
    API->>Ver: auto-verify (event)
    Ver->>Engine: POST /proof/generate
    Engine-->>Ver: merkle_root, ed25519 sig
    Ver->>API: trust_score + certificate
    API->>Audit: append hash-chained event
    API-->>User: 201 + certificate_hash
```

---

## 5. Event-Driven Governance Flow

```mermaid
flowchart TD
    A[consent.withdrawn] --> B[policy re-evaluation]
    C[policy.violation.detected] --> D[approval.requested]
    D --> E{approved?}
    E -->|yes| F[deletion.triggered]
    E -->|no / timeout| G[approval.escalated]
    F --> H[unlearning.started]
    H --> I[unlearning.completed]
    I --> J[auto-verification]
    J --> K[certificate.generated]
    K --> L[audit.logged + chain anchored]
```

---

## 6. Database ER Diagram (core unlearning + verification + governance)

```mermaid
erDiagram
    tenants ||--o{ users : has
    users ||--o{ unlearning_requests : creates
    users ||--o{ sessions : owns
    tenants ||--o{ unlearning_requests : scopes
    unlearning_requests ||--o{ unlearning_jobs : spawns
    unlearning_jobs }o--|| model_versions : updates
    model_versions ||--o{ model_shards : shards
    unlearning_jobs ||--o{ deletion_proofs : produces
    deletion_proofs ||--o{ proof_verifications : checked_by
    unlearning_requests ||--o{ deletion_certificates : certifies
    tenants ||--o{ audit_events : emits
    audit_events ||--o{ audit_chain_heads : chains
    tenants ||--o{ consent_records : governs
    consent_records ||--o{ consent_history : tracks
    tenants ||--o{ policies : defines
    policies ||--o{ policy_violations : triggers
    tenants ||--o{ approval_requests : routes
    tenants ||--o{ risk_assessments : scores
    tenants ||--o{ data_lineage : traces
    data_lineage }o--|| unlearning_requests : references
    tenants ||--o{ compliance_reports : publishes
```

> Full DDL (PostgreSQL, Redis, Qdrant, MinIO) is in
> [architecture/02-database-schema.md](architecture/02-database-schema.md).

---

## 7. Folder Structure

```mermaid
flowchart TD
    ROOT[VeriUnlearn] --> PKG[packages/]
    ROOT --> INFRA[infra/]
    ROOT --> DOCS[docs/]
    ROOT --> NGINX[nginx/]

    PKG --> BE[backend/\nFastAPI+Celery]
    PKG --> ML[ml-engine/\nPyTorch]
    PKG --> FE[frontend/\nNext.js]
    PKG --> SH[shared/]

    BE --> BEAPI[app/api/\nv1 + v2 routers]
    BE --> BESVC[app/domain/\nservices + entities]
    BE --> BECORE[app/core/\nconfig, rbac, events, crypto]
    BE --> BEMW[app/middleware/]

    ML --> MLU[unlearning/\n7 algorithms]
    ML --> MLV[verification/\nmerkle, zk, sig]
    ML --> MLEX[explainability/\nSHAP,LIME,IG]
    ML --> MLT[training/\nLoRA, CL, benchmarks]

    INFRA --> DOCK[docker/]
    INFRA --> K8S[k8s/]
    INFRA --> MON[monitoring/]
    INFRA --> TF[terraform/]
    INFRA --> SCR[scripts/]
```
