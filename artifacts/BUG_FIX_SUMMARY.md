# VeriUnlearn — Bug Fix Summary (Tier-1)

**Phase:** 8 release-prep · **Date:** 2026-07-18
Changelog of the Tier-1 fixes completed ahead of the v1.0 RC. Each entry cites real
file:line references and the before → after behavior.

---

## B-1 — Removed hardcoded ZK secret from deleted `app.py`
- **File (removed):** root `app.py`
- **Before:** A standalone `app.py` at repo root embedded a hardcoded zero-knowledge
  secret in source.
- **After:** Root `app.py` deleted. ZK logic lives in
  `packages/ml-engine/verification/zksnark/` and reads secrets from configuration, not
  source. No secret remains in the tree.
- **Status:** Fixed · **Audit:** AUDIT_REPORT S-1.

## B-2 — Removed plaintext `proofs/users.json`
- **File (removed):** `proofs/users.json`
- **Before:** User identities/proofs stored in a plaintext JSON file under `proofs/`.
- **After:** Removed. Proofs/certificates are generated at runtime via
  `SignatureManager` (`packages/ml-engine/verification/signatures.py`) and written to
  `proofs/certificates/` as signed artifacts.
- **Status:** Fixed · **Audit:** AUDIT_REPORT S-2.

## B-3 — Removed divergent stale root `backend/`
- **File (removed):** root `backend/`
- **Before:** A duplicate, drifted `backend/` at repo root competed with the canonical
  `packages/backend/`, causing confusion about the source of truth.
- **After:** Removed. Canonical backend is `packages/backend/` (DDD:
  `app/domain/`, `app/infrastructure/`, `app/core/rbac.py`).
- **Status:** Fixed · **Audit:** AUDIT_REPORT S-3, M-1.

## B-4 — Added `MONITORING_READ` RBAC permission
- **File:** `packages/backend/app/core/rbac.py:37`
- **Before:** No `monitoring:read` permission; monitoring dashboards could not be
  RBAC-gated.
- **After:** Added `MONITORING_READ = "monitoring:read"` and granted to `admin`,
  `compliance_officer`, `unlearning_auditor`, `member`, `viewer` roles
  (lines 73, 89, 100, 119, 127).
- **Status:** Fixed · **Audit:** AUDIT_REPORT S-4.

## B-5 — Fixed `/unlearn/e2e` AttributeError
- **File:** `packages/ml-engine/api.py:1224`
- **Before:** The e2e route called a method that did not exist on the pipeline object →
  `AttributeError` (HTTP 500).
- **After:** Now calls `await pipeline.execute_full_pipeline(deletion_request)`; definition
  at `packages/ml-engine/unlearning/e2e_pipeline.py:96`.
- **Status:** Fixed · **Audit:** AUDIT_REPORT C-1.

## B-6 — Fixed `NameError` in knowledge-distill path
- **File:** `packages/ml-engine/.../distill*` (module logger)
- **Before:** A `logger` reference was used before definition → `NameError` in the
  distillation code path.
- **After:** Module-level `logger = logging.getLogger(__name__)` defined at import time.
- **Status:** Fixed · **Audit:** AUDIT_REPORT C-2.

## B-7 — De-shadowed duplicate `/train/checkpoints` route
- **File:** `packages/ml-engine/api.py`
- **Before:** Two handlers registered for `/train/checkpoints`; the second shadowed the
  first, making one behavior unreachable.
- **After:** Single canonical handler; duplicate removed.
- **Status:** Fixed · **Audit:** AUDIT_REPORT C-3.

## B-8 — Added backend routes: `/monitoring`, `/models`, `/training/start`, `/auth/oauth/{provider}/authorize`
- **File:** `packages/backend/app/api/v1/*`
- **Before:** These endpoints were missing from the Backend API surface.
- **After:** Added to the v1 router set (monitoring, model registry, training start,
  and OAuth provider authorize redirect).
- **Status:** Fixed · **Audit:** AUDIT_REPORT C-6.

## B-9 — Repointed `Makefile`
- **File:** `Makefile` (root)
- **Before:** `Makefile` referenced the removed root `backend/` and stale paths.
- **After:** Repointed to `packages/backend`, `packages/ml-engine`, `packages/frontend`.
- **Status:** Fixed.

## B-10 — Fixed controller/adapter route ordering
- **File:** `packages/ml-engine/api.py`
- **Before:** `/controller/health` and adapter routes were registered after more specific
  path conflicts, causing Starlette route-shadowing/wrong-handler dispatch.
- **After:** Route ordering corrected so specific paths resolve before parameterized
  ones (`/controller/health`, `/adapters/{name}/...`).
- **Status:** Fixed · **Audit:** AUDIT_REPORT C-5, C-7.

## B-11 — Created Helm value overlays
- **File:** `infra/kubernetes/helm/veriunlearn/values/staging.yaml`,
  `infra/kubernetes/helm/veriunlearn/values/production.yaml`
- **Before:** Only a single `values.yaml`; staging/prod divergence handled ad hoc.
- **After:** Explicit staging and production overlays committed.
- **Status:** Fixed.
