# Async Architecture Report

**VeriUnlearn v1.0 Release Candidate** — 2026-08-08

## Status: PRODUCTION-SAFE

The async architecture audit and hardening for the v1.0 release is complete.
This report summarizes the concurrency fixes verified during this block and
the standing architecture that makes the runtime event-loop-safe.

## Verified fixes (this release block)

### HTTP client lifecycle — `MLEngineClient`
- All HTTP plumbing (connection pooling, retries with jitter, error
  normalization, header injection) was consolidated into a single `_request`
  helper backed by a **per-event-loop pooled `httpx.AsyncClient`** (100 max
  connections / 20 keep-alive).
- Clients are keyed by event-loop id, so FastAPI handlers on the main loop
  reuse keep-alive sockets while Celery tasks on fresh loops get their own
  client (no cross-loop socket reuse).
- `aclose()` closes every pooled client and is invoked from the FastAPI
  shutdown event — no leaked sockets on restart.

### Retry semantics
- Transient failures (429, 502/503/504, connection errors) retried with
  exponential backoff + jitter inside the client.
- `MLEngineClientError.status_code` + `is_transient` lets Celery tasks retry
  only transient failures (see RAG Pipeline Report).

### Celery worker lifecycle
- RAG tasks are bound tasks with explicit `max_retries`, progress states, and
  DB-backed status transitions — no unbounded retries, no lost updates.
- The `_run_async` bridge in `workers/utils.py` is the single supported
  coroutine bridge for Celery tasks (fresh event loop per invocation).

### Async DB / session handling
- Repositories and services use async SQLAlchemy sessions throughout; the RAG
  upload path flushes then commits atomically after dispatch decisions.
- Rate limiter fix (from the hardening block): denied requests no longer leave
  phantom members in the Redis sliding window (previously a fresh UUID was
  removed instead of the member that was added, letting rejected attempts keep
  the window saturated).

### Email delivery
- SMTP sending runs via `asyncio.to_thread` — never blocks the event loop.

## Standing architecture (unchanged, verified sound)

- `asyncio.run()` is confined to process entry points (alembic env, workers
  bridge, scripts); no nested event loops in library code.
- Streaming responses (`generate_text_stream`) use `client.stream()` with
  proper error classification; no `asyncio.run` inside handlers.
- ML Engine shutdown closes HTTP clients; cache and DB connections close in the
  shutdown event.
- GPU scheduler synchronization and HPO study isolation were addressed in the
  earlier hardening block (documented in COMPLETE_AUDIT_REPORT.md); no new
  issues were found in this pass.

## Remaining notes

- The only `asyncio.run` in library code lives in `training/benchmarks.py`
  (benchmark driver invoking the hybrid controller). It runs synchronously
  under a `to_thread` bridge from the API router, so it does not conflict with
  the running event loop; this is intentional and documented.
