# VeriUnlearn — Architecture

System architecture for VeriUnlearn v1.0 RC. Diagrams use Mermaid.

---

## (a) High-Level System Context

```mermaid
flowchart TB
    User[Tenant / Browser]
    FE[Frontend\nNext.js 15\n:3000]
    BE[Backend\nFastAPI DDD\n:8000]
    MLE[ML Engine\nFastAPI\n:8001]
    PG[(PostgreSQL 16)]
    RD[(Redis 7)]
    QD[(Qdrant)]
    MI[(MinIO)]
    MON[Prometheus / Grafana / Loki]

    User -->|HTTPS| FE
    FE -->|Bearer JWT| BE
    BE -->|httpx + X-API-Key| MLE
    BE --> PG & RD & QD & MI
    MLE --> PG & RD & QD & MI
    BE & MLE --> MON
```

The **Backend is the only component permitted to call the ML Engine**
(`MLEngineClient`, `packages/backend/app/infrastructure/external/ml_engine.py`).
Frontend talks only to the Backend.

---

## (b) Unlearning + Verification Request Flow

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant BE as Backend
    participant MLE as ML Engine
    participant ST as Storage

    U->>FE: Submit deletion request
    FE->>BE: POST /api/v1/unlearning/requests (JWT)
    BE->>BE: RBAC check (require_permission)
    BE->>MLE: execute_e2e_unlearning() → POST /unlearn/e2e
    MLE->>MLE: execute_full_pipeline() (e2e_pipeline.py:96)
    MLE->>MLE: HybridAdaptiveController.select_strategies()
    MLE->>ST: Remove target data (SISA/Influence/Certified)
    MLE->>MLE: MerkleTree + SignatureManager proof
    MLE-->>BE: Signed certificate (VUC-*)
    BE->>ST: Audit log + compliance record
    BE-->>FE: Request status + certificate ID
    FE-->>U: Verification dashboard
```

---

## (c) RBAC Permission Model

```mermaid
flowchart LR
    subgraph Roles
        ADMIN[admin]
        CO[compliance_officer]
        UA[unlearning_auditor]
        MEM[member]
        VIEW[viewer]
    end

    subgraph Permissions
        UNL[unlearning:*]
        VER[verification:*]
        AUD[audit:read]
        COMP[compliance:*]
        MON[monitoring:read]
        SEC[security:*]
        BEN[benchmarks:*]
    end

    ADMIN --> UNL & VER & AUD & COMP & MON & SEC & BEN
    CO --> VER & AUD & COMP & MON
    UA --> UNL & VER & AUD & BEN & MON
    MEM --> UNL & VER & AUD & SEC & BEN & MON
    VIEW --> VER & AUD & BEN

    style ADMIN fill:#f96,stroke:#333
    style MON fill:#9f9,stroke:#333
```

Source: `packages/backend/app/core/rbac.py` (`Permission` enum + `ROLE_PERMISSIONS`).
`MONITORING_READ` added in RC (`rbac.py:37`).

---

## (d) CI/CD Pipeline

```mermaid
flowchart LR
    DEV[Push / PR] --> CI[ci.yml\nlint + type-check + test]
    CI -->|green| CD[cd.yml\nbuild images\nstage → prod]
    CD --> REL[release.yml\ntag + notes]
    REL --> ART[Artifacts\nHelm chart, images,\nbenchmark harness]
    CI -.->|fail| DEV
```

Workflows: `.github/workflows/{ci,cd,release}.yml`. Images deployed via
`infra/kubernetes/helm/veriunlearn/` (staging + production overlays).

---

_See also: `docs/adr/ADR-0001-architecture.md`, `artifacts/SECURITY_AUDIT.md`,
`artifacts/DEPLOYMENT_CHECKLIST.md`._
