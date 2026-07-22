# VeriUnlearn — Release Notes v1.0 (Release Candidate)

**Release:** v1.0.0-rc1 · **Date:** 2026-07-18
Target audiences: IEEE publication, OSS release, enterprise demo, research benchmarking.

---

## 1. User-Facing Highlights

- **Verifiable machine unlearning** with downloadable, signed deletion certificates
  (`proofs/certificates/VUC-*`), backed by Merkle-tree provenance and Ed25519 signatures.
- **Five unlearning strategies** selectable manually or automatically via the
  Hybrid Adaptive Controller: SISA, Influence Functions, Certified Removal, Full
  Retraining, Fine-Tune-Forgetting.
- **Privacy evaluation dashboard**: membership-inference AUC, model-inversion resistance,
  quality metrics.
- **Compliance workflows**: GDPR/CCPA deletion requests, webhooks, audit log, per-tenant
  settings (MFA enforcement, retention).
- **RBAC** with five roles; new `monitoring:read` permission gates the monitoring view.
- **Polished Next.js dashboard**: unlearning, models, training, monitoring, audit,
  benchmarks, webhooks, explainability, adapters, RAG.

## 2. Technical Highlights

- Three-tier architecture: `packages/frontend`, `packages/backend` (FastAPI DDD),
  `packages/ml-engine` (FastAPI). Backend↔ML Engine via `MLEngineClient` (httpx).
- End-to-end unlearning: `POST /unlearning/e2e` → `execute_full_pipeline`
  (`packages/ml-engine/unlearning/e2e_pipeline.py:96`).
- Reproducible benchmark harness in `evaluation/` emitting CSV/JSON/LaTeX.
- Helm chart with staging + production overlays
  (`infra/kubernetes/helm/veriunlearn/values/{staging,production}.yaml`).
- CI/CD: `.github/workflows/{ci,cd,release}.yml`.

## 3. Tier-1 Fixes in this RC

See `artifacts/BUG_FIX_SUMMARY.md` for file:line detail:

- Removed hardcoded ZK secret (root `app.py`) and plaintext `proofs/users.json`.
- Removed divergent root `backend/`; canonical is `packages/backend/`.
- Added `MONITORING_READ` RBAC permission.
- Fixed `/unlearn/e2e` `AttributeError` (now `execute_full_pipeline`).
- Fixed `NameError` in distill path; de-shadowed duplicate `/train/checkpoints`.
- Added backend routes `/monitoring`, `/models`, `/training/start`,
  `/auth/oauth/{provider}/authorize`; fixed controller/adapter route ordering.
- Repointed `Makefile`; created Helm staging/prod overlays.

## 4. Known Issues / Limitations (RC)

- ML Engine not yet wired to real torch models in this environment (LIMITATIONS).
- v1.0 benchmark harness not yet executed; demo numbers are illustrative
  (PERFORMANCE_REPORT, BENCHMARK_PLAN).
- Orphaned modules `input_validator.py`, `audit_logger.py`, `quality_metrics.py` exist
  but are not yet wired (TECHNICAL_DEBT D-1/D-2/D-3).
- Single-tenant assumptions remain in places (FUTURE_WORK).

## 5. Upgrade Notes

- DB migration: `docker compose exec backend alembic upgrade head` (or Helm job).
- Regenerate all secrets (DEPLOYMENT_CHECKLIST B); add `ML_ENGINE_API_KEY`.
- If upgrading from a pre-RC, remove any `docker-compose.phase5.yml` usage.

## 6. Checksums / Provenance

- Record the RC tag SHA at publish; attach reproducibility metadata from
  `evaluation/reproducibility.py`.
