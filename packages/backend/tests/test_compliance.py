import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


TEST_EMAIL = "compliance-test@example.com"
TEST_PASSWORD = "SecureP@ss123!"


async def _register_and_login(client: AsyncClient, email: str = TEST_EMAIL) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": TEST_PASSWORD, "full_name": "Compliance Test"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": TEST_PASSWORD},
    )
    return resp.json()["access_token"]


async def _register_and_upgrade(client: AsyncClient, email: str) -> str:
    from app.core.database import db
    from sqlalchemy import update
    from app.infrastructure.database.models import UserModel

    await _register_and_login(client, email)
    async with db.session_factory() as session:
        await session.execute(
            update(UserModel).where(UserModel.email == email).values(role="admin")
        )
        await session.commit()
    token = (await client.post("/api/v1/auth/login", json={"email": email, "password": TEST_PASSWORD})).json()["access_token"]
    return token


class TestSettingsAPI:
    async def test_get_default_settings(self, client: AsyncClient):
        token = await _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/compliance/settings", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["timezone"] == "UTC"
        assert data["data_retention_days"] == 365
        assert data["mfa_enforced"] is False

    async def test_update_settings(self, client: AsyncClient):
        token = await _register_and_upgrade(client, "settings-update@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.put(
            "/api/v1/compliance/settings",
            json={"timezone": "America/New_York", "mfa_enforced": True},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "updated"

        resp = await client.get("/api/v1/compliance/settings", headers=headers)
        data = resp.json()
        assert data["timezone"] == "America/New_York"
        assert data["mfa_enforced"] is True

    async def test_update_settings_unauthorized(self, client: AsyncClient):
        resp = await client.put(
            "/api/v1/compliance/settings",
            json={"timezone": "UTC"},
        )
        assert resp.status_code == 401

    async def test_member_can_read_settings(self, client: AsyncClient):
        token = await _register_and_login(client, "member-settings@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/compliance/settings", headers=headers)
        assert resp.status_code == 200

    async def test_member_cannot_write_settings(self, client: AsyncClient):
        token = await _register_and_login(client, "member-write@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.put("/api/v1/compliance/settings", json={"timezone": "UTC"}, headers=headers)
        assert resp.status_code == 403


class TestWebhookAPI:
    async def test_create_webhook(self, client: AsyncClient):
        token = await _register_and_upgrade(client, "wh-create@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/api/v1/compliance/webhooks",
            params={
                "name": "Test Webhook",
                "url": "https://example.com/webhook",
                "events": ["unlearning.completed", "proof.generated"],
                "retry_count": 3,
                "timeout_ms": 5000,
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test Webhook"
        assert data["url"] == "https://example.com/webhook"
        assert "unlearning.completed" in data["events"]
        assert data["status"] == "active"

    async def test_list_webhooks(self, client: AsyncClient):
        token = await _register_and_upgrade(client, "wh-list@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        await client.post(
            "/api/v1/compliance/webhooks",
            params={"name": "WH1", "url": "https://example.com/wh1", "events": ["unlearning.completed"]},
            headers=headers,
        )
        await client.post(
            "/api/v1/compliance/webhooks",
            params={"name": "WH2", "url": "https://example.com/wh2", "events": ["proof.generated"]},
            headers=headers,
        )

        resp = await client.get("/api/v1/compliance/webhooks", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) >= 2
        names = [w["name"] for w in data["data"]]
        assert "WH1" in names
        assert "WH2" in names

    async def test_get_webhook(self, client: AsyncClient):
        token = await _register_and_upgrade(client, "wh-get@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post(
            "/api/v1/compliance/webhooks",
            params={"name": "GetTest", "url": "https://example.com/get", "events": ["unlearning.completed"]},
            headers=headers,
        )
        webhook_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/compliance/webhooks/{webhook_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "GetTest"

    async def test_get_webhook_not_found(self, client: AsyncClient):
        token = await _register_and_upgrade(client, "wh-notfound@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/compliance/webhooks/non-existent", headers=headers)
        assert resp.status_code == 404

    async def test_update_webhook(self, client: AsyncClient):
        token = await _register_and_upgrade(client, "wh-update@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post(
            "/api/v1/compliance/webhooks",
            params={"name": "UpdateTest", "url": "https://example.com/old", "events": ["unlearning.completed"]},
            headers=headers,
        )
        webhook_id = create_resp.json()["id"]

        resp = await client.put(
            f"/api/v1/compliance/webhooks/{webhook_id}",
            params={"name": "Updated", "url": "https://example.com/new", "is_active": False},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"
        assert resp.json()["is_active"] is False

    async def test_delete_webhook(self, client: AsyncClient):
        token = await _register_and_upgrade(client, "wh-delete@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post(
            "/api/v1/compliance/webhooks",
            params={"name": "DeleteTest", "url": "https://example.com/del", "events": ["unlearning.completed"]},
            headers=headers,
        )
        webhook_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/v1/compliance/webhooks/{webhook_id}", headers=headers)
        assert resp.status_code == 204

        resp = await client.get(f"/api/v1/compliance/webhooks/{webhook_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False
        assert resp.json()["status"] == "disabled"

    async def test_test_webhook(self, client: AsyncClient):
        token = await _register_and_upgrade(client, "wh-test@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post(
            "/api/v1/compliance/webhooks",
            params={"name": "TestHook", "url": "https://example.com/test", "events": ["unlearning.completed"]},
            headers=headers,
        )
        webhook_id = create_resp.json()["id"]

        resp = await client.post(
            f"/api/v1/compliance/webhooks/{webhook_id}/test",
            headers=headers,
        )
        assert resp.status_code == 200
        result = resp.json()
        assert "status_code" in result
        assert "success" in result

    async def test_webhook_logs_empty(self, client: AsyncClient):
        token = await _register_and_upgrade(client, "wh-logs@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post(
            "/api/v1/compliance/webhooks",
            params={"name": "LogTest", "url": "https://example.com/log", "events": ["unlearning.completed"]},
            headers=headers,
        )
        webhook_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/compliance/webhooks/{webhook_id}/logs", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["meta"]["total"] == 0
        assert data["data"] == []

    async def test_create_webhook_unauthorized(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/compliance/webhooks",
            params={"name": "Test", "url": "https://example.com/t", "events": ["unlearning.completed"]},
        )
        assert resp.status_code == 401


class TestWebhookServiceDirect:
    async def test_dispatch_event(self, client: AsyncClient):
        from app.core.database import db
        from app.domain.compliance.services import TenantService
        from app.domain.audit.services import AuditService
        from app.infrastructure.database.repositories.compliance import (
            SQLAlchemyWebhookRepository,
            SQLAlchemyWebhookEventLogRepository,
        )
        from app.infrastructure.database.repositories.auth import SQLAlchemyTenantRepository
        from app.infrastructure.database.repositories.audit import SQLAlchemyAuditEventRepository

        async with db.session_factory() as session:
            audit_repo = SQLAlchemyAuditEventRepository(session)
            audit_svc = AuditService(repo=audit_repo)
            svc = TenantService(
                tenant_repo=SQLAlchemyTenantRepository(session),
                webhook_repo=SQLAlchemyWebhookRepository(session),
                webhook_log_repo=SQLAlchemyWebhookEventLogRepository(session),
                audit_service=audit_svc,
            )

            webhook = await svc.create_webhook(
                tenant_id="test-tenant",
                name="Dispatch Test",
                url="https://example.com/dispatch",
                events=["unlearning.completed"],
            )

            with patch.object(svc, "_send_webhook", AsyncMock(return_value=(200, "OK"))):
                logs = await svc.dispatch_event(
                    tenant_id="test-tenant",
                    event_type="unlearning.completed",
                    payload={"request_id": "req-1", "status": "completed"},
                )
                assert len(logs) == 1
                assert logs[0].status.value == "delivered"
                assert logs[0].response_code == 200

                retrieved = await svc.get_webhook("test-tenant", webhook.id)
                assert retrieved.last_success_at is not None
                assert retrieved.consecutive_failures == 0

    async def test_dispatch_event_no_matching_webhooks(self, client: AsyncClient):
        from app.core.database import db
        from app.domain.compliance.services import TenantService
        from app.domain.audit.services import AuditService
        from app.infrastructure.database.repositories.compliance import (
            SQLAlchemyWebhookRepository,
            SQLAlchemyWebhookEventLogRepository,
        )
        from app.infrastructure.database.repositories.auth import SQLAlchemyTenantRepository
        from app.infrastructure.database.repositories.audit import SQLAlchemyAuditEventRepository

        async with db.session_factory() as session:
            audit_repo = SQLAlchemyAuditEventRepository(session)
            audit_svc = AuditService(repo=audit_repo)
            svc = TenantService(
                tenant_repo=SQLAlchemyTenantRepository(session),
                webhook_repo=SQLAlchemyWebhookRepository(session),
                webhook_log_repo=SQLAlchemyWebhookEventLogRepository(session),
                audit_service=audit_svc,
            )

            logs = await svc.dispatch_event(
                tenant_id="test-tenant-empty",
                event_type="unlearning.completed",
                payload={"test": True},
            )
            assert logs == []

    async def test_dispatch_event_failure(self, client: AsyncClient):
        from app.core.database import db
        from app.domain.compliance.services import TenantService
        from app.domain.audit.services import AuditService
        from app.infrastructure.database.repositories.compliance import (
            SQLAlchemyWebhookRepository,
            SQLAlchemyWebhookEventLogRepository,
        )
        from app.infrastructure.database.repositories.auth import SQLAlchemyTenantRepository
        from app.infrastructure.database.repositories.audit import SQLAlchemyAuditEventRepository

        async with db.session_factory() as session:
            audit_repo = SQLAlchemyAuditEventRepository(session)
            audit_svc = AuditService(repo=audit_repo)
            svc = TenantService(
                tenant_repo=SQLAlchemyTenantRepository(session),
                webhook_repo=SQLAlchemyWebhookRepository(session),
                webhook_log_repo=SQLAlchemyWebhookEventLogRepository(session),
                audit_service=audit_svc,
            )

            webhook = await svc.create_webhook(
                tenant_id="test-tenant-fail",
                name="Fail Test",
                url="https://example.com/fail",
                events=["unlearning.failed"],
            )

            with patch.object(svc, "_send_webhook", AsyncMock(return_value=(500, "Internal Server Error"))):
                logs = await svc.dispatch_event(
                    tenant_id="test-tenant-fail",
                    event_type="unlearning.failed",
                    payload={"error": "test failure"},
                )
                assert len(logs) == 1
                assert logs[0].status.value == "failed"
                assert logs[0].response_code == 500

    async def test_tenant_settings_persistence(self, client: AsyncClient):
        from app.core.database import db
        from app.domain.compliance.services import TenantService
        from app.domain.audit.services import AuditService
        from app.infrastructure.database.repositories.auth import SQLAlchemyTenantRepository
        from app.infrastructure.database.repositories.compliance import (
            SQLAlchemyWebhookRepository,
            SQLAlchemyWebhookEventLogRepository,
        )
        from app.infrastructure.database.repositories.audit import SQLAlchemyAuditEventRepository

        async with db.session_factory() as session:
            from app.domain.auth.entities import Tenant
            from app.domain.auth.interfaces import TenantRepository

            tenant_repo = SQLAlchemyTenantRepository(session)
            tenant = Tenant(name="Settings Test", slug="settings-test")
            tenant = await tenant_repo.create(tenant)

            audit_repo = SQLAlchemyAuditEventRepository(session)
            audit_svc = AuditService(repo=audit_repo)
            svc = TenantService(
                tenant_repo=tenant_repo,
                webhook_repo=SQLAlchemyWebhookRepository(session),
                webhook_log_repo=SQLAlchemyWebhookEventLogRepository(session),
                audit_service=audit_svc,
            )

            settings = await svc.get_settings(tenant.id)
            assert settings.timezone == "UTC"
            assert settings.mfa_enforced is False

            await svc.update_settings(
                tenant_id=tenant.id,
                settings_data={
                    "timezone": "Asia/Tokyo",
                    "mfa_enforced": True,
                    "data_retention_days": 90,
                },
            )

            updated = await svc.get_settings(tenant.id)
            assert updated.timezone == "Asia/Tokyo"
            assert updated.mfa_enforced is True
            assert updated.data_retention_days == 90

            tenant = await tenant_repo.get_by_id(tenant.id)
            assert tenant.settings["timezone"] == "Asia/Tokyo"
            assert tenant.settings["mfa_enforced"] is True
