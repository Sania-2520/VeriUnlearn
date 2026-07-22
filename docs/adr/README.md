# Architecture Decision Records (ADRs)

This directory captures the significant architecture and design decisions made while building
VeriUnlearn. ADRs are numbered, immutable once accepted, and superseded ADRs are linked from
their status. Format based on Michael Nygard's ADR template.

| # | Title | Status | Date |
|---|-------|--------|------|
| [0001](0001-monorepo-packages.md) | Monorepo with `packages/` layout | Accepted | 2025-11 |
| [0002](0002-fastapi-async.md) | Async FastAPI + SQLAlchemy 2.0 backend | Accepted | 2025-11 |
| [0003](0003-separate-ml-engine.md) | Separate ML Engine service | Accepted | 2025-12 |
| [0004](0004-postgres-redis-qdrant.md) | Polyglot persistence (Postgres/Redis/Qdrant/MinIO) | Accepted | 2025-12 |
| [0005](0005-strategy-registry.md) | Strategy + Registry pattern for algorithms & verification | Accepted | 2026-01 |
| [0006](0006-event-bus.md) | In-process async EventBus for workflow orchestration | Accepted | 2026-01 |
| [0007](0007-celery-workers.md) | Celery + Redis for async jobs | Accepted | 2026-02 |
| [0008](0008-ed25519-merkle.md) | Ed25519 + SHA-256 Merkle for verification | Accepted | 2026-02 |
| [0009](0009-rbac-model.md) | 8-role / 24-permission RBAC model | Accepted | 2026-02 |
| [0010](0010-plugin-system.md) | DB-backed plugin system via importlib | Accepted | 2026-03 |
| [0011](0011-future-namespace.md) | Interface-only `app.future.*` namespace for Phases 7+ | Accepted | 2026-04 |
| [0012](0012-zero-knowledge-proofs.md) | Groth16-style zk-SNARK prototype for verification | Accepted (Prototype) | 2026-05 |
| [0013](0013-tenant-data-model.md) | Tenant-first data model with row-level isolation | Accepted | 2026-05 |
| [0014](0014-audit-hash-chain.md) | Tamper-evident SHA-256 audit hash chain + blockchain anchoring | Accepted | 2026-06 |

See also [architecture.md](../architecture.md) and [FUTURE_ROADMAP.md](../FUTURE_ROADMAP.md).
