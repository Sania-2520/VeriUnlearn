from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.services.notifications import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    db: DbSession,
    user: CurrentUser,
    limit: int = Query(default=100, ge=1, le=500),
) -> dict:
    service = NotificationService(db)
    return {
        "notifications": await service.list(user["sub"], limit=limit),
        "unread": await service.unread_count(user["sub"]),
    }


@router.get("/unread-count")
async def unread_count(db: DbSession, user: CurrentUser) -> dict:
    return {"unread": await NotificationService(db).unread_count(user["sub"])}


@router.post("/{notification_id}/read")
async def mark_read(notification_id: str, db: DbSession, user: CurrentUser) -> dict:
    notification = await NotificationService(db).mark_read(notification_id, user["sub"])
    return {"id": notification.id, "is_read": notification.is_read}


@router.post("/read-all")
async def mark_all_read(db: DbSession, user: CurrentUser) -> dict:
    count = await NotificationService(db).mark_all_read(user["sub"])
    return {"marked": count}
