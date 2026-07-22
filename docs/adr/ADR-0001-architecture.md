# ADR-0001: Three-Tier Frontend / Backend / ML-Engine Architecture

- **Status:** Accepted
- **Date:** 2026-07-18
- **Deciders:** VeriUnlearn core maintainers
- **Supersedes / Superseded by:** Companion ADRs `docs/adr/0003-separate-ml-engine.md`,
  `docs/adr/0001-monorepo-packages.md`, `docs/adr/0002-fastapi-async.md`

## Context

VeriUnlearn is a machine-unlearning SaaS platform that must satisfy four audiences at
once: an IEEE publication, an open-source release, an enterprise demo, and a research
benchmarking community. The system needs to (a) present a polished product UI, (b) expose
a governed, auditable API surface, and (c) perform heavyweight, experiment-grade
unlearning / verification / privacy-attack computation without coupling those concerns
together.

Mixing the UI, the API/business logic, and the ML computation in a single process would
make the ML workloads hard to scale independently, would blur the security boundary
between tenant-facing requests and privileged model operations, and would complicate
reproducible research runs.

## Decision

We adopt a **three-tier monorepo** split under `packages/`:

1. **Frontend** (`packages/frontend`) — Next.js 15 application responsible for the
   product UI, dashboards, and OAuth/MFA login flows. It never talks to models directly.
2. **Backend** (`packages/backend`) — FastAPI DDD service (canonical). Hosts the domain
   model (`app/domain/`), infrastructure adapters (`app/infrastructure/`), RBAC
   (`app/core/rbac.py`), compliance/audit APIs, and proxies ML work over HTTP.
3. **ML Engine** (`packages/ml-engine`) — Separate FastAPI service that performs the
   actual unlearning algorithms (SISA, Influence Functions, Certified Removal, Full
   Retraining, Fine-Tune-Forgetting via `unlearning/hybrid_controller.py`), verification
   (Merkle tree, signatures, quality metrics), and security evaluation (membership
   inference, model inversion/extraction).

The **Backend is the only component that may call the ML Engine**, via the httpx-based
`MLEngineClient` (`packages/backend/app/infrastructure/external/ml_engine.py`). The
Frontend only calls the Backend. Shared types/constants live in `packages/shared`.

## Consequences

### Positive

- Independent scaling: the ML Engine can occupy GPU nodes while the Backend/UI scale on
  cheap CPU/replicas.
- Clean security boundary: tenant-facing API authz (RBAC) is enforced in the Backend;
  the ML Engine trusts the Backend and is not directly internet-exposed.
- Reproducible research: benchmark suites exercise the ML Engine and emit
  CSV/JSON/LaTeX via `evaluation/` and `demo/benchmark-reports/`.
- Clear ownership and review boundaries per package.

### Negative / Trade-offs

- Added network hop (proxy overhead) between Backend and ML Engine — documented in
  `artifacts/PERFORMANCE_REPORT.md`.
- Three deployable surfaces to operate and observe (mitigated by
  `infra/kubernetes/helm/veriunlearn` and `docker-compose.yml`).
- Risk of "contract drift" between the Backend proxy and ML Engine routes — tracked in
  `artifacts/TECHNICAL_DEBT.md` and `artifacts/AUDIT_REPORT.md`.

## Validation

- Routes exercised end-to-end via `/unlearn/e2e` → `execute_full_pipeline`
  (`packages/ml-engine/unlearning/e2e_pipeline.py:96`, wired in `packages/ml-engine/api.py:1224`).
- Health endpoints per tier (`/health`, `/controller/health`) for liveness/readiness.
- Helm chart deploys all three tiers (`infra/kubernetes/helm/veriunlearn/templates/`).
