"""End-to-end integration tests covering the full API workflow."""
from unittest.mock import AsyncMock, patch

import pytest
from app.core.cache import cache
from app.core.database import Base, db
from app.infrastructure.external.ml_engine import ml_engine_client
from app.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tests.conftest import MockRedis


@pytest.fixture(autouse=True)
def _mock_ml_engine():
    with patch.object(ml_engine_client, "health", AsyncMock(return_value={
        "status": "healthy", "version": "1.0.0", "algorithms": ["sisa", "influence", "certified"],
    })):
        with patch.object(ml_engine_client, "execute_unlearning", AsyncMock(return_value={
            "success": True, "algorithm": "hybrid", "utility_retained": 0.97,
            "processing_time_ms": 150, "metrics": {},
        })):
            with patch.object(ml_engine_client, "generate_proof", AsyncMock(return_value={
                "merkle_root": "abc123def456", "merkle_tree": {"root": "abc123def456", "depth": 3},
                "signature_hex": "sig" + "0" * 62, "algorithm": "ed25519",
                "public_key_pem": "-----BEGIN PUBLIC KEY-----\npemdata\n-----END PUBLIC KEY-----",
                "leaf_count": 5, "tree_depth": 3,
            })):
                with patch.object(ml_engine_client, "verify_proof", AsyncMock(return_value={
                    "is_valid": True, "algorithm": "ed25519",
                })):
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


async def _register(client: AsyncClient, email: str, password: str = "Pass1234!", tenant_slug: str | None = None) -> dict:
    payload = {"email": email, "password": password, "full_name": "Test User"}
    if tenant_slug:
        payload["tenant_slug"] = tenant_slug
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201, f"Register failed: {resp.text}"
    return resp.json()


async def _login(client: AsyncClient, email: str, password: str = "Pass1234!") -> dict:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()


async def _make_admin(client: AsyncClient, user_id: str) -> None:
    from app.core.database import get_db
    from app.domain.auth.entities import UserRole
    from app.infrastructure.database.repositories.auth import SQLAlchemyUserRepository
    async for session in get_db():
        repo = SQLAlchemyUserRepository(session)
        user = await repo.get_by_id(user_id)
        user.role = UserRole.ADMIN
        await repo.update(user)
        await session.commit()
        break


@pytest.fixture
async def member_token(client: AsyncClient) -> str:
    data = await _register(client, "member@test.com")
    _ = data
    login_data = await _login(client, "member@test.com")
    return login_data["access_token"]


@pytest.fixture
async def admin_token(client: AsyncClient) -> str:
    data = await _register(client, "admin@test.com")
    user_id = data["user"]["id"]
    await _make_admin(client, user_id)
    login_data = await _login(client, "admin@test.com")
    return login_data["access_token"]


class TestE2EHealth:
    async def test_health(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "ml_engine" in data["components"]
        assert "database" in data["components"]
        assert "cache" in data["components"]

    async def test_liveness(self, client: AsyncClient):
        resp = await client.get("/health/live")
        assert resp.status_code == 200
        assert resp.json()["status"] == "alive"

    async def test_readiness(self, client: AsyncClient):
        resp = await client.get("/health/ready")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"


class TestE2EAuth:
    async def test_full_auth_flow(self, client: AsyncClient):
        reg = await _register(client, "flow@test.com")
        assert reg["user"]["email"] == "flow@test.com"
        assert reg["user"]["role"] == "member"
        assert "access_token" in reg

        login = await _login(client, "flow@test.com")
        assert "access_token" in login
        assert "refresh_token" in login
        assert login["token_type"] == "bearer"

        me = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {login['access_token']}"})
        assert me.status_code == 200
        assert me.json()["email"] == "flow@test.com"

    async def test_refresh_token(self, client: AsyncClient):
        await _register(client, "refresh@test.com")
        login = await _login(client, "refresh@test.com")
        resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_logout(self, client: AsyncClient):
        await _register(client, "logout@test.com")
        login = await _login(client, "logout@test.com")
        resp = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {login['access_token']}"},
            json={"refresh_token": login["refresh_token"]},
        )
        assert resp.status_code == 200

    async def test_unauthenticated_access_denied(self, client: AsyncClient):
        resp = await client.get("/api/v1/users/me")
        assert resp.status_code == 401

    async def test_invalid_token(self, client: AsyncClient):
        resp = await client.get("/api/v1/users/me", headers={"Authorization": "Bearer invalid"})
        assert resp.status_code == 401


