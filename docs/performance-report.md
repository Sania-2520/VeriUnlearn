# VeriUnlearn — Performance Report

Measured performance of the 1.0.0 build: API latency, unlearning cost, benchmark timing,
and the optimizations already in place (plus recommendations).

---

## 1. Summary

| Metric | Measured value | Context |
|---|---|---|
| API latency p50 / p95 (`/health`) | 2.0 ms / 2.7 ms | in-process ASGI, dev machine |
| API latency p50 (`/metrics`) | 14.2 ms | includes live monitoring snapshot |
| Certified removal | 0.32 s (40 records, 4 shards) | Adult Census, bound 1.5e3 |
| SISA shard retrain | 0.44 s (40 records) | Adult Census |
| Influence scrub | 0.13 s | fastest, lowest fidelity |
| Full test suite | ~33–82 s | 65 tests, SQLite |
| Benchmark run (6 methods) | seconds | in-memory clones, eval cap 2,000 |

## 2. API latency (measured)

50 sequential requests per endpoint over `ASGITransport` (no network overhead), Python 3.13:

| Endpoint | p50 | p95 | p99 |
|---|---|---|---|
| `GET /health` | 2.02 ms | 2.65 ms | 2.74 ms |
| `GET /metrics` | 14.20 ms | 16.98 ms | 30.44 ms |
| `GET /openapi.json` | 2.97 ms | 4.85 ms | 63.96 ms (first-call cold) |

Notes: `/metrics` cost is dominated by the live `MonitoringService.snapshot()` (psutil +
dependency pings) — an acceptable trade for observability; the monitoring UI caches it in
the browser (8 s poll). Real-network latency adds RTT on top of these numbers.

## 3. Unlearning cost (Adult Census, 8,000 records, 4 shards, 40 deleted)

| Method | Time | Utility (acc/F1) | Evidence |
|---|---|---|---|
| Full retrain (baseline) | n/a (all shards) | 0.777 / 0.362 | — |
| SISA retrain | 0.44 s | 0.777 / 0.362 | roots + certificate |
| Certified removal | 0.32 s | 0.777 / 0.362 | bound 1.5e3 |
| Influence scrub | 0.13 s | 0.760 / 0.143 | roots + certificate |

Cost scales with affected shards for SISA (not dataset size) and with record count for the
certified Newton step (cap 200/call) — the two mechanisms the framework advertises.

## 4. Optimizations already in place

- **Database**: async SQLAlchemy sessions; indexed columns on hot tables
  (`ix_notifications_user_id`, `ix_api_keys_key_hash`, `ix_system_metrics_sampled_at`,
  `ix_compliance_reports_created_at`, …); JSON columns for flexible payloads.
- **Caching**: `analytics_cache` table (keyed) for expensive analytics aggregates;
  TanStack Query client-side caching + 8 s polls on monitoring, 30 s on notifications.
- **Backend**: soft-vote inference is O(shards); per-shard weights are cached; metrics
  middleware never blocks requests (`try/except` around observability); `compileall`
  import-check in CI.
- **Frontend**: Next.js static/dynamic hybrid — dashboards pre-render where possible,
  dynamic pages are server-rendered on demand; shared UI bundle (~106 kB first load).
- **Docker**: multi-stage builds (wheels builder; Next standalone), non-root runtime,
  `--no-cache`-independent layers; images are lean by construction.
- **Benchmark**: in-memory clones avoid disk I/O per method; `eval_size` capped (2,000)
  for memory safety.

## 5. Load & stress smoke (ad hoc)

A quick concurrent smoke (50 sequential reqs × 3 endpoints) shows p99 ≤ 31 ms on a dev
laptop with zero tuning — the platform is latency-light at research scale. Formal load
testing (locust/k6) is a documented Phase 8 item; at 1.0.0 the CI gate is correctness
(65 tests) + build, not throughput.

## 6. Bottlenecks & recommendations

| Area | Current state | Recommendation (Phase 8) |
|---|---|---|
| Deep models | linear/logistic only | GPU training; vectorised shards |
| MIA probes | O(shards × eval_size) | sample-based auditing; caching per split |
| Background jobs | in-request execution | Celery/ARQ worker + queue metrics |
| Multi-instance | SQLite dev limits | Postgres/Redis (already in prod compose) |
| GPU metrics | not collected | extend `MonitoringService.snapshot()` |
| Frontend tests | none | Vitest + Testing Library |
| Formal load tests | none | locust suite in CI (nightly) |

## 7. Measuring it yourself

```bash
cd backend
../.venv/Scripts/python -m pytest tests -q            # correctness
../.venv/Scripts/python -m pytest tests -q --cov=app  # coverage
# API latency: see docs/performance-report.md §2 methodology (httpx ASGI loop)
# Benchmark: POST /api/v1/benchmark/run → CSV/JSON/Excel export
```
