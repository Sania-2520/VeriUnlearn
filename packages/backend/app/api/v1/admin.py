import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func, desc

from app.api.deps import CurrentUser, DatabaseSession, default_rate_limiter, require_permission
from app.core.logging import get_logger
from app.core.rbac import Permission
from app.domain.compliance.entities import Webhook as WebhookEntity, WebhookStatus
from app.infrastructure.database.models import UserModel, UnlearningJobModel, WebhookModel
from app.infrastructure.database.repositories.compliance import SQLAlchemyWebhookRepository
from app.infrastructure.external.ml_engine import ml_engine_client, MLEngineClientError

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(default_rate_limiter), Depends(require_permission(Permission.ADMIN_READ))])


class UpdateUserRequest(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None


class CreateWebhookRequest(BaseModel):
    url: str
    events: list[str]
    secret: str
    name: str = "Default"


@router.get("/users")
async def list_users(
    current_user: CurrentUser,
    session: DatabaseSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
):
    tenant_uuid = uuid.UUID(current_user["tenant_id"])
    query = select(UserModel).where(UserModel.tenant_id == tenant_uuid)
    count_query = select(func.count(UserModel.id)).where(UserModel.tenant_id == tenant_uuid)
    if role:
        query = query.where(UserModel.role == role)
        count_query = count_query.where(UserModel.role == role)
    if is_active is not None:
        query = query.where(UserModel.is_active == is_active)
        count_query = count_query.where(UserModel.is_active == is_active)
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    query = query.order_by(desc(UserModel.created_at)).offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    users = result.scalars().all()
    return {
        "data": [
            {
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "is_active": u.is_active,
                "is_email_verified": u.is_email_verified,
                "mfa_enabled": u.mfa_enabled,
                "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        "meta": {"page": page, "page_size": page_size, "total": total},
    }


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    from sqlalchemy import update as sa_update
    tenant_uuid = uuid.UUID(current_user["tenant_id"])
    user_uuid = uuid.UUID(user_id)
    values = {}
    if request.role is not None:
        values["role"] = request.role
    if request.is_active is not None:
        values["is_active"] = request.is_active
    if not values:
        raise HTTPException(status_code=400, detail="No fields to update")
    values["updated_at"] = datetime.now(timezone.utc)
    await session.execute(
        sa_update(UserModel)
        .where(UserModel.id == user_uuid, UserModel.tenant_id == tenant_uuid)
        .values(**values)
    )
    await session.commit()
    result = await session.execute(
        select(UserModel).where(UserModel.id == user_uuid, UserModel.tenant_id == tenant_uuid)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
        }
    }


@router.get("/gpu-metrics")
async def get_gpu_metrics(current_user: CurrentUser):
    try:
        ml_result = await ml_engine_client.get_controller_health()
        return {"gpus": [{"status": "connected", "metrics": ml_result}]}
    except (MLEngineClientError, AttributeError) as e:
        logger.error("Failed to fetch GPU metrics: %s", str(e))
        return {"gpus": [], "error": str(e)}


@router.get("/jobs")
async def list_jobs(
    current_user: CurrentUser,
    session: DatabaseSession,
    status: Optional[str] = None,
    job_type: Optional[str] = Query(None, alias="type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    query = select(UnlearningJobModel)
    count_query = select(func.count(UnlearningJobModel.id))
    if status:
        query = query.where(UnlearningJobModel.status == status)
        count_query = count_query.where(UnlearningJobModel.status == status)
    if job_type:
        query = query.where(UnlearningJobModel.algorithm == job_type)
        count_query = count_query.where(UnlearningJobModel.algorithm == job_type)
    query = query.order_by(desc(UnlearningJobModel.created_at)).offset((page - 1) * page_size).limit(page_size)
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    result = await session.execute(query)
    jobs = result.scalars().all()
    return {
        "data": [
            {
                "id": j.id,
                "algorithm": j.algorithm,
                "status": j.status,
                "progress": j.progress,
                "started_at": j.started_at.isoformat() if j.started_at else None,
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
                "processing_time_ms": j.processing_time_ms,
                "error_message": j.error_message,
                "created_at": j.created_at.isoformat() if j.created_at else None,
            }
            for j in jobs
        ],
        "meta": {"page": page, "page_size": page_size, "total": total},
    }


@router.get("/analytics")
async def get_analytics(
    current_user: CurrentUser,
    session: DatabaseSession,
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    granularity: str = "day",
):
    tenant_uuid = uuid.UUID(current_user["tenant_id"])
    total_users_result = await session.execute(
        select(func.count(UserModel.id)).where(UserModel.tenant_id == tenant_uuid)
    )
    total_users = total_users_result.scalar() or 0
    active_users_result = await session.execute(
        select(func.count(UserModel.id)).where(
            UserModel.tenant_id == tenant_uuid, UserModel.is_active == True
        )
    )
    active_users = active_users_result.scalar() or 0
    total_jobs_result = await session.execute(select(func.count(UnlearningJobModel.id)))
    total_jobs = total_jobs_result.scalar() or 0
    return {
        "metrics": {
            "total_users": total_users,
            "active_users": active_users,
            "total_jobs": total_jobs,
            "granularity": granularity,
        },
        "over_time": [],
    }


@router.post("/webhooks", status_code=status.HTTP_201_CREATED)
async def create_webhook(
    request: CreateWebhookRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    from uuid import uuid4
    webhook_repo = SQLAlchemyWebhookRepository(session)
    webhook = WebhookEntity(
        id=str(uuid4()),
        tenant_id=current_user["tenant_id"],
        name=request.name,
        url=request.url,
        secret=request.secret,
        events=request.events,
        is_active=True,
        status=WebhookStatus.ACTIVE,
        headers={},
        retry_count=3,
        timeout_ms=5000,
    )
    created = await webhook_repo.create(webhook)
    await session.commit()
    return {
        "webhook": {
            "id": created.id,
            "name": created.name,
            "url": created.url,
            "events": created.events,
            "is_active": created.is_active,
            "status": created.status.value if hasattr(created.status, "value") else created.status,
            "created_at": created.created_at.isoformat() if created.created_at else None,
        }
    }


@router.get("/webhooks")
async def list_webhooks(
    current_user: CurrentUser,
    session: DatabaseSession,
):
    webhook_repo = SQLAlchemyWebhookRepository(session)
    webhooks = await webhook_repo.list_by_tenant(current_user["tenant_id"])
    return {
        "data": [
            {
                "id": w.id,
                "name": w.name,
                "url": w.url,
                "events": w.events,
                "is_active": w.is_active,
                "status": w.status.value if hasattr(w.status, "value") else w.status,
                "created_at": w.created_at.isoformat() if w.created_at else None,
                "updated_at": w.updated_at.isoformat() if w.updated_at else None,
            }
            for w in webhooks
        ]
    }
