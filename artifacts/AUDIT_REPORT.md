# VeriUnlearn — Repository Audit Report

**Scope:** Full audit of the VeriUnlearn monorepo as of Phase 8 release-prep (v1.0 RC).
**Date:** 2026-07-18
**Auditor:** Release-prep automated review (file/line verified where cited).

This report consolidates the security, correctness, and maintainability posture of the
repository and tracks the remediation status of each finding. Severity legend:
**Critical / High / Medium / Low / Info**.

---

## 1. Security

| # | Finding | Location | Severity | Status |
|---|---------|----------|----------|--------|
| S-1 | Hardcoded ZK secret in deleted `app.py` | (removed) `app.py` | Critical | **Fixed** — root `app.py` deleted; no ZK secret in source. ZK path uses `verification/zksnark/` with external config. |
| S-2 | Plaintext `proofs/users.json` | (removed) `proofs/users.json` | High | **Fixed** — file removed; users/certs now derived at runtime (`SignatureManager`, `verification/signatures.py`). |
| S-3 | Divergent stale root `backend/` | (removed) root `backend/` | High | **Fixed** — removed; canonical backend is `packages/backend/`. |
| S-4 | RBAC permission set incomplete | `packages/backend/app/core/rbac.py:5-37` | Medium | **Fixed** — added `MONITORING_READ = "monitoring:read"` (line 37) and wired into admin/compliance_officer/unlearning_auditor/member/viewer roles (lines 73,89,100,119,127). |
| S-5 | Secret scanning in CI | `.github/workflows/ci.yml` | Medium | **Open/Verify** — gitleaks referenced in `docs/DEPLOYMENT_CHECKLIST.md:46`; confirm step present in CI. |
| S-6 | Input validation at ML Engine boundary | `packages/ml-engine/security/input_validator.py` | Medium | **Open (see TECHNICAL_DEBT)** — module exists but is not wired into `packages/ml-engine/api.py` request handlers. |
| S-7 | Audit logging module unwired | `packages/ml-engine/security/audit_logger.py` | Medium | **Open (see TECHNICAL_DEBT)** — module exists but not invoked by API layer. |

### Security notes

- Auth is enforced in the Backend (`app/api/deps.py` `require_permission`, RBAC in
  `rbac.py`). The ML Engine is a trusted internal service reached only via
  `MLEngineClient` (`packages/backend/app/infrastructure/external/ml_engine.py`).
- Provenance/verification uses `MerkleTree` (`packages/ml-engine/verification/merkle_tree.py`)
  and `SignatureManager` (`packages/ml-engine/verification/signatures.py`, Ed25519/RSA-4096).
- See `artifacts/SECURITY_AUDIT.md` for the full threat model.

---

## 2. Correctness

| # | Finding | Location | Severity | Status |
|---|---------|----------|----------|--------|
| C-1 | `/unlearn/e2e` raised `AttributeError` | `packages/ml-engine/api.py` (e2e route) | High | **Fixed** — now calls `pipeline.execute_full_pipeline(deletion_request)` (`packages/ml-engine/api.py:1224`; def at `packages/ml-engine/unlearning/e2e_pipeline.py:96`). |
| C-2 | `NameError` in knowledge-distill path | `packages/ml-engine/.../distill*` | High | **Fixed** — module-level `logger = logging.getLogger(__name__)` defined before use. |
| C-3 | Duplicate `/train/checkpoints` route shadowing | `packages/ml-engine/api.py` | Medium | **Fixed** — de-shadowed; single canonical `/train/checkpoints` handler. |
| C-4 | Backend contract drift vs ML Engine routes | `packages/backend/app/infrastructure/external/ml_engine.py` vs `packages/ml-engine/api.py` | Medium | **Open (see TECHNICAL_DEBT)** — proxy exposes many routes; not all are covered by integration tests. |
| C-5 | Route ordering: `/controller/health` | `packages/ml-engine/api.py` | Low | **Fixed** — controller health route ordering corrected. |
| C-6 | `/monitoring`, `/models`, `/training/start`, `/auth/oauth/{provider}/authorize` missing | `packages/backend/app/api/v1/*` | Medium | **Fixed** — routes added in backend API layer. |
| C-7 | Adapter route ordering bug | `packages/ml-engine/api.py` (adapters) | Low | **Fixed** — adapter route ordering corrected. |

---

## 3. Maintainability

| # | Finding | Location | Severity | Status |
|---|---------|----------|----------|--------|
| M-1 | Divergent duplicate backend root | root `backend/` | High | **Fixed** — removed; canonical is `packages/backend/`. |
| M-2 | Orphaned security module: `input_validator.py` | `packages/ml-engine/security/input_validator.py` | Medium | **Open** — exists, not imported by API layer. |
| M-3 | Orphaned security module: `audit_logger.py` | `packages/ml-engine/security/audit_logger.py` | Medium | **Open** — exists, not imported by API layer. |
| M-4 | Orphaned verification module: `quality_metrics.py` | `packages/ml-engine/verification/quality_metrics.py` | Medium | **Open** — `QualityEvaluator` exists, not wired into unlearning pipeline output. |
| M-5 | Config sprawl (`config/settings.yaml`, `packages/*` settings, Helm values) | `config/settings.yaml`, `infra/kubernetes/helm/veriunlearn/values*.yaml` | Low | **Open** — consolidate documented in `artifacts/TECHNICAL_DEBT.md`. |
| M-6 | Stale `docker-compose.phase5.yml` present alongside `docker-compose.yml` | repo root | Low | **Open** — mark deprecated or remove before GA. |

---

## 4. Remediation Summary

- **Tier-1 fixes (done):** S-1, S-2, S-3, S-4, C-1, C-2, C-3, C-5, C-6, C-7, M-1.
- **Open / tracked in TECHNICAL_DEBT.md:** S-5, S-6, S-7, C-4, M-2, M-3, M-4, M-5, M-6.

See `artifacts/BUG_FIX_SUMMARY.md` for file:line references and before/after behavior of
the Tier-1 fixes.
