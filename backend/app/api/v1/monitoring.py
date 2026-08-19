from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DbSession, require_permission
from app.services.monitoring import MonitoringService

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

MonitoringUser = Annotated[dict, Depends(require_permission("monitoring:read"))]


@router.get("/system")
async def system_snapshot(db: DbSession, user: MonitoringUser) -> dict:
    """Live system snapshot + persisted history (CPU/RAM/disk, dependencies,
    queue, API latency/error rate, uptime)."""
    service = MonitoringService(db)
    snapshot = await service.snapshot(persist=True)
    history = await service.history(limit=200)
    return {"snapshot": snapshot, "history": history}
