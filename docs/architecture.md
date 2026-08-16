# VeriUnlearn — Architecture

## 1. Design principles

- **Clean architecture, dependency inversion** — API → services → repositories → models. Services
  depend on interfaces (e.g. `UnlearnableModel`, `VectorStore`), never on transports.
- **One transaction per request** — async SQLAlchemy sessions commit on success, roll back on error.
- **Append-only, never destructive** — deleted records are *tombstoned* (flagged + tombstone hash),
  never hard-deleted, so certificates stay verifiable forever.
- **Deterministic hashing** — canonical JSON + sorted Merkle leaves make every root reproducible.
- **Config-driven infrastructure** — SQLite/in-memory by default; PostgreSQL/Redis/Qdrant via env.

## 2. Component diagram

```mermaid
flowchart LR
    subgraph Frontend["Next.js Dashboard (port 3000)"]
        UI[Pages: Dashboard · Privacy Auditor · Certificates · Audit · Compliance · Attack Lab · Benchmark]
        RQ[React Query] --> API
    end

    subgraph Backend["FastAPI (port 8000)"]
        direction TB
        API[REST API /api/v1]
        AUTH[JWT auth + RBAC]
        SRV[Services]
        WRK[Background unlearning worker]
        REPO[Repositories]
        DB[(PostgreSQL / SQLite)]
        VEC[(Vector Store: memory / Qdrant)]
        RED[(Redis optional)]
        ML[ML Core: SISA · influence · certified removal · LoRA]
        CRYPTO[Crypto: Merkle · RSA · AES-GCM · ZK commitment]
    end

    UI --> API
    API --> AUTH
    API --> SRV
    SRV --> REPO --> DB
    SRV --> VEC
    SRV --> CRYPTO
    SRV --> ML
    API --> WRK --> SRV
    RED -. rate limits .- API
```

## 3. The unlearning pipeline (sequence)

```mermaid
sequenceDiagram
    participant U as Operator
    participant A as API
    participant S as UnlearningService
    participant M as SISA engine
    participant C as Crypto/Certificate
    participant DB as Database

    U->>A: POST /privacy/search?query=maya
    A->>S: scan all shards (decrypt PII, fuzzy match, confidence)
    S-->>U: matches (source, shard, influence, sensitivity, model)

    U->>A: POST /unlearning/selective {identity_key, method}
    A->>S: resolve records → affected shards
    S->>DB: capture PRE Merkle root
    S->>DB: tombstone records (is_deleted, tombstone_hash) + drop embeddings
    S->>M: scrub model (retrain shards | Newton step | gradient scrub)
    M-->>S: new weights_hash
    S->>DB: capture POST Merkle root (tombstone leaves)
    S->>C: issue certificate (roots, hashes, method, bound) → RSA sign
    C->>DB: persist certificate + PDF
    S->>DB: blockchain ledger entry + audit event (hash chain)
    S-->>U: 202 {request_id}
    U->>A: GET /unlearning/requests/{id} (poll → completed)
    U->>A: POST /verification/verify/{cert_id}
    A->>C: re-hash content, check signature, recompute post-root, verify audit chain
    C-->>U: {verified: true, ...}
```

## 4. SISA + certified removal

```mermaid
flowchart TB
    DS[Dataset] -->|stratified by label| SH1[Shard 0]
    DS --> SH2[Shard 1]
    DS --> SH3[Shard 2]
    DS --> SH4[Shard 3]
    SH1 --> M1[Model 0]
    SH2 --> M2[Model 1]
    SH3 --> M3[Model 2]
    SH4 --> M4[Model 3]
    M1 & M2 & M3 & M4 --> AG[Soft-voting aggregation]
    AG --> PRED[Predictions]

    DEL[Deletion request] -->|affects only| SH2
    SH2 -->|retrain OR Newton-step certified removal| M2n[Model 1′]
    M2n --> AG
```

