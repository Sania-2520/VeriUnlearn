from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from typing import Optional

from app.api.deps import CurrentUser, DatabaseSession, default_rate_limiter, require_permission
from app.core.rbac import Permission

router = APIRouter(dependencies=[Depends(default_rate_limiter), Depends(require_permission(Permission.ADMIN_READ))])


class UpdateUserRequest(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None


class CreateWebhookRequest(BaseModel):
    url: str
    events: list[str]
    secret: str


@router.get("/users")
async def list_users(
    current_user: CurrentUser,
    session: DatabaseSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
):
    return {"data": [], "meta": {"page": page, "page_size": page_size, "total": 0}}


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    return {"user": {}}


@router.get("/gpu-metrics")
async def get_gpu_metrics(current_user: CurrentUser):
    return {"gpus": []}


@router.get("/jobs")
async def list_jobs(
    current_user: CurrentUser,
    session: DatabaseSession,
    status: Optional[str] = None,
    job_type: Optional[str] = Query(None, alias="type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    return {"data": [], "meta": {"page": page, "page_size": page_size, "total": 0}}


@router.get("/analytics")
async def get_analytics(
    current_user: CurrentUser,
    session: DatabaseSession,
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    granularity: str = "day",
):
    return {
        "metrics": {},
        "over_time": [],
    }


@router.post("/webhooks", status_code=status.HTTP_201_CREATED)
async def create_webhook(
    request: CreateWebhookRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    return {"webhook": {}}


@router.get("/webhooks")
async def list_webhooks(
    current_user: CurrentUser,
    session: DatabaseSession,
):
    return {"data": []}
