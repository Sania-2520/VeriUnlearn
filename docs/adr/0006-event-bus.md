# ADR-0006: In-process async EventBus for workflow orchestration

- **Status:** Accepted (2026-01)

## Context

Unlearning → verification → governance → compliance is a multi-step workflow spanning
services. We wanted loose coupling without an external message broker for the core path.

## Decision

`app.core.events.EventBus` is an in-process async pub/sub singleton with 44 named events,
wildcard handlers, concurrent dispatch via `asyncio.gather` (per-handler error isolation),
and a 500-event history buffer. Lifespan wiring in `main.py` subscribes auto-actions
(e.g., `UNLEARNING_COMPLETED` → verify, `APPROVAL_GRANTED` → delete).

## Consequences

- ✅ Decoupled services; easy to add reactions (notifications, lineage).
- ✅ Debuggable via event history.
- ❌ In-process only — events do not survive process restart (durable work uses Celery).
- ❌ Not distributed; cross-process eventing is a future (`app.future.*`) concern.

## Alternatives considered

- Kafka/RabbitMQ for all events (rejected: heavy ops for single-process dev + tests).
- Database polling (rejected: latency + load).
