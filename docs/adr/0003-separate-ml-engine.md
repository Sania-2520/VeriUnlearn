# ADR-0003: Separate ML Engine service

- **Status:** Accepted (2025-12)

## Context

ML training/inference is GPU-heavy and has a different scaling, dependency, and release
cadence than the REST API. Coupling them in one process would force API deploys to pull in
PyTorch and vice versa.

## Decision

Split into `packages/backend` (FastAPI + Celery + SQLAlchemy) and `packages/ml-engine`
(FastAPI + PyTorch + PEFT + MLflow). The backend reaches the engine over HTTP via
`MLEngineClient` (httpx), with retries and a typed client interface.

## Consequences

- ✅ Independent horizontal scaling (scale GPU nodes separately).
- ✅ Backend stays light; engine can use CUDA without affecting API latency.
- ❌ Network hop + serialization between API and engine; contract drift risk (mitigated by
  `MLEngineClient` interface + engine tests).
- ❌ Two services to operate (mitigated by docker-compose / Helm).

## Alternatives considered

- In-process ML module in backend (rejected: GPU memory + CUDA deps in API container).
- gRPC (rejected: HTTP/JSON simpler for mixed Python/JS clients, acceptable latency).
