from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import (
    CurrentUser,
    DatabaseSession,
    TenantID,
    UnlearningServiceDep,
    default_rate_limiter,
    require_permission,
)
from app.core.logging import get_logger
from app.core.rbac import Permission
from app.core.rate_limiter import make_rate_limiter, parse_rate_limit
from app.core.config import settings
from app.domain.unlearning.entities import TargetType, UnlearningPriority, UnlearningAlgorithm
from app.infrastructure.external.ml_engine import ml_engine_client, MLEngineClientError
from app.workers.unlearning_tasks import dispatch_unlearning_workflow

logger = get_logger(__name__)

_unl_count, _unl_window = parse_rate_limit(settings.rate_limit_unlearning)
_unlearning_rl = make_rate_limiter(
    max_requests=_unl_count,
    window_seconds=_unl_window,
    group="unlearning",
)
router = APIRouter(dependencies=[Depends(_unlearning_rl)])


@router.post("/requests", status_code=status.HTTP_201_CREATED)
async def create_unlearning_request(
    target_type: str = Query(...),
    target_id: str = Query(...),
    reason: Optional[str] = None,
    gdpr_article: Optional[str] = None,
    priority: str = "normal",
    algorithm: str = "hybrid",
    current_user: Annotated[dict, Depends(require_permission(Permission.UNLEARNING_CREATE))] = ...,
    unlearning_service: UnlearningServiceDep = ...,
    tenant_id: TenantID = ...,
):
    try:
        target_type_enum = TargetType(target_type)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid target_type: {target_type}")
    try:
        priority_enum = UnlearningPriority(priority)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid priority: {priority}")
    try:
        algorithm_enum = UnlearningAlgorithm(algorithm)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid algorithm: {algorithm}")

    result, job = await unlearning_service.create_request(
        tenant_id=tenant_id,
        requested_by=current_user["user_id"],
        target_type=target_type_enum,
        target_id=target_id,
        reason=reason,
        gdpr_article=gdpr_article,
        priority=priority_enum,
        algorithm=algorithm_enum,
    )

    workflow = dispatch_unlearning_workflow(request_id=str(result.id))

    return {
        "request_id": result.id,
        "status": result.status.value,
        "job_id": job.id if job else None,
        "workflow": workflow.get("workflow"),
    }


@router.get("/requests/{request_id}")
async def get_unlearning_request(
    request_id: str,
    current_user: Annotated[dict, Depends(require_permission(Permission.UNLEARNING_READ))],
    unlearning_service: UnlearningServiceDep = ...,
    tenant_id: TenantID = ...,
):
    request = await unlearning_service.get_request(tenant_id, request_id)
    return {
        "id": request.id,
        "tenant_id": request.tenant_id,
        "requested_by": request.requested_by,
        "target_type": request.target_type.value,
        "target_id": request.target_id,
        "reason": request.reason,
        "gdpr_article": request.gdpr_article,
        "status": request.status.value,
        "priority": request.priority.value,
        "created_at": request.created_at.isoformat() if request.created_at else None,
        "updated_at": request.updated_at.isoformat() if request.updated_at else None,
    }


@router.get("/requests")
async def list_unlearning_requests(
    current_user: Annotated[dict, Depends(require_permission(Permission.UNLEARNING_READ))],
    unlearning_service: UnlearningServiceDep = ...,
    tenant_id: TenantID = ...,
    status_filter: Optional[str] = Query(None, alias="status"),
    target_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    results, total = await unlearning_service.list_requests(
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        status=status_filter,
        target_type=target_type,
    )
    return {
        "data": [
            {
                "id": r.id,
                "target_type": r.target_type.value,
                "target_id": r.target_id,
                "status": r.status.value,
                "priority": r.priority.value,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in results
        ],
        "meta": {"page": page, "page_size": page_size, "total": total},
    }


@router.post("/requests/{request_id}/retry", status_code=status.HTTP_202_ACCEPTED)
async def retry_unlearning_request(
    request_id: str,
    current_user: Annotated[dict, Depends(require_permission(Permission.UNLEARNING_RETRY))],
    unlearning_service: UnlearningServiceDep = ...,
    tenant_id: TenantID = ...,
):
    job = await unlearning_service.retry_request(
        tenant_id=tenant_id,
        request_id=request_id,
        requested_by=current_user["user_id"],
    )
    return {"message": "Retry initiated", "job_id": job.id}


@router.get("/queue")
async def get_queue_status(
    current_user: Annotated[dict, Depends(require_permission(Permission.UNLEARNING_READ))],
    unlearning_service: UnlearningServiceDep = ...,
    tenant_id: TenantID = ...,
):
    try:
        controller_health = await ml_engine_client.get_controller_health()
    except MLEngineClientError:
        controller_health = {"status": "unknown"}
    return {
        "queue": await unlearning_service.get_queue_status(tenant_id),
        "controller": controller_health,
    }


@router.post("/model-versions", status_code=status.HTTP_201_CREATED)
async def create_model_version(
    name: str = Query(...),
    algorithm: Optional[str] = None,
    shard_count: int = Query(1, ge=1),
    config: Optional[dict] = None,
    current_user: Annotated[dict, Depends(require_permission(Permission.UNLEARNING_CREATE))] = ...,
    unlearning_service: UnlearningServiceDep = ...,
    tenant_id: TenantID = ...,
):
    version = await unlearning_service.create_model_version(
        tenant_id=tenant_id,
        name=name,
        algorithm=algorithm,
        config=config,
        shard_count=shard_count,
    )
    return {
        "id": version.id,
        "name": version.name,
        "version": version.version,
        "parent_version_id": version.parent_version_id,
        "algorithm": version.algorithm,
        "status": version.status,
        "created_at": version.created_at.isoformat() if version.created_at else None,
    }
