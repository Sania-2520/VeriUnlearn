from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy import select

from app.core.dependencies import DatabaseDep, CurrentUser
from app.core.rbac import Permission, check_permission
from app.models.user import User
from app.schemas.auth import UserResponse
from app.services.audit_service import AuditService


class AuditLogEntry(BaseModel):
    id: int
    event_type: str
    event_data: dict
    user_id: int | None
    ip_address: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogResponse(BaseModel):
    entries: list[AuditLogEntry]
    total: int


router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=list[UserResponse])
async def list_users(user: CurrentUser, db: DatabaseDep):
    check_permission(user, Permission.USER_READ)
    result = await db.execute(select(User).order_by(User.id))
    return list(result.scalars().all())


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, user: CurrentUser, db: DatabaseDep):
    check_permission(user, Permission.USER_READ)
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return target


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(user_id: int, role: str, user: CurrentUser, db: DatabaseDep):
    check_permission(user, Permission.USER_WRITE)
    valid_roles = {"admin", "user", "auditor"}
    if role not in valid_roles:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid role: {role}")
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    old_role = target.role
    target.role = role
    await db.flush()
    await db.refresh(target)

    audit = AuditService(db)
    audit.log(user.id, "admin:user_role_changed", {
        "target_user_id": user_id,
        "target_username": target.username,
        "old_role": old_role,
        "new_role": role,
        "changed_by": user.username,
    })
    return target


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, user: CurrentUser, db: DatabaseDep):
    check_permission(user, Permission.USER_DELETE)
    if user_id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself")
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    audit = AuditService(db)
    audit.log(user.id, "admin:user_deleted", {
        "target_user_id": user_id,
        "target_username": target.username,
        "deleted_by": user.username,
    })

    await db.delete(target)
    await db.flush()


@router.get("/audit-log", response_model=AuditLogResponse)
async def get_audit_log(
    user: CurrentUser,
    db: DatabaseDep,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    event_type: str | None = Query(None),
    target_user_id: int | None = Query(None),
):
    check_permission(user, Permission.AUDIT_LOG)
    audit = AuditService(db)
    entries = await audit.get_logs(limit=limit, offset=offset, event_type=event_type, user_id=target_user_id)
    total = await audit.count_logs(event_type=event_type, user_id=target_user_id)
    return AuditLogResponse(entries=entries, total=total)
