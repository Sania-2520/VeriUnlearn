# VeriUnlearn — Diagrams

Editable diagram sources (Mermaid). Render on GitHub by viewing this file, on
[mermaid.live](https://mermaid.live), or via `npx @mermaid-js/mermaid-cli mmdc -i docs/diagrams.md -o out.svg`.
Each diagram is a self-contained fenced block — copy a block into mermaid.live to export
PNG/SVG for reports and presentations.

---

## 1. High-Level System Architecture

```mermaid
flowchart TB
    subgraph Clients
        U[User Browser]
        A[API Client / CI]
    end
    subgraph Frontend
        NX[Next.js App]
        NX -->|/api/v1| API
    end
    subgraph Backend
        API[FastAPI + Middleware<br/>RBAC · API keys · Rate limit · CSRF]
        SVC[Services Layer<br/>SISA · Certified · Influence · Merkle · Certificate · Verification]
        REPO[Repositories]
    end
    subgraph Storage
        DB[(PostgreSQL / SQLite)]
        VS[(Qdrant / in-memory vectors)]
        RED[(Redis)]
        KEYS[keys/ RSA keypair]
    end
    subgraph Observability
        PROM[Prometheus]
        GRAF[Grafana]
    end
    U --> NX
    A -->|X-API-Key| API
    API --> SVC --> REPO
    REPO --> DB
    SVC --> VS
    API --> RED
    SVC --> KEYS
    API -->|/metrics| PROM --> GRAF
```

## 2. Low-Level Architecture (Module View)

```mermaid
flowchart LR
    subgraph api
        A1[auth] A2[datasets] A3[models] A4[privacy] A5[unlearning]
        A6[verification] A7[certificates] A8[compliance] A9[research]
        A10[admin] A11[apikeys] A12[notifications] A13[monitoring] A14[analytics]
    end
    subgraph services
        S1[crypto/sisa/certified/influence] S2[merkle/certificate/verification_engine/zkproof]
        S3[pii_detection/privacy] S4[benchmark_engine/attacks/experiments/research_metrics]
        S5[admin/api_keys/notifications/monitoring/analytics/compliance]
    end
    subgraph repositories
        R1[user/dataset/model/deletion] R2[privacy/verification/research] R3[audit]
    end
    subgraph core
        C1[config/security/rbac/middleware/logging/exceptions]
    end
    api --> services --> repositories
    api --> core
    services --> core
```

## 3. ER Diagram (core entities)

```mermaid
erDiagram
    USERS ||--o{ API_KEYS : owns
    USERS ||--o{ DELETION_REQUESTS : creates
    USERS ||--o{ NOTIFICATIONS : receives
    DATASETS ||--o{ DATASET_VERSIONS : versions
    DATASETS ||--o{ MODELS : trains
    MODELS ||--o{ MODEL_SHARDS : has
    DELETION_REQUESTS ||--o{ TOMBSTONES : produces
    DELETION_REQUESTS ||--o| CERTIFICATES : issues
    CERTIFICATES ||--o| VERIFICATION_REPORTS : verified_by
    PRIVACY_REPORTS }o--|| DATASETS : scans
    EXPERIMENTS ||--o{ BENCHMARK_RESULTS : runs
    MODELS ||--o{ ATTACK_RESULTS : probed_by
    ROLES ||--o{ USERS : assigned
    USERS {
        string id PK
        string email UK
        string full_name
        string role
        boolean is_active
    }
    DATASETS {
        string id PK
        string name
        int shard_count
        int record_count
    }
    DELETION_REQUESTS {
        string id PK
        string method
        string scope
        string status
    }
    CERTIFICATES {
        string id PK
        string pre_merkle_root
        string post_merkle_root
        string signature
    }
```

## 4. Database Schema (Phase 7 tables added)

```mermaid
flowchart TB
    subgraph Phase7_Tables
        R[roles] --> U2[users.role]
        P[permissions]
        AK[api_keys] --> U2
        N[notifications] --> U2
        SM[system_metrics]
        CR[compliance_reports]
        DL[deployment_logs]
        AC[analytics_cache]
    end
    subgraph Phases1_6
        U[users] DT[datasets] M[models] MS[model_shards] DR[deletion_requests]
        TB[tombstones] CERT[certificates] VR[verification_reports] AE[audit_events]
        BR[benchmark_results] AR[attack_results] EXP[experiments] PM[performance_metrics]
        PR[privacy_reports] SH[search_history]
    end
```

## 5. DFD Level 0 (Context)

```mermaid
flowchart LR
    DP[Data Principal] -->|erasure request / search| SYS[VeriUnlearn System]
    OPS[Operator] -->|manage datasets, run unlearning| SYS
    AUD[Auditor] -->|verify certificates / audit trail| SYS
    RES[Researcher] -->|benchmarks / attacks| SYS
    SYS -->|evidence, certificates, reports| DP
    SYS -->|dashboards, monitoring| OPS
    SYS -->|verification results| AUD
    SYS -->|results, exports| RES
```

## 6. DFD Level 1 (Main processes)

```mermaid
flowchart LR
    P1[1.0 Ingest & Train] --> D1[(Dataset store)]
    P2[2.0 Search / Audit] --> D1
    P2 --> D2[(Tombstones)]
    P3[3.0 Unlearn] --> D2
    P3 --> D3[(Models + shards)]
    P4[4.0 Prove & Certify] --> D3
    P4 --> D4[(Certificates)]
    P5[5.0 Verify] --> D4
    P5 --> D5[(Audit events)]
    P6[6.0 Compliance & Platform] --> D4
    P6 --> D6[(Compliance reports)]
```

## 7. DFD Level 2 (Unlearning process 3.0)

```mermaid
flowchart LR
    REQ[erasure request] --> IA[3.1 Impact analysis]
    IA --> SEL{3.2 Scope: records/chat/dataset}
    SEL -->|records| RES[3.3 Resolve records]
    SEL -->|chat| CHAT[3.3 Resolve chat messages]
    SEL -->|dataset| DS[3.3 Resolve dataset]
    RES --> TOMB[3.4 Tombstone]
    CHAT --> TOMB
    DS --> TOMB
    TOMB --> SCRUB[3.5 Shard scrub / certified / influence]
    SCRUB --> ROOTS[3.6 Recompute Merkle roots]
    ROOTS --> CERT[3.7 Issue certificate + audit event]
```

## 8. Use Case Diagram

```mermaid
flowchart TB
    Admin[Admin] Ops[Operator] Res[Researcher] Aud[Auditor] Viewer[Viewer] DP[Data Principal]
    subgraph Platform
        UC1[Search identities] UC2[Run unlearning] UC3[Verify certificates]
        UC4[Manage users/roles] UC5[Issue API keys] UC6[Run benchmark/attacks]
        UC7[View compliance] UC8[View monitoring] UC9[Export reports]
        UC10[View dashboards]
    end
    DP --> UC1
    Ops --> UC2
    Aud --> UC3
    Aud --> UC7
    Admin --> UC4
    Admin --> UC5
    Admin --> UC8
    Res --> UC6
    Res --> UC9
    Viewer --> UC10
```

## 9. Class Diagram (core services)

```mermaid
classDiagram
    class IngestionService { +ingest_dataset() +shard() }
    class SISAService { +train_shards() +soft_vote() +retrain_shard() }
    class UnlearningService { +analyze_impact() +resolve_records() +execute() }
    class CertifiedRemovalService { +remove(records) bound }
    class MerkleEngine { +build_tree() +root() +prove_membership() }
    class CertificateService { +issue() +verify() }
    class VerificationEngine { +run_checks() report }
    class AuditService { +log() +verify_chain() }
    class PrivacyService { +search_identities() +footprint() }
    IngestionService --> SISAService
    UnlearningService --> CertifiedRemovalService
    UnlearningService --> MerkleEngine
    UnlearningService --> AuditService
    MerkleEngine --> CertificateService
    VerificationEngine --> CertificateService
    PrivacyService --> UnlearningService
```

## 10. Sequence Diagram (erasure request)

```mermaid
sequenceDiagram
    participant U as Data Principal
    participant F as Frontend
    participant API as API (FastAPI)
    participant SVC as UnlearningService
    participant DB as Database
    participant CRYPTO as Proof stack
    U->>F: Erasure request (identity/records)
    F->>API: POST /unlearning/impact
    API->>SVC: analyze_impact()
    SVC-->>API: report (shards, embeddings, est. time)
    F->>API: POST /unlearning/selective (method, scope)
    API->>SVC: execute()
    SVC->>DB: tombstone records
    SVC->>SVC: shard scrub / certified removal
    SVC->>CRYPTO: recompute Merkle roots
    CRYPTO-->>SVC: pre/post roots
    SVC->>CRYPTO: sign certificate
    SVC->>DB: append audit event
    API-->>F: 202 + request id
    F->>API: GET /unlearning/requests/{id}
    API-->>F: status, certificate id
```

## 11. Activity Diagram (deletion pipeline)

```mermaid
flowchart TB
    START([Start]) --> VAL{Method valid?}
    VAL -- no --> ERR[422 validation error]
    VAL -- yes --> SCOPE{Scope provided?}
    SCOPE -- no --> ERR
    SCOPE -- yes --> IMP[Impact analysis]
    IMP --> RES[Resolve records]
    RES --> TOMB[Tombstone records]
    TOMB --> M{Method}
    M -- retrain --> RET[SISA retrain affected shards]
    M -- certified --> CER[Newton-step removal]
    M -- influence --> INF[Gradient scrub]
    RET --> ROOT[Recompute Merkle roots]
    CER --> ROOT
    INF --> ROOT
    ROOT --> CERT[Issue certificate]
    CERT --> AUD[Audit event]
    AUD --> DONE([Request complete])
```

## 12. State Diagram (deletion request)

```mermaid
stateDiagram-v2
    [*] --> pending: created
    pending --> analyzing: impact analysis
    analyzing --> running: executed
    running --> completed: roots + certificate issued
    running --> failed: error
    failed --> running: retry
    completed --> verified: verification report
    completed --> [*]
    verified --> [*]
```

## 13. Deployment Diagram

```mermaid
flowchart TB
    subgraph Edge
        NGX[NGINX :80/443]
    end
    subgraph Docker_Network
        FE[frontend :3000 Next.js standalone]
        BE[backend :8000 FastAPI + alembic]
        PG[(postgres :5432)]
        RD[(redis :6379)]
        QD[(qdrant :6333)]
        PROM[prometheus :9090]
        GRAF[grafana :3001]
    end
    NGX --> FE
    NGX --> BE
    BE --> PG
    BE --> RD
    BE --> QD
    PROM -->|scrape /metrics| BE
    GRAF --> PROM
    BE --> VOL[(backend_data + keys volume)]
```

## 14. Component Diagram (verification flow)

```mermaid
flowchart LR
    subgraph VerificationEngine
        C1[records check] C2[embeddings check] C3[vectors check]
        C4[versions check] C5[merkle check] C6[signature check]
        C7[audit check] C8[consistency check]
    end
    DB[(DB)] --> C1 & C4 & C7
    VS[(Vector store)] --> C2 & C3
    CERT[certificate] --> C5 & C6
    VERDICT[Report: verdict + per-check results] --> EXPORT[PDF/JSON download]
    C1 & C2 & C3 & C4 & C5 & C6 & C7 & C8 --> VERDICT
```

## 15. Network Diagram

```mermaid
flowchart LR
    U[User] -->|HTTPS 443| NGX[NGINX]
    NGX -->|:3000| FE[Frontend]
    NGX -->|:8000| BE[Backend API]
    BE -->|5432| PG[(PostgreSQL)]
    BE -->|6379| RD[(Redis)]
    BE -->|6333| QD[(Qdrant)]
    PROM[Prometheus] -->|scrape :8000/metrics| BE
    GRAF[Grafana] -->|9090| PROM
    OPS[Operator] -->|3001| GRAF
```

## 16. Workflow Diagram (compliance loop)

```mermaid
flowchart LR
    A[Ingest] --> B[Shard + Train]
    B --> C[Identity Search / Footprint]
    C --> D[Impact Analysis]
    D --> E[Surgical Delete]
    E --> F[Merkle Pre/Post Roots]
    F --> G[RSA Certificate]
    G --> H[Audit Chain]
    H --> I[8-check Verification]
    I --> J[Compliance Snapshot + Export]
```

## 17. User Journey

```mermaid
journey
    title Data Principal erasure request
    section Request
      Submit erasure request: 4: User
      Receive confirmation: 4: User, System
    section Processing
      Search identity footprint: 5: System
      Impact analysis: 4: System
      Surgical deletion: 5: System
    section Evidence
      Certificate generated: 5: System
      Verification passed: 5: System
      Download PDF evidence: 5: User
```
