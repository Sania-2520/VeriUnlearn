"""Test fixtures.

- in-memory SQLite engine (StaticPool single shared connection)
- API client with the real FastAPI app and an overridden DB dependency
- the unlearning dispatcher is replaced with a recorder; tests execute the
  recorded requests inline (after the HTTP transaction commits) via
  ``run_unlearning_inline``
"""
from __future__ import annotations

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.services.unlearning import UnlearningService


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(db_engine):
    return async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def client(db_engine, session_factory):
    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    dispatched: list[str] = []

    async def recorder_dispatcher(request_id: str) -> None:
        dispatched.append(request_id)

    import app.api.v1.unlearning as unlearning_module

    original_dispatch = unlearning_module.dispatch_unlearning
    unlearning_module.dispatch_unlearning = recorder_dispatcher
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.dispatched = dispatched  # type: ignore[attr-defined]
        yield ac

    app.dependency_overrides.clear()
    unlearning_module.dispatch_unlearning = original_dispatch


async def run_unlearning_inline(session_factory, request_id: str) -> None:
    """Execute one recorded unlearning request in a fresh session."""
    async with session_factory() as session:
        await UnlearningService(session).execute(request_id)
        await session.commit()


@pytest_asyncio.fixture
async def auth_headers(client) -> dict:
    """Register + login a user; returns Authorization header."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "tester@veriunlearn.dev", "full_name": "Test User", "password": "password123"},
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
