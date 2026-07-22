# ADR-0007: Celery + Redis for async jobs

- **Status:** Accepted (2026-02)

## Context

Training, unlearning, webhook delivery, and audit anchoring are long-running and must
survive request/response boundaries and retries.

## Decision

Use Celery with Redis as broker (`CELERY_BROKER_URL`) and result backend. Real tasks:
`execute_unlearning`, `generate_deletion_proof`, `dispatch_webhook`,
`retry_failed_webhooks` (beat 5 min), `cleanup_deletion_queue` (beat 30 min),
`audit.anchor_chains` (beat 6 h). Tasks open their own DB session (`worker_session`).

## Consequences

- ✅ Durable, retryable, scheduled work decoupled from API latency.
- ✅ Beat schedules cover webhook retry + cleanup + anchoring.
- ❌ Another moving part (Redis + worker processes) to operate.
- ❌ At-least-once semantics: tasks must be idempotent (guarded by `unlearning:lock`).

## Alternatives considered

- RQ (rejected: weaker scheduling/beat). ARQ (rejected: smaller ecosystem).
