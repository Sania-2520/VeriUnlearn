import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.core.database import db, Base
from app.core.cache import cache
from app.infrastructure.external.ml_engine import ml_engine_client
from tests.conftest import MockRedis


@pytest.fixture(autouse=True)
def _mock_ml_engine():
    with patch.object(ml_engine_client, "health", AsyncMock(return_value={"status": "healthy"})):
        yield


@pytest.fixture(autouse=True)
async def _setup_db():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    db._engine = engine
    db._session_factory = session_factory
    cache._redis = MockRedis()
    app.dependency_overrides.clear()
    yield
    db._engine = None
    db._session_factory = None
    cache._redis = None
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/register", json={
        "email": "api_test@test.com",
        "password": "Test123!",
        "full_name": "Test User",
    })
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestHealthEndpoint:
    async def test_health_returns_json(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data

    async def test_root_returns_info(self, client):
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data


class TestAuthEndpoints:
    async def test_register_endpoint(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "Test123!",
                "full_name": "Test User",
            },
        )
        assert response.status_code == 201

    async def test_login_endpoint(self, client):
        await client.post("/api/v1/auth/register", json={
            "email": "login_test@example.com",
            "password": "Test123!",
            "full_name": "Test User",
        })
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "login_test@example.com",
                "password": "Test123!",
            },
        )
        assert response.status_code == 200


class TestChatEndpoints:
    async def test_list_sessions(self, client, auth_headers):
        response = await client.get("/api/v1/chat/sessions", headers=auth_headers)
        assert response.status_code == 200

    async def test_create_session(self, client, auth_headers):
        response = await client.post(
            "/api/v1/chat/sessions",
            json={"title": "Test Chat"},
            headers=auth_headers,
        )
        assert response.status_code == 201
