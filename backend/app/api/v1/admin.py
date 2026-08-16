from __future__ import annotations

from fastapi import APIRouter, Body

from app.api.deps import AdminUser, DbSession
from app.api.serializers import user_out
from app.core.exceptions import ValidationFailedError
from app.repositories.user_repo import UserRepository
from app.services.audit import AuditService

router = APIRouter(prefix="/admin", tags=["admin"])

_VALID_ROLES = {"admin", "operator", "auditor"}


@router.get("/users")
async def list_users(db: DbSession, user: AdminUser) -> dict:
    users = await UserRepository(db).list(limit=500)
    return {"users": [user_out(u) for u in users]}


@router.patch("/users/{user_id}/role")
async def update_role(user_id: str, db: DbSession, user: AdminUser, role: str = Body(...)) -> dict:
    if role not in _VALID_ROLES:
        raise ValidationFailedError(f"role must be one of {sorted(_VALID_ROLES)}")
    repo = UserRepository(db)
    target = await repo.get(user_id)
    target.role = role
    await db.flush()
    await AuditService(db).log(
        event_type="admin.role_changed",
        actor=user["sub"],
        subject=user_id,
        payload={"role": role},
    )
    return {"user": user_out(target)}