class TestE2EUnlearning:
    async def test_create_list_get_request(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        create = await client.post(
            "/api/v1/unlearning/requests",
            params={"target_type": "user_data", "target_id": "data_001", "reason": "GDPR deletion"},
            headers=headers,
        )
        assert create.status_code == 201
        req_id = create.json()["request_id"]
        assert req_id
        assert create.json()["status"] in ("pending", "completed")

        listing = await client.get("/api/v1/unlearning/requests", headers=headers)
        assert listing.status_code == 200

        get_req = await client.get(f"/api/v1/unlearning/requests/{req_id}", headers=headers)
        assert get_req.status_code == 200


class TestE2EVerification:
    async def test_generate_and_verify_proof(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}

        create = await client.post(
            "/api/v1/unlearning/requests",
            params={"target_type": "conversation", "target_id": "conv_001"},
            headers=headers,
        )
        assert create.status_code == 201
        job_id = create.json()["job_id"]
        req_id = create.json()["request_id"]

        proof = await client.post(
            "/api/v1/verify/proofs/generate",
            params={"job_id": job_id, "request_id": req_id, "deletion_steps": ["step1", "step2"]},
            headers=headers,
        )
        assert proof.status_code == 201
        proof_id = proof.json()["id"]
        assert proof.json()["proof_type"] == "merkle"
        assert proof.json()["verified"] is False

        verify = await client.post(
            f"/api/v1/verify/proofs/{proof_id}/verify",
            headers=headers,
        )
        assert verify.status_code == 200
        assert verify.json()["is_valid"] is True

    async def test_list_proofs(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = await client.get("/api/v1/verify/proofs", headers=headers)
        assert resp.status_code == 200
        assert "data" in resp.json()

    async def test_certificate(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = await client.get("/api/v1/verify/certificates/nonexistent", headers=headers)
        data = resp.json()
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            cert = data.get("certificate") or data
            assert cert.get("certificate_id") is not None
            assert cert.get("status") is not None


class TestE2EAudit:
    async def test_audit_events(self, client: AsyncClient, member_token: str):
        headers = {"Authorization": f"Bearer {member_token}"}
        resp = await client.get("/api/v1/audit/events", headers=headers)
        assert resp.status_code == 200
        assert "data" in resp.json()

    async def test_chain_status(self, client: AsyncClient, member_token: str):
        headers = {"Authorization": f"Bearer {member_token}"}
        resp = await client.get("/api/v1/audit/chain/status", headers=headers)
        assert resp.status_code == 200

    async def test_anchor_chain(self, client: AsyncClient, member_token: str):
        headers = {"Authorization": f"Bearer {member_token}"}
        resp = await client.post("/api/v1/audit/chain/anchor", headers=headers)
        assert resp.status_code in (200, 201)


class TestE2ERBAC:
    async def test_member_cannot_access_admin(self, client: AsyncClient, member_token: str):
        resp = await client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {member_token}"})
        assert resp.status_code == 403

    async def test_admin_can_access_admin(self, client: AsyncClient, admin_token: str):
        resp = await client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200

    async def test_missing_permission(self, client: AsyncClient, member_token: str):
        headers = {"Authorization": f"Bearer {member_token}"}
        resp = await client.get("/api/v1/verify/proofs/nonexistent", headers=headers)
        assert resp.status_code == 404

        resp = await client.post(
            "/api/v1/verify/proofs/generate-zksnark",
            json={"job_id": "j", "request_id": "r", "leaf_data": "x", "all_leaves": ["x"]},
            headers=headers,
        )
        assert resp.status_code == 403
        assert "Missing" in resp.json()["detail"]


class TestE2ESecurity:
    async def test_security_headers(self, client: AsyncClient):
        resp = await client.get("/health")
        assert "content-security-policy" in resp.headers
        assert "strict-transport-security" in resp.headers
        assert "x-content-type-options" in resp.headers
        assert "x-frame-options" in resp.headers

    async def test_cors_headers(self, client: AsyncClient):
        resp = await client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )
        cors_present = (
            resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
            or resp.headers.get("access-control-allow-credentials") == "true"
        )
        assert cors_present
