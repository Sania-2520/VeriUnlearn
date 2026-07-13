import pytest
from httpx import AsyncClient

from app.core.database import db
from app.domain.audit.entities import EventType, ActorType, EventStatus
from app.domain.audit.services import AuditService
from app.infrastructure.database.repositories.audit import SQLAlchemyAuditEventRepository


@pytest.fixture
async def audit_service(client: AsyncClient) -> AuditService:
    async with db.session_factory() as session:
        repo = SQLAlchemyAuditEventRepository(session)
        return AuditService(repo=repo)


class TestAuditServiceDirect:
    async def test_record_and_retrieve_event(self, client: AsyncClient):
        from app.domain.audit.entities import EventType, ActorType, EventStatus
        from app.domain.audit.services import AuditService
        from app.infrastructure.database.repositories.audit import SQLAlchemyAuditEventRepository

        async with db.session_factory() as session:
            repo = SQLAlchemyAuditEventRepository(session)
            svc = AuditService(repo=repo)
            event = await svc.record(
                tenant_id="test-tenant",
                event_type=EventType.USER_LOGOUT,
                actor_id="test-user",
                actor_type=ActorType.USER,
                action="test.logout",
                status=EventStatus.SUCCESS,
            )
            assert event.id is not None
            assert event.event_hash != ""
            assert event.event_type == EventType.USER_LOGOUT

            retrieved = await repo.get_by_id(event.id)
            assert retrieved is not None
            assert retrieved.action == "test.logout"
            assert retrieved.tenant_id == "test-tenant"


class TestAuditEventRecording:
    async def test_register_creates_audit_event(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "audit-reg@example.com", "password": "SecureP@ss123!", "full_name": "Audit Reg"},
        )
        assert resp.status_code == 201

        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        audit_resp = await client.get("/api/v1/audit/events", headers=headers)
        assert audit_resp.status_code == 200
        data = audit_resp.json()
        events = data["data"]
        assert len(events) >= 1
        assert any(e["action"] == "auth.register" for e in events)

    async def test_login_creates_audit_event(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "audit-login@example.com", "password": "SecureP@ss123!", "full_name": "Audit Login"},
        )
        token = (await client.post(
            "/api/v1/auth/login",
            json={"email": "audit-login@example.com", "password": "SecureP@ss123!"},
        )).json()["access_token"]

        headers = {"Authorization": f"Bearer {token}"}
        audit_resp = await client.get("/api/v1/audit/events?event_type=user.login", headers=headers)
        assert audit_resp.status_code == 200
        events = audit_resp.json()["data"]
        assert any(e["action"] == "auth.login" for e in events)

    async def test_audit_events_log_after_auth_actions(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "audit-multi@example.com", "password": "SecureP@ss123!", "full_name": "Audit Multi"},
        )
        token = (await client.post(
            "/api/v1/auth/login",
            json={"email": "audit-multi@example.com", "password": "SecureP@ss123!"},
        )).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        await client.post("/api/v1/auth/change-password", json={"current_password": "SecureP@ss123!", "new_password": "NewP@ss123!"}, headers=headers)

        audit_resp = await client.get("/api/v1/audit/events", headers=headers)
        assert audit_resp.status_code == 200
        actions = [e["action"] for e in audit_resp.json()["data"]]
        assert "auth.register" in actions
        assert "auth.login" in actions
        assert "auth.password.changed" in actions

    async def test_mfa_events_logged(self, client: AsyncClient):
        import pyotp

        await client.post(
            "/api/v1/auth/register",
            json={"email": "audit-mfa@example.com", "password": "SecureP@ss123!", "full_name": "Audit MFA"},
        )
        token = (await client.post(
            "/api/v1/auth/login",
            json={"email": "audit-mfa@example.com", "password": "SecureP@ss123!"},
        )).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        setup = await client.post("/api/v1/auth/mfa/totp/setup", json={"password": "SecureP@ss123!"}, headers=headers)
        secret = setup.json()["secret"]
        totp = pyotp.TOTP(secret)

        await client.post("/api/v1/auth/mfa/totp/enable", json={"secret": secret, "code": totp.now()}, headers=headers)

        code = totp.now()
        await client.post("/api/v1/auth/mfa/totp/disable", json={"code": code}, headers=headers)

        audit_resp = await client.get("/api/v1/audit/events", headers=headers)
        events = audit_resp.json()["data"]
        actions = [e["action"] for e in events]
        assert "auth.mfa.enabled" in actions
        assert "auth.mfa.disabled" in actions

    async def test_audit_events_require_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/audit/events")
        assert resp.status_code == 401

    async def test_audit_events_filtered_by_tenant(self, client: AsyncClient):
        email1 = "audit-tenant-a@example.com"
        email2 = "audit-tenant-b@example.com"

        for email in [email1, email2]:
            await client.post(
                "/api/v1/auth/register",
                json={"email": email, "password": "SecureP@ss123!", "full_name": email.split("@")[0]},
            )

        token_a = (await client.post("/api/v1/auth/login", json={"email": email1, "password": "SecureP@ss123!"})).json()["access_token"]
        token_b = (await client.post("/api/v1/auth/login", json={"email": email2, "password": "SecureP@ss123!"})).json()["access_token"]

        resp_a = await client.get("/api/v1/audit/events", headers={"Authorization": f"Bearer {token_a}"})
        resp_b = await client.get("/api/v1/audit/events", headers={"Authorization": f"Bearer {token_b}"})

        assert resp_a.json()["meta"]["total"] > 0
        assert resp_b.json()["meta"]["total"] > 0

    async def test_audit_chain_status(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "audit-chain@example.com", "password": "SecureP@ss123!", "full_name": "Audit Chain"},
        )
        token = (await client.post(
            "/api/v1/auth/login",
            json={"email": "audit-chain@example.com", "password": "SecureP@ss123!"},
        )).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/audit/chain/status", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["chain_length"] >= 2
        assert data["last_event_hash"] != ""
