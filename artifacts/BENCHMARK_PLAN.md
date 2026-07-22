# VeriUnlearn — Benchmark Plan

**Version:** 1.0 RC · **Date:** 2026-07-18
This document specifies the evaluation suite used to substantiate the IEEE publication and
OSS benchmarking claims. All numbers in this plan are either derived from an existing demo
report (`demo/benchmark-reports/sample-report.json`) or marked
**`<to be populated by eval harness>`** where the v1.0 run has not yet executed.

---

## 1. Scope

Goal: quantify the trade-off between **forget quality**, **privacy**, and **utility
retention** across unlearning algorithms and datasets, and report **runtime / memory**
characteristics.

---

## 2. Datasets

| Dataset | Modality | Classes | Notes |
|---------|----------|---------|-------|
| MNIST | Vision (grayscale digits) | 10 | Baseline sanity set |
| CIFAR-10 | Vision (32×32) | 10 | Primary benchmark |
| IMDB | Text (reviews) | 2 | Sentiment / transformer |
| AG News | Text (news) | 4 | Transformer classification |

> Existing demo report exercised `cifar10`, `cifar100`, `tiny_imagenet`
> (`demo/benchmark-reports/sample-report.json:4-7`). MNIST/IMDB/AG News are added for
> the v1.0 IEEE study.

---

## 3. Algorithms (selectable via `HybridAdaptiveController`)

Implemented in `packages/ml-engine/unlearning/`:

- **SISA** — `unlearning/algorithms/sisa.py` (`SISAUnlearning`, sharded training).
- **Influence Functions** — `unlearning/algorithms/influence.py`
  (`InfluenceFunctionUnlearning`, damping in `ControllerConfig.influence_damping`).
- **Certified Removal** — `unlearning/algorithms/certified_removal.py`
  (`CertifiedRemovalUnlearning`, `(ε,δ)` from `ControllerConfig`).
- **Full Retraining** — reference baseline (utility upper bound).
- **Fine-Tune-Forgetting** — approximate forgetting via fine-tuning.
- **Hybrid** — `unlearning/hybrid_controller.py` (`HybridAdaptiveController.select_strategies`)
  dynamically composes the above.

---

## 4. Metrics

| Metric | Definition | Source module |
|--------|------------|---------------|
| Forget quality / forget rate | Fraction of target influence removed | `verification/quality_metrics.py` (`forget_rate`) |
| Membership-inference AUC / success rate | Attack success on retained vs. removed | `security/attacks/membership_inference.py` |
| Utility retention | Task accuracy post-unlearn vs. baseline | `verification/quality_metrics.py` (`retained_utility`) |
| Privacy leakage | Composite privacy risk score | demo report `privacy_leakage` |
| Model-inversion resistance | Resistance to inversion attack | demo report `model_inversion_resistance` |
| Runtime (latency_ms) | End-to-end unlearn latency | pipeline timing |
| Memory (peak) | Peak RSS / GPU mem | `<to be populated by eval harness>` |

---

## 5. Output Formats

The harness (`evaluation/` + `demo/benchmark-reports/`) emits:

- **CSV** — one row per (dataset, algorithm) with all metrics.
- **JSON** — machine-readable, schema-compatible with
  `demo/benchmark-reports/sample-report.json` (report_id, datasets, algorithms, results[], summary{}).
- **LaTeX** — `\begin{tabular}` tables for the paper (forget rate, MIA AUC, utility,
  runtime). Figures exported as PDF/PNG for §architecture + §results.

> Example existing metrics (CIFAR-10, from `sample-report.json`):
> certified → accuracy 0.8651, mia_success_rate 0.1219, latency_ms 2595.3,
> forget_rate 0.8569. These are demo numbers; the v1.0 harness will regenerate.

---

## 6. Reproducibility Harness

- **Location:** `evaluation/` — `runner.py`, `run_all.py`, `datasets.py`, `algorithms.py`,
  `metrics.py`, `export.py`, `reproducibility.py`, `report.py`, `visualization.py`,
  `config.py`.
- **Determinism:** `QualityEvaluator` seeds `np.random.RandomState(42)`
  (`verification/quality_metrics.py:28`); harness records commit SHA + dataset hashes.
- **Trigger:** `MLEngineClient.run_benchmarks()`
  (`packages/backend/app/infrastructure/external/ml_engine.py:821`) → ML Engine
  `/benchmarks/run`; summary via `/benchmarks/summary`.
- **Baseline heuristics:** `hybrid_controller.py:62-66` `_BASELINE_TIMES` (small/medium/large)
  used only for *estimates*, not for reported results.

---

## 7. Status

- [x] Suite structure and datasets defined.
- [x] Algorithms implemented and selectable.
- [x] Metrics modules present (`quality_metrics.py`, `membership_inference.py`).
- [ ] **v1.0 eval harness run not yet executed** — reported numbers are `<to be populated
      by eval harness>` except where cited from the demo report.
- See `artifacts/LIMITATIONS.md` and `artifacts/PERFORMANCE_REPORT.md`.
