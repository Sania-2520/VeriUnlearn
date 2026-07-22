# VeriUnlearn — Security Audit & Threat Model

**Date:** 2026-07-18 · **Target:** v1.0 RC
This document describes the threat model and the security controls implemented in
VeriUnlearn, citing real modules. Severity: **Critical/High/Medium/Low**.

---

## 1. Trust Boundaries

```
 Tenant / Browser
      │  HTTPS
      ▼
 Frontend (Next.js)            packages/frontend
      │  Bearer JWT
      ▼
 Backend (FastAPI, DDD)        packages/backend   ← enforces RBAC + audit
      │  httpx (X-API-Key)
      ▼
 ML Engine (FastAPI)           packages/ml-engine  ← trusted internal, not public
      │
      ▼
 Storage: PostgreSQL, Redis, Qdrant, MinIO
```

The **Backend is the only component permitted to call the ML Engine**
(`MLEngineClient`, `packages/backend/app/infrastructure/external/ml_engine.py`).
The ML Engine should not be internet-exposed.

---

## 2. Threat Model

| Threat | Vector | Likelihood | Impact | Control |
|--------|--------|-----------|--------|---------|
| Unauthorized unlearn/deletion | Missing authz | Low | Critical | RBAC `rbac.py` + `require_permission` |
| Privilege escalation | Role confusion | Low | High | Explicit `ROLE_PERMISSIONS` map |
| Secret leakage | Hardcoded creds | Low (fixed) | Critical | Removed root `app.py` ZK secret; `.env` git-ignored |
| Plaintext PII at rest | `proofs/users.json` | Low (fixed) | High | Removed; signed certs only |
| MIA extraction of deleted data | Shadow models | Med | High | `security/attacks/membership_inference.py` eval |
| Tampered deletion proof | Forged signature | Low | High | `SignatureManager` Ed25519/RSA-4096 |
| Provenance tampering | Merkle root swap | Low | High | `MerkleTree` (`verification/merkle_tree.py`) |
| Audit gap | Unlogged action | Med | Medium | Backend audit domain + (TODO) `audit_logger.py` |

---

## 3. Controls

### 3.1 Authentication — OAuth / JWT / MFA
- Login via `POST /api/v1/auth/login`; frontend OAuth authorize route
  `GET /api/v1/auth/oauth/{provider}/authorize` (added in Tier-1).
- JWT signed with `JWT_SECRET_KEY`; MFA enforced per-tenant
  (`compliance.py:36` `mfa_enforced`, settings domain).
- Frontend MFA setup/verify pages under `packages/frontend/src/app/auth/mfa/`.

### 3.2 Authorization — RBAC
- `Permission` enum + `ROLE_PERMISSIONS` in `packages/backend/app/core/rbac.py`.
- Five roles: `admin`, `compliance_officer`, `unlearning_auditor`, `member`, `viewer`.
- Enforcement via `require_permission(Permission.*)` dependency (`app/api/deps.py`).
- **RC addition:** `MONITORING_READ` (`rbac.py:37`) gates `/monitoring`.

### 3.3 Data Deletion Guarantees
- GDPR/CCPA workflows in `packages/backend/app/api/v1/compliance.py`
  (deletion-request lifecycle, webhooks, audit).
- Backend proxies to ML Engine `/unlearn/e2e` → `execute_full_pipeline`
  (`packages/ml-engine/unlearning/e2e_pipeline.py:96`, wired `api.py:1224`).
- Each deletion yields a signed certificate under `proofs/certificates/VUC-*/`.

### 3.4 Provenance & Verification
- `MerkleTree` (`packages/ml-engine/verification/merkle_tree.py`) roots the deletion
  provenance; `SignatureManager` (`verification/signatures.py`) signs proofs
  (Ed25519 default, RSA-4096 option).
- zk-SNARK proofs in `packages/ml-engine/verification/zksnark/` (see ADR-0012).

### 3.5 Privacy Evaluation (ZK-adjacent)
- Membership-inference attack + AUC: `security/attacks/membership_inference.py`.
- Model-inversion / extraction attacks: `/attacks/model-inversion`, `/attacks/model-extraction`
  (client `ml_engine.py:900-985`).
- Quality/privacy composite: `verification/quality_metrics.py` (`QualityEvaluator`).
  **TODO:** wire into pipeline output (TECHNICAL_DEBT D-3).

### 3.6 Secrets Management
- No secrets in source (root `app.py` removed; `proofs/users.json` removed).
- `.env` git-ignored; Helm secrets via `--set secrets.*` / sealed secrets.
- Recommended: `gitleaks detect` in CI (DEPLOYMENT_CHECKLIST B).

### 3.7 Audit Logging
- Backend audit domain: `packages/backend/app/domain/audit/`.
- **TODO:** ML Engine `audit_logger.py` (`packages/ml-engine/security/audit_logger.py`)
  is not yet wired to API handlers (TECHNICAL_DEBT D-2).

---

## 4. Open Security Items (pre-GA)

- [ ] Wire `input_validator.py` at ML Engine boundary (D-1).
- [ ] Wire `audit_logger.py` (D-2).
- [ ] Confirm `gitleaks` step in `.github/workflows/ci.yml` (AUDIT S-5).
- [ ] NetworkPolicy egress from Backend→ML Engine only (`infra/kubernetes/helm/veriunlearn/templates/networkpolicy.yaml`).

See `artifacts/AUDIT_REPORT.md` and `artifacts/TECHNICAL_DEBT.md`.
