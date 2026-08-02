import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.compiler import compiles


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
os.environ.setdefault("CELERY_TASK_EAGER_PROPAGATES", "true")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_CACHE_BACKEND", "memory")
os.environ.setdefault("SMTP_HOST", "")
os.environ.setdefault("SMTP_PORT", "587")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-secret")
os.environ.setdefault("GOOGLE_REDIRECT_URI", "http://localhost:8000/callback")
os.environ.setdefault("GITHUB_CLIENT_ID", "test-id")
os.environ.setdefault("GITHUB_CLIENT_SECRET", "test-secret")
os.environ.setdefault("GITHUB_REDIRECT_URI", "http://localhost:8000/callback")

from app.core.cache import cache
from app.core.database import Base, db, get_db
from app.main import app


class MockPipeline:
    def __init__(self, store: dict):
        self._store = store
        self._commands: list = []

    def zremrangebyscore(self, key, min_score, max_score):
        self._commands.append(("zremrangebyscore", key, min_score, max_score))
        return self

    def zcard(self, key):
        self._commands.append(("zcard", key))
        return self

    def zadd(self, key, mapping):
        self._commands.append(("zadd", key, mapping))
        return self

    def expire(self, key, ttl):
        self._commands.append(("expire", key, ttl))
        return self

    async def execute(self):
        results = []
        for cmd in self._commands:
            if cmd[0] == "zremrangebyscore":
                results.append(0)
            elif cmd[0] == "zcard":
                key = cmd[1]
                if key in self._store and isinstance(self._store[key], dict):
                    results.append(len(self._store[key]))
                else:
                    results.append(0)
            elif cmd[0] == "zadd":
                key = cmd[1]
                mapping = cmd[2]
                if key not in self._store:
                    self._store[key] = {}
                self._store[key].update(mapping)
                results.append(len(mapping))
            elif cmd[0] == "expire":
                results.append(True)
            else:
                results.append(None)
        return results


class MockRedis:
    def __init__(self):
        self._store = {}

    def pipeline(self):
        return MockPipeline(self._store)

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


@pytest_asyncio.fixture
async def async_client(client) -> AsyncClient:
    return client


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with db.session_factory() as session:
        yield session
