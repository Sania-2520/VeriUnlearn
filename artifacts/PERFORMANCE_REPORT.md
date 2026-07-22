# VeriUnlearn — Performance Report

**Date:** 2026-07-18 · **Target:** v1.0 RC
Characteristics of each unlearning algorithm, the Backend→ML-Engine proxy overhead, and
scaling notes. Each figure is tagged **[measured]** (from `demo/benchmark-reports/sample-report.json`)
or **[estimated]** (from `hybrid_controller.py` heuristics / not yet run).

---

## 1. Per-Algorithm Characteristics

Measured end-to-end latency from the demo report (CIFAR-10):

| Algorithm | Latency (ms) [measured] | Accuracy [measured] | MIA success [measured] | Forget rate [measured] |
|-----------|------------------------:|--------------------:|-----------------------:|-----------------------:|
| SISA | 4258.1 | 0.8303 | 0.3372 | 0.8819 |
| Influence | 3999.2 | 0.8182 | 0.0923 | 0.8912 |
| Certified | 2595.3 | 0.8651 | 0.1219 | 0.8569 |
| Hybrid | 3317.4 | 0.8180 | 0.1631 | 0.8727 |

> Demo numbers are illustrative; **v1.0 harness run pending** → `<to be populated by eval harness>`.

### Heuristic estimates (not reported results)
`hybrid_controller.py:62-66` `_BASELINE_TIMES` (CPU, no GPU; ×1.5 when `CUDA_AVAILABLE=False`):

| Algorithm | small | medium | large |
|-----------|------:|-------:|------:|
| influence | 50 | 200 | 800 |
| sisa | 150 | 400 | 1200 |
| certified | 80 | 300 | 1000 |

These are planning estimates only; the e2e pipeline measures real `processing_time_ms`.

### Qualitative profile
- **SISA** — sharded retraining; higher latency, scales with `#shards`
  (`ControllerConfig.sisa_shards=10`); strong forget, weaker MIA resistance in demo.
- **Influence Functions** — fastest on small sets; best MIA resistance in demo; damping
  `influence_damping=1e-3`.
- **Certified Removal** — lowest latency in demo; `(ε=0.1, δ=1e-5)` guarantee
  (`ControllerConfig`); best for regulatory (GDPR/AI Act/HIPAA/CCPA) selection
  (`hybrid_controller.py:179-184`).
- **Full Retraining** — utility upper bound; highest cost (reference only).
- **Fine-Tune-Forgetting** — approximate; cheap, no guarantee.
- **Hybrid** — composes via `select_strategies` scoring (latency/accuracy/regulatory/GPU).

---

## 2. Proxy Overhead (Backend → ML Engine)

- Transport: `httpx.AsyncClient` over loopback/internal network
  (`packages/backend/app/infrastructure/external/ml_engine.py`).
- Each call constructs a **new** `httpx.AsyncClient` per request (no connection pool
  reuse) → added ~1-5 ms handshake per call **[estimated]**; candidate for a shared
  pooled client (TECHNICAL_DEBT).
- Default timeouts: 300s general, 600s benchmarks, 10s read-only (`ml_engine.py`).
- Error path wraps responses in `MLEngineClientError` with status/text logging.

---

## 3. Memory

- ML Engine: demo runs on CPU/numpy; **real torch models not yet wired in this env**
  (see LIMITATIONS). Peak GPU memory for SISA scales with shard count × batch
  **[estimated]**.
- Helm prod sets `deploy.resources.limits.memory: 16G` + 1 GPU
  (`infra/kubernetes/helm/veriunlearn/values/production.yaml`).

---

## 4. Scaling Notes

- Backend/UI scale horizontally on CPU replicas; ML Engine on GPU nodes.
- `HybridAdaptiveController` prefers SISA when `CUDA_AVAILABLE` and large data
  (`hybrid_controller.py:161-163`); Influence when CPU-only
  (`hybrid_controller.py:137-139`).
- Celery workers (`docs/adr/0007-celery-workers.md`) offload async unlearning jobs.
- HPA defined in `infra/kubernetes/helm/veriunlearn/templates/hpa.yaml`.

---

## 5. Status

- [x] Latency/accuracy/MIA measured in demo report (cite, don't claim as v1.0).
- [ ] v1.0 full eval (MNIST/CIFAR-10/IMDB/AG News) not yet executed.
- [ ] Memory profiling on real torch models pending (LIMITATIONS).

See `artifacts/BENCHMARK_PLAN.md` and `artifacts/LIMITATIONS.md`.
