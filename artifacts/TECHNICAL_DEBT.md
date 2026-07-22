# VeriUnlearn — Technical Debt Catalog

**Date:** 2026-07-18 · **Target:** v1.0 GA
This catalog lists known technical debt with severity and recommended remediation. Items
marked **[BLOCKER]** should be resolved before GA; others are post-RC backlog.

---

## 1. Orphaned / Unwired Modules

### D-1 — `input_validator.py` not wired
- **Path:** `packages/ml-engine/security/input_validator.py`
- **Severity:** Medium
- **Detail:** A request-validation module exists but is not invoked by
  `packages/ml-engine/api.py` handlers, so unlearning/verify payloads are not centrally
  validated at the ML Engine boundary.
- **Remediation:** Import and call `validate_*` in each route handler, or register a
  FastAPI dependency. Add a test asserting rejection of malformed payloads.

### D-2 — `audit_logger.py` not wired
- **Path:** `packages/ml-engine/security/audit_logger.py`
- **Severity:** Medium
- **Detail:** Audit-logging helper exists but is not called by the API layer; ML Engine
  side-effects (proofs generated, deletions executed) are not captured in a structured
  audit trail consistent with the Backend's audit domain (`packages/backend/app/domain/audit/`).
- **Remediation:** Emit structured audit events on `/unlearn`, `/proof/*`, `/certificate`
  routes; persist to the same audit store the Backend reads.

### D-3 — `quality_metrics.py` not wired into pipeline
- **Path:** `packages/ml-engine/verification/quality_metrics.py` (`QualityEvaluator`)
- **Severity:** Medium
- **Detail:** `QualityEvaluator` computes forget rate, retention, membership-inference
  risk, model-inversion resistance, etc., but is not invoked by
  `unlearning/e2e_pipeline.py` or `unlearning/hybrid_controller.py`, so benchmark-quality
  metrics are not produced on real runs.
- **Remediation:** Call `QualityEvaluator.evaluate(...)` in the e2e pipeline and surface
  results in the response + benchmark reports.

---

## 2. Test Coverage Gaps

### D-4 — Backend↔ML-Engine contract coverage
- **Severity:** Medium
- **Detail:** `MLEngineClient` (`packages/backend/app/infrastructure/external/ml_engine.py`)
  exposes ~40 methods, but integration tests covering the contract drift (C-4 in
  AUDIT_REPORT) are incomplete.
- **Remediation:** Add a contract test that asserts every client method maps to a live
  ML Engine route; run in CI against a mock server.

### D-5 — Algorithm unit tests
- **Severity:** Medium
- **Detail:** `unlearning/algorithms/` (SISA, influence, certified) and `hybrid_controller.py`
  have limited coverage for the selection logic and retry paths.
- **Remediation:** Unit-test `select_strategies` scoring branches and `_execute_with_retries`.

### D-6 — Frontend coverage
- **Severity:** Low
- **Detail:** Dashboard pages under `packages/frontend/src/app/dashboard/**` lack a
  stated coverage gate.
- **Remediation:** Add Vitest/Jest coverage threshold to CI.

---

## 3. Duplicated Logic

### D-7 — Baseline time estimates duplicated
- **Severity:** Low
- **Detail:** Heuristic baseline times in `hybrid_controller.py:62-66`
  (`_BASELINE_TIMES`) partially overlap with benchmark metadata elsewhere.
- **Remediation:** Single source of truth in `evaluation/config.py` or shared constants.

### D-8 — Two compose files
- **Severity:** Low
- **Detail:** `docker-compose.yml` and `docker-compose.phase5.yml` both exist; risk of
  using the stale one.
- **Remediation:** Delete `docker-compose.phase5.yml` or clearly mark it deprecated.

---

## 4. Config Sprawl

### D-9 — Multiple configuration sources
- **Severity:** Low
- **Detail:** Settings live in `config/settings.yaml`, per-package settings, and three Helm
  value files (`infra/kubernetes/helm/veriunlearn/values.yaml`,
  `values/staging.yaml`, `values/production.yaml`). No single precedence doc.
- **Remediation:** Document precedence (env > Helm values > defaults) in `docs/deployment.md`.

---

## 5. Recommended Remediation Order (pre-GA)

1. D-2, D-3 — wire audit + quality metrics (correctness/trust for IEEE claims).
2. D-1 — wire input validator (security boundary).
3. D-4 — contract tests (prevent regression of C-4 drift).
4. D-5, D-6 — coverage gates.
5. D-7, D-8, D-9 — cleanup (post-RC acceptable).

See `artifacts/FUTURE_WORK.md` for the longer-term roadmap (multi-tenant hardening, formal
verification, additional algorithms).
