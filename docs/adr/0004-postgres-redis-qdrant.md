# ADR-0004: Polyglot persistence (Postgres / Redis / Qdrant / MinIO)

- **Status:** Accepted (2025-12)

## Context

Different data shapes need different stores: relational governance data, a cache/queue,
vector embeddings for RAG, and large binary model artifacts.

## Decision

- **PostgreSQL 16** — primary relational store (users, governance, audit, verification).
- **Redis 7** — cache, rate limiting (sliding window), Celery broker/backend, pub/sub.
- **Qdrant** — vector embeddings for documents, memory, conversations (Cosine distance).
- **MinIO** — S3-compatible object storage for models, documents, proofs, exports.

All connections are configurable via environment variables (see `.env.example`).

## Consequences

- ✅ Each store used for its strength (SQL for integrity, vectors for ANN search).
- ❌ Operational surface grows (4 stateful services).
- ❌ Cross-store transactions are not atomic; consistency handled via the audit chain and
  Celery job retries.

## Alternatives considered

- Postgres-only with `pgvector` (rejected: Qdrant scales ANN search better for production).
- Single object store for everything (rejected: no relational integrity / fast cache).
