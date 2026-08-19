"""Phase 7 tests — RBAC, API keys, notifications, monitoring, analytics,
compliance reports, and security hardening."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.rbac import ROLE_PERMISSIONS, has_permission, role_permissions
from app.main import app
from app.services.admin import AdminService
from app.services.analytics import AnalyticsService
from app.services.api_keys import APIKeyService
from app.services.compliance import ComplianceService
from app.services.monitoring import MonitoringService
from app.services.notifications import NotificationService

# ------------------------------------------------------------------ RBAC


def test_role_matrix_complete():
    assert set(ROLE_PERMISSIONS) == {"admin", "researcher", "auditor", "operator", "viewer"}
    # Privilege monotonicity: admin grants everything anyone else has.
    admin_perms = set(role_permissions("admin"))
    for role in ROLE_PERMISSIONS:
        assert set(role_permissions(role)) <= admin_perms


def test_has_permission():
    assert has_permission("admin", "users:manage")
    assert has_permission("operator", "unlearning:execute")
    assert not has_permission("viewer", "unlearning:execute")
    assert not has_permission("researcher", "api_keys:manage")
    # Legacy roles map onto the matrix.
    assert has_permission("operator", "datasets:manage")


@pytest.mark.asyncio
async def test_rbac_matrix_endpoint(db_session):
    from app.api.deps import require_permission

    ok = require_permission("unlearning:execute")({"sub": "u1", "role": "operator"})
    assert ok["role"] == "operator"
    with pytest.raises(ForbiddenError):
        require_permission("unlearning:execute")({"sub": "u1", "role": "viewer"})


# ----------------------------------------------------------------- API keys


@pytest.mark.asyncio
async def test_api_key_issue_authenticate_revoke(db_session):
    service = APIKeyService(db_session)
    issued = await service.issue(user_id="user-1", name="ci-key", quota_per_minute=5)
    assert issued["key"].startswith("vk_")
    assert "key_hash" not in issued  # never expose the hash

    key = await service.authenticate(issued["key"])
    assert key.id == issued["id"]
    assert key.requests_count == 1
    assert key.usage[-1]["path"] is None  # path filled by middleware after response

    await service.revoke(issued["id"])
    with pytest.raises(UnauthorizedError):
        await service.authenticate(issued["key"])


@pytest.mark.asyncio
async def test_api_key_quota_enforced(db_session):
    service = APIKeyService(db_session)
    issued = await service.issue(user_id="user-1", name="quota-key", quota_per_minute=3)
    for _ in range(3):
        await service.authenticate(issued["key"])
    with pytest.raises(UnauthorizedError):
        await service.authenticate(issued["key"])


@pytest.mark.asyncio
async def test_api_key_middleware(db_session, session_factory):
    from app.core import middleware as middleware_module

    user = await AdminService(db_session).create_user(
        email="apikey-user@test.dev", full_name="Key User", password="password123", role="viewer"
    )
    service = APIKeyService(db_session)
    issued = await service.issue(user_id=user.id, name="http-key", quota_per_minute=10)
    await db_session.commit()

    from app.db.session import get_db

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    original_factory = middleware_module.session_factory
    middleware_module.session_factory = session_factory  # point middleware at test DB
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Missing key → bearer dependency rejects (route requires auth).
            resp = await client.get("/api/v1/notifications")
            assert resp.status_code == 401
            # Bogus key → middleware rejects.
            resp = await client.get("/api/v1/notifications", headers={"X-API-Key": "vk_bogus"})
            assert resp.status_code == 401
            # Valid key → authenticated as the owning viewer, route executes.
            resp = await client.get("/api/v1/notifications", headers={"X-API-Key": issued["key"]})
            assert resp.status_code == 200
    finally:
        middleware_module.session_factory = original_factory
        app.dependency_overrides.clear()


# ------------------------------------------------------------ notifications


@pytest.mark.asyncio
async def test_notification_lifecycle(db_session):
    service = NotificationService(db_session)
    n = await service.notify(
        user_id="user-1",
        event_type="deletion.completed",
        title="Deletion finished",
        body="Request completed",
        payload={"request_id": "r1"},
    )
    assert n.id is not None
    unread = await service.unread_count("user-1")
    assert unread == 1

    items = await service.list("user-1")
    assert items[0]["title"] == "Deletion finished"
    assert items[0]["is_read"] is False

    await service.mark_read(n.id, "user-1")
    assert await service.unread_count("user-1") == 0

    # Email channel: null provider delivers immediately (no-op).
    email = await service.notify(
        user_id="user-1", event_type="experiment.finished", title="Run done", channels=["email"]
    )
    assert email.delivered is True


@pytest.mark.asyncio
async def test_notification_email_retry_semantics(db_session):
    service = NotificationService(db_session)
    n = await service.notify(
        user_id="user-1",
        event_type="system.error",
        title="Something failed",
        body="detail",
        channels=["email"],
    )
    assert n.attempts >= 1
    assert n.delivered is True  # null provider succeeds


# --------------------------------------------------------------- monitoring


@pytest.mark.asyncio
async def test_monitoring_snapshot_and_persistence(db_session):
    service = MonitoringService(db_session)
    snapshot = await service.snapshot(persist=True)
    assert "system" in snapshot
    assert "dependencies" in snapshot
    assert snapshot["dependencies"]["database"]["healthy"] is True
    assert "queue" in snapshot
    assert "api" in snapshot
    assert snapshot["api"]["uptime_seconds"] > 0

    history = await service.history(kind="system")
    assert history, "system metrics should be persisted"
    names = {h["name"] for h in history}
    assert "cpu_percent" in names


# ---------------------------------------------------------------- analytics


@pytest.mark.asyncio
async def test_analytics_overview_and_export(db_session):
    service = AnalyticsService(db_session)
    overview = await service.overview()
    assert "deletion_requests" in overview
    trends = await service.deletion_trends(30)
    assert "series" in trends
    csv_out = service.export_csv(trends["series"], ["day", "total", "completed", "failed"])
    assert csv_out.startswith("day")


# ----------------------------------------------------- compliance reports


@pytest.mark.asyncio
async def test_compliance_report_persisted(db_session):
    service = ComplianceService(db_session)
    report = await service.run_report(created_by="tester")
    assert report.gdpr_score >= 0
    assert report.id is not None
    history = await service.history()
    assert any(r["id"] == report.id for r in history)


# ------------------------------------------------------------ admin service


@pytest.mark.asyncio
async def test_admin_create_user_and_rbac_matrix(db_session):
    service = AdminService(db_session)
    user = await service.create_user(
        email="auditor2@test.dev", full_name="A2", password="password123", role="auditor"
    )
    assert user.role == "auditor"
    matrix = await service.rbac_matrix()
    assert set(matrix["roles"]) == {"admin", "researcher", "auditor", "operator", "viewer"}
    assert "unlearning:execute" in matrix["permissions"]


# -------------------------------------------------------------- security


@pytest.mark.asyncio
async def test_security_headers_present():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.headers.get("x-content-type-options") == "nosniff"
        assert resp.headers.get("x-frame-options") == "DENY"
        assert resp.headers.get("referrer-policy") == "no-referrer"


@pytest.mark.asyncio
async def test_cross_origin_blocked():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "a@b.c", "password": "x"},
            headers={"Origin": "https://evil.example"},
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_prometheus_metrics_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/metrics")
        assert resp.status_code == 200
        assert "veriunlearn_http_requests_total" in resp.text
