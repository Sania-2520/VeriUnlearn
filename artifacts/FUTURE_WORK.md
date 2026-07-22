# VeriUnlearn — Future Work

**Date:** 2026-07-18 · **Target:** post-v1.0
Roadmap for closing the gaps identified in `artifacts/LIMITATIONS.md` and
`artifacts/TECHNICAL_DEBT.md`.

---

## 1. Wire orphaned security/verification modules (pre-GA candidate)
- **D-1** Invoke `packages/ml-engine/security/input_validator.py` in all API handlers
  (FastAPI dependency).
- **D-2** Emit structured audit events via `packages/ml-engine/security/audit_logger.py`
  on `/unlearn`, `/proof/*`, `/certificate`; persist to the Backend audit store.
- **D-3** Call `QualityEvaluator` (`verification/quality_metrics.py`) inside
  `unlearning/e2e_pipeline.py` and surface metrics in responses + benchmark reports.

## 2. Real-model evaluation
- Wire `membership_inference.py` and algorithm modules to actual `torch` models
  (`models/single_model.py`, `models/sharded_classifier.py`).
- Execute the v1.0 benchmark suite (MNIST, CIFAR-10, IMDB, AG News) on GPU and publish
  authoritative CSV/JSON/LaTeX via `evaluation/`.

## 3. Multi-tenant hardening
- Enforce per-tenant model isolation, quotas, and data residency end-to-end
  (Backend domain + ML Engine store).
- NetworkPolicy egress Backend→ML Engine only; tenant-scoped audit/proof namespaces.

## 4. Additional algorithms
- Add more unlearning strategies to `unlearning/algorithms/` and register them in
  `HybridAdaptiveController.algorithms` (`hybrid_controller.py:86-95`).
- Catastrophic forgetting / continual-learning aware unlearning (see `CONTINUAL_LEARNING_WRITE`).

## 5. Formal verification
- Strengthen `verification/zksnark/` from "ZK-adjacent" to a validated circuit; link to
  ADR-0012.
- Formal guarantees for Certified Removal parameters (`ε,δ`) under real distributions.

## 6. Performance / scale
- Pool `httpx` clients in `MLEngineClient` (remove per-call client creation).
- Benchmark SISA shard scaling; HPA tuning from `infra/kubernetes/helm/veriunlearn/templates/hpa.yaml`.

## 7. Testing & CI
- Contract tests for every `MLEngineClient` method (D-4).
- Coverage gates for algorithms (D-5) and frontend (D-6).
- Add `gitleaks` to `.github/workflows/ci.yml` if not present (AUDIT S-5).

## 8. Docs / OSS polish
- Single config-precedence doc (D-9); remove `docker-compose.phase5.yml` (D-8).
- Expand `docs/FUTURE_ROADMAP.md` from this list.

See `artifacts/IEEE_ASSET_LIST.md` for how future-work items map to publication claims.
