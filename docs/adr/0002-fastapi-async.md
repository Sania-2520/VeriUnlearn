# ADR-0002: Async FastAPI + SQLAlchemy 2.0 backend

- **Status:** Accepted (2025-11)

## Context

The backend serves many concurrent I/O-bound requests (auth, chat streaming, RAG retrieval)
and async jobs. Synchronous ORM access would block the event loop.

## Decision

Backend is FastAPI with `async def` route handlers, SQLAlchemy 2.0 async engine
(`asyncpg`), and Pydantic v2 models. Services are constructed per-request with
`db: AsyncSession` via `Depends()`. No service holds cross-request state.

## Consequences

- ✅ High concurrency with a single worker process.
- ✅ Clean DI through `Annotated[AsyncSession, Depends(get_db)]` and `CurrentUser`.
- ❌ All DB access must be `await`-ed; sync libraries (e.g., some crypto) run via
  `asyncio.to_thread`.
- ❌ In-memory SQLite used in E2E tests must be `aiosqlite`-compatible.

## Alternatives considered

- Sync Flask/Django (rejected: poor async/streaming story).
- Raw asyncpg without ORM (rejected: too much boilerplate for 47+ models).
