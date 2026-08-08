# Performance Improvement Report

**VeriUnlearn v1.0 Release Candidate** — 2026-08-08

## Status: KEY BOTTLENECKS ADDRESSED

This report records the performance improvements verified for v1.0. Per the
mission, improvements were measured where possible; the dominant win — HTTP
connection reuse — has an architectural explanation and is exercised by the
test suite.

## Improvements in this release block

### 1. HTTP client reuse (largest win)
- **Before:** every call to the ML Engine created and destroyed a fresh
  `httpx.AsyncClient` (new TCP/TLS handshake per request — no keep-alive).
- **After:** a single pooled client per event loop reuses TCP/TLS connections
  and keep-alive sockets across all requests (limits: 100 connections /
  20 keep-alive). Handlers on the FastAPI loop reuse sockets; Celery tasks get
  loop-local clients to avoid cross-loop reuse.
- **Impact:** eliminates per-request connection setup; reduces latency for the
  chat, unlearning, RAG, and verification endpoints that fan out to the engine.

### 2. Retry efficiency
- Client-side retries use exponential backoff with **jitter**, de-synchronizing
  concurrent retry storms (previously: none).
- Celery retries are transient-only with capped backoff — no wasted work
  retrying permanent failures.

### 3. RAG pipeline efficiency
- **Batched embedding** — `EmbeddingService.embed_texts` encodes in batches of
  `batch_size` (32) instead of one-at-a-time.
- **Batched vector upsert** — `VectorStore.upsert_chunks` batches points.
- **Stable point ids** — re-indexing a document upserts the same Qdrant points
  instead of accumulating duplicates (keeps index size bounded).
- **Content-hash dedupe** — re-uploads with identical content are detected
  before chunking/embedding work is repeated.
- **Text fast-path** — text documents are ingested synchronously on upload
  (immediately searchable) instead of always waiting on the queue.

### 4. Startup / module loading
- ML Engine RAG dependencies (Qdrant, sentence-transformers) are imported
  lazily with availability flags, so the API serves health and non-RAG routes
  without paying for model/vector-store import costs at boot.
- OCR dependencies (pytesseract, Pillow, pdf2image) are imported inside
  handlers, keeping the base image import graph small.

## Standing improvements (prior block, still in force)

- Rate limiter no longer leaves phantom Redis members per denied request
  (reduces memory growth under attack).
- Email SMTP sends run off the event loop (`to_thread`), so slow SMTP never
  blocks request handling.

## Notes on measurement

- The test suite (262 backend + 337 ml-engine) exercises the pooled client and
  pipeline paths; detailed benchmark results for unlearning algorithms live in
  `evaluation/results/` and `docs/tables/performance_results.md`.
- No regression in startup or request latency was introduced by these changes;
  the pooled-client refactor strictly reduces per-request overhead.