- **SISA retrain** — gold standard: re-train only affected shard(s) on remaining data.
- **Certified removal** — for convex models, `w' = w − H⁻¹ ∇L(z_removed)` with the *exact* Hessian
  of the averaged regularised logistic loss. The certificate stores the bound
  `|f_{w'}(x) − f_w(x)| ≤ ‖w'−w‖₂ · max_x‖x‖₂` for every input `x`.

## 5. Merkle deletion proofs

```mermaid
flowchart LR
    R1[record 1] --> H1[leaf = SHA256(record_id, content_hash)]
    R2[record 2] --> H2[leaf]
    R3[record 3] --> H3[tombstone leaf after deletion]
    R4[record 4] --> H4[leaf]
    H1 & H2 --> P1[parent]
    H3 & H4 --> P2[parent]
    P1 & P2 --> ROOT[Pre/Post Merkle Root]
    ROOT --> CERT[RSA-signed certificate]
```

Leaves are sorted; deleting a record swaps its leaf for a deterministic tombstone
(`SHA256(record_id, content_hash, deleted)`) so the root provably changes and can be recomputed
from the live database during verification.

## 6. Data model (ER)

```mermaid
erDiagram
    USERS ||--o{ DELETION_REQUESTS : requests
    DATASETS ||--o{ DATASET_RECORDS : contains
    DATASETS ||--o{ ML_MODELS : trains
    ML_MODELS ||--o{ MODEL_SHARDS : owns
    DELETION_REQUESTS ||--o| CERTIFICATES : produces
    CERTIFICATES ||--o| AUDIT_EVENTS : anchored
    CERTIFICATES ||--o| BLOCKCHAIN_LEDGER : mirrored

    DATASETS { string id PK; string name; int shard_count; json feature_names }
    DATASET_RECORDS { string id PK; string dataset_id FK; int shard_id; json features; string content_hash; bool is_deleted; string tombstone_hash; string identity_key; string full_name_enc; float influence_score }
    ML_MODELS { string id PK; string dataset_id FK; int version; string weights_hash; json metrics }
    MODEL_SHARDS { string id PK; string model_id FK; int shard_index; string weights_path; string weights_hash; int record_version }
    DELETION_REQUESTS { string id PK; string identity_key; string method; string status; json record_ids; json shard_ids }
    CERTIFICATES { string id PK; string dataset_id; string pre_merkle_root; string post_merkle_root; string signature; json zk_proof }
    AUDIT_EVENTS { string id PK; string event_type; string prev_hash; string event_hash; json payload }
    BLOCKCHAIN_LEDGER { string id PK; string certificate_id FK; string cert_hash; string tx_hash }
```

## 7. Deployment topology

```mermaid
flowchart LR
    INET[Internet] --> NGINX
    NGINX --> FE[Next.js on Vercel / Docker]
    NGINX --> BE[FastAPI on Render / Docker]
    BE --> PG[(PostgreSQL)]
    BE --> QD[(Qdrant)]
    BE --> RD[(Redis)]
    BE --> CHAIN[(Ethereum testnet, optional)]
    BE --> STORE[Model weights / keys volume]
```

See [`deployment.md`](deployment.md) for environment variables and platform-specific steps.

## 8. Security model

| Layer | Mechanism |
|---|---|
| Authentication | JWT (HS256) with role claims; bcrypt password hashes |
| Authorization | RBAC: `admin`, `operator`, `auditor` (FastAPI dependency) |
| PII at rest | AES-256-GCM (key from HKDF of `SECRET_KEY`); identities decrypted only in memory |
| Integrity | SHA-256 content hashes, canonical JSON, sorted Merkle leaves |
| Non-repudiation | RSA-PKCS1v15 signatures over canonical certificate bodies |
| Audit | Hash-chained events; recomputation detects any tampering |
| Abuse | slowapi rate limiting, CORS allowlist, input validation, secure upload size caps |
