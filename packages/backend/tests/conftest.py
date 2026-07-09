import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import INET, UUID


@compiles(INET, "sqlite")
def compile_inet_sqlite(element, compiler, **kw):
    return "VARCHAR(45)"


@compiles(UUID, "sqlite")
def compile_uuid_sqlite(element, compiler, **kw):
    return "VARCHAR(36)"

os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-32-chars!!")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-at-least-32-chars!")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
os.environ.setdefault("CORS_ORIGINS", '["*"]')
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "true")
os.environ.setdefault("SMTP_HOST", "")
os.environ.setdefault("SMTP_PORT", "587")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-secret")
os.environ.setdefault("GOOGLE_REDIRECT_URI", "http://localhost:8000/callback")
os.environ.setdefault("GITHUB_CLIENT_ID", "test-id")
os.environ.setdefault("GITHUB_CLIENT_SECRET", "test-secret")
os.environ.setdefault("GITHUB_REDIRECT_URI", "http://localhost:8000/callback")

from app.main import app
from app.core.database import Base, db, get_db
from app.core.cache import cache


class MockRedis:
    def __init__(self):
        self._store = {}

    async def get(self, key):
        return self._store.get(key)

    async def setex(self, key, ttl, value):
        self._store[key] = value

    async def set(self, key, value):
        self._store[key] = value

    async def delete(self, *keys):
        for key in keys:
            self._store.pop(key, None)

    async def exists(self, key):
        return key in self._store

    async def expire(self, key, ttl):
        pass

    async def ttl(self, key):
        return 60

    async def incr(self, key):
        self._store[key] = self._store.get(key, 0) + 1
        return self._store[key]

    async def scan(self, cursor=0, match=None, count=None):
        keys = list(self._store.keys())
        if match:
            pattern = match.replace("*", "")
            keys = [k for k in keys if pattern in k]
        return 0, keys

    async def ping(self):
        return True

    async def close(self):
        self._store.clear()

    def pubsub(self):
        return AsyncMock()


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    @asynccontextmanager
    async def test_lifespan(_app):
        yield

    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = test_lifespan

    db._engine = engine
    db._session_factory = session_factory
    cache._redis = MockRedis()

    app.dependency_overrides[get_db] = db.get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    app.router.lifespan_context = original_lifespan
    db._engine = None
    db._session_factory = None
    cache._redis = None

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
