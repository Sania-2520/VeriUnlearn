# Benchmark Guide

VeriUnlearn includes a benchmarking platform to compare unlearning algorithms across datasets
and measure the **utility / privacy / latency** trade-off objectively.

---

## What Gets Measured

The `BenchmarkService` runs each algorithm over a dataset for N trials and computes:

| Metric | Meaning |
|--------|---------|
| `accuracy` | Post-unlearning task accuracy |
| `precision` / `recall` / `f1` | Classification quality |
| `utility_retained` | 1 − (utility drop vs. retrained-from-scratch) |
| `mia_accuracy` | Membership-inference attack success (lower = better) |
| `privacy_leakage` | Aggregate privacy risk score |
| `latency_ms` | End-to-end unlearning time |
| `forget_quality` | How completely the forget set is removed |

Metrics are computed by `MetricsEngine` and tracked in Prometheus via `MetricsTracker`.

---

## Datasets

Nine built-in datasets (synthetic + real-world) are seedable:

| Category | Examples |
|----------|----------|
| Synthetic | `sentiment_synthetic`, `toxic_synthetic`, `pii_synthetic` |
| Real-world | `sst2`, `ag_news`, `tweet_eval`, `enron_spam` (adapters), etc. |

Register a dataset via `POST /datasets` (backend) or load from the registry and run:

```http
POST /api/v1/benchmarks/run
{
  "dataset": "sentiment_synthetic",
  "algorithms": ["sisa", "influence_function", "certified_removal", "hybrid"],
  "trials": 5
}
```

---

## Running Benchmarks

### Via Make

```bash
make benchmark     # run the default suite
make graphs        # render latency / utility / MIA charts
```

### Via ML engine directly

```http
POST http://localhost:8001/benchmarks/run
{ "dataset": "ag_news", "algorithms": ["sisa", "hybrid"], "trials": 3 }
```

```http
GET http://localhost:8001/benchmarks/summary
GET http://localhost:8001/benchmarks/results
GET http://localhost:8001/benchmarks/config
```

### Via CLI / scripts

```bash
python infra/scripts/run_benchmarks.py --dataset sentiment_synthetic --trials 5
python infra/scripts/generate_graphs.py
```

---

## Leaderboards & Comparison

`LeaderboardService` ranks algorithms across all benchmark runs; `ComparisonService`
produces cross-algorithm analysis. View via:

```http
GET /api/v1/benchmarks/leaderboard
```

Export results:

```http
GET /api/v1/benchmarks/results?format=csv
GET /api/v1/benchmarks/results?format=json
```

---

## Reference Results (synthetic, 5 trials)

| Algorithm | Utility Retained | MIA Accuracy | Latency (ms) |
|-----------|------------------|--------------|--------------|
| SISA | 0.95 ± 0.02 | 0.12 ± 0.03 | 1250 ± 200 |
| Influence | 0.93 ± 0.03 | 0.15 ± 0.04 | 350 ± 50 |
| Certified Removal | 0.91 ± 0.04 | 0.08 ± 0.02 | 180 ± 30 |
| Hybrid | 0.94 ± 0.02 | 0.11 ± 0.03 | 420 ± 80 |

---

## Reproducibility

`ReproducibilityService` captures the experiment environment (Python version, package
hashes, random seeds, git commit) into `ExperimentReproducibility` so any benchmark can be
re-run exactly. Use `POST /api/v1/benchmarks/run` with `seed` fixed, then read the
reproducibility record from the experiment run.

---

## Known Limitations

- Benchmark numbers depend on the base model (`BASE_MODEL_NAME`, default `Qwen/Qwen2.5-1.5B-Instruct`)
  and hardware (CUDA vs CPU — `DEVICE`).
- Latency figures include queue wait under Celery; for pure compute, run the ML engine
  single-threaded.
- Real-world datasets require network access to HuggingFace unless cached.
