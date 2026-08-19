from __future__ import annotations

from fastapi import APIRouter, Body

from app.api.deps import AdminUser, DbSession
from app.api.serializers import user_out
from app.services.admin import AdminService
from app.services.audit import AuditService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
async def list_users(db: DbSession, user: AdminUser) -> dict:
    return {"users": await AdminService(db).list_users()}


@router.post("/users")
async def create_user(
    db: DbSession,
    user: AdminUser,
    email: str = Body(...),
    full_name: str = Body(...),
    password: str = Body(..., min_length=8),
    role: str = Body(default="viewer"),
) -> dict:
    created = await AdminService(db).create_user(email=email, full_name=full_name, password=password, role=role)
    await AuditService(db).log(
        event_type="admin.user_created",
        actor=user["sub"],
        subject=created.id,
        payload={"email": created.email, "role": created.role},
    )
    return {"user": user_out(created)}


@router.patch("/users/{user_id}/role")
async def update_role(user_id: str, db: DbSession, user: AdminUser, role: str = Body(...)) -> dict:
    target = await AdminService(db).set_role(user_id, role)
    await AuditService(db).log(
        event_type="admin.role_changed",
        actor=user["sub"],
        subject=user_id,
        payload={"role": role},
    )
    return {"user": user_out(target)}


@router.patch("/users/{user_id}/active")
async def set_active(user_id: str, db: DbSession, user: AdminUser, is_active: bool = Body(...)) -> dict:
    target = await AdminService(db).set_active(user_id, is_active)
    await AuditService(db).log(
        event_type="admin.user_activated" if is_active else "admin.user_deactivated",
        actor=user["sub"],
        subject=user_id,
    )
    return {"user": user_out(target)}


@router.get("/roles")
async def rbac_matrix(db: DbSession, user: AdminUser) -> dict:
    """Role/permission matrix (Phase 7 RBAC)."""
    return await AdminService(db).rbac_matrix()


@router.get("/deployments")
async def deployment_history(db: DbSession, user: AdminUser) -> dict:
    return {"deployments": await AdminService(db).deployment_history()}


@router.post("/deployments")
async def record_deployment(
    db: DbSession,
    user: AdminUser,
    version: str = Body(...),
    environment: str = Body(default="staging"),
    status: str = Body(default="pending"),
    commit_sha: str | None = Body(default=None),
    artifact: str | None = Body(default=None),
) -> dict:
    entry = await AdminService(db).record_deployment(
        version=version,
        environment=environment,
        status=status,
        commit_sha=commit_sha,
        artifact=artifact,
        deployed_by=user["sub"],
    )
    return {
        "deployment": {
            "id": entry.id,
            "version": entry.version,
            "environment": entry.environment,
            "status": entry.status,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
        }
    }


@router.get("/overview")
async def admin_overview(db: DbSession, user: AdminUser) -> dict:
    return await AdminService(db).overview()
