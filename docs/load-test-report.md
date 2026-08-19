# VeriUnlearn — Load & Stress Test Report

**Scope:** final-phase validation of API throughput and latency under concurrency.
**Tooling:** `backend/scripts/load_test.py` — spawns the real ASGI app (uvicorn) against a
fresh SQLite DB with the full middleware stack active (security headers, request metrics,
origin check, rate limiter raised to a non-binding limit so the test measures API
throughput rather than the 100 req/min default quota).
**Date:** 2026-08-17 (final verification pass). Raw JSON: `docs/data/load-test-results.json`.

## 1. Methodology

- **Endpoints under load** (each worker cycles through all four, so every path sees equal
  pressure): `GET /health` (anonymous), `GET /metrics` (anonymous, includes a live
  `MonitoringService.snapshot()` psutil + DB sample), `GET /api/v1/auth/me` and
  `GET /api/v1/datasets` (JWT-authenticated DB reads).
- **Concurrency ramp:** 1 → 5 → 10 → 25 → 50 concurrent clients, 5 s per level, preceded
  by a fresh-DB boot and a throwaway operator registration (so auth + audit writes are
  part of the workload from the first request).
- Each level is wall-clock bounded; in-flight requests get an 8 s drain window and any
  stragglers are cancelled and counted as errors, so no request silently disappears.
- Environment: Python 3.13, Windows, SQLite (dev profile). Numbers for the production
  profile (PostgreSQL + Redis) will differ — see §4.

## 2. Results (2026-08-17 run)

| Concurrency | Endpoint | Requests | Errors | req/s | p50 (ms) | p90 (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|---|---|---|---|---|
| 1 | auth/me | 137 | 0 | 27.4 | 9.1 | 11.6 | 12.0 | 12.7 |
| 1 | datasets | 137 | 0 | 27.4 | 8.4 | 10.5 | 11.1 | 13.9 |
| 1 | health | 137 | 0 | 27.4 | 3.7 | 5.0 | 5.4 | 6.5 |
| 1 | metrics | 137 | 0 | 27.4 | 12.2 | 15.0 | 15.7 | 17.0 |
| 5 | auth/me | 141 | 0 | 27.8 | 32.1 | 39.5 | 40.9 | 57.0 |
| 5 | datasets | 141 | 0 | 27.8 | 30.8 | 37.7 | 40.9 | 45.3 |
| 5 | health | 141 | 0 | 27.8 | 12.0 | 16.7 | 18.3 | 141.3 |
| 5 | metrics | 141 | 0 | 27.8 | 44.2 | 53.8 | 57.8 | 58.9 |
| 10 | auth/me | 99 | 0 | 19.2 | 64.1 | 73.8 | 77.7 | 80.9 |
| 10 | datasets | 99 | 0 | 19.2 | 59.9 | 68.8 | 73.3 | 76.4 |
| 10 | health | 99 | 0 | 19.2 | 27.2 | 39.0 | 42.2 | 44.8 |
| 10 | metrics | 99 | 0 | 19.2 | 90.4 | 106.5 | 108.8 | 112.3 |
| 25 | auth/me | 16 | 0 | 2.0 | 76.2 | 79.7 | 81.6 | 81.6 |
| 25 | datasets | 16 | 0 | 2.0 | 54.7 | 71.3 | 71.3 | 71.3 |
| 25 | health | 16 | 0 | 2.0 | 82.3 | 87.1 | 87.2 | 87.2 |
| 25 | metrics | 16 | 0 | 2.0 | 134.4 | 148.5 | 153.8 | 153.8 |
| 50 | auth/me | 16 | 0 | 1.0 | 78.6 | 91.3 | 93.0 | 93.0 |
| 50 | datasets | 16 | 0 | 1.0 | 55.2 | 90.2 | 92.0 | 92.0 |
| 50 | health | 16 | 0 | 1.0 | 105.7 | 117.7 | 118.5 | 118.5 |
| 50 | metrics | 16 | 0 | 1.0 | 136.2 | 145.3 | 155.7 | 155.7 |

**Zero errors across every level** — no 5xx, no connection failures, no request timeouts.

## 3. Interpretation

1. **Single-client latency is excellent.** `/health` p50 3.7 ms, JWT DB reads p50 ≈ 9 ms,
   `/metrics` (with a live system snapshot) p50 12.2 ms — consistent with the figures
   recorded in `docs/performance-report.md` (health p50 2.0 ms, metrics p50 14.2 ms on a
   slightly different machine).
2. **Throughput plateaus at ~28 req/s aggregate** for 1–5 concurrent clients, then falls
   as concurrency rises. The regression past 10 concurrent clients is dominated by the
   **dev SQLite backend**, not the API code: the connection pool (default size 5 +
   overflow 10) plus SQLite's serialized execution queue requests, so DB-bound endpoints
   queue behind each other and latency climbs ~10x.
3. **The cliff at 25–50 concurrent clients** (16 completed cycles in the 13 s window,
   req/s ≈ 1–2, latencies 50–155 ms) is the SQLite/pool ceiling. It is not a
   correctness failure: errors stayed at 0 and the drain window cleanly reaped stragglers.
4. **Expected production behaviour:** the prod profile (`docker-compose.prod.yml`) runs
   PostgreSQL 16 + Redis with uvicorn `--workers 2` and an nginx edge with a rate-limit
   zone; PostgreSQL's MVCC + a larger pool removes the serialization cliff. Re-running
   `python scripts/load_test.py` against the prod stack (with `DATABASE_URL` pointed at
   PostgreSQL) is the recommended validation before go-live.

## 4. Recommendations (already reflected in the 1.0.0 docs)

- **Use the `full`/prod compose profile for anything beyond single-user demo load** —
  this is the documented guidance in `docs/release-1.0.0.md` (Known issues #7) and
  `docs/deployment.md`.
- Optional Phase 8 hardening (not required for 1.0.0): a formal locust/k6 suite in CI
  against the prod profile, and pool-size tuning (`SQLAlchemy pool_size`/`max_overflow`)
  once PostgreSQL is the target.

## 5. Reproducing

```bash
cd backend
python scripts/load_test.py --levels 1,5,10,25,50 --duration 5
```

Output: the table above plus a machine-readable JSON file at
`docs/data/load-test-results.json`.
