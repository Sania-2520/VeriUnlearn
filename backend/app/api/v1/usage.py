from __future__ import annotations

from fastapi import APIRouter

from app.core.dependencies import DatabaseDep, CurrentUser
from app.services.usage_service import UsageQuota

router = APIRouter(prefix="/usage", tags=["Usage"])


@router.get("/me")
async def get_my_usage(user: CurrentUser, db: DatabaseDep):
    quota = UsageQuota(db)
    return await quota.get_usage(user.id)
