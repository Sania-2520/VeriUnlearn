from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.api.serializers import deletion_request_out
from app.core.exceptions import ValidationFailedError
from app.db.models import DeletionRequest
from app.repositories.deletion_repo import DeletionRepository
from app.schemas.unlearning import (
    DeletionRequestOut,
    IdentityResetRequest,
    SelectiveDeletionRequest,
)
from app.services.audit import AuditService
from app.services.unlearning import UnlearningService
from app.workers.tasks import dispatch_unlearning, task_status

router = APIRouter(prefix="/unlearning", tags=["unlearning"])

_VALID_METHODS = {"retrain", "certified", "influence"}


@router.post("/selective", response_model=DeletionRequestOut, status_code=202)
async def selective_unlearning(
    payload: SelectiveDeletionRequest, db: DbSession, user: CurrentUser
) -> DeletionRequestOut:
    """Selective surgical unlearning: single record / embedding / chat / adapter."""
    if payload.method not in _VALID_METHODS:
        raise ValidationFailedError(f"method must be one of {sorted(_VALID_METHODS)}")
    if not payload.identity_key and not payload.record_ids:
        raise ValidationFailedError("Provide identity_key or record_ids")
    if payload.method == "certified" and payload.record_ids and len(payload.record_ids) > 200:
        raise ValidationFailedError("certified method supports up to 200 records per call")

    service = UnlearningService(db)
    records = await service.resolve_records(
        identity_key=payload.identity_key, record_ids=payload.record_ids
    )
    request = DeletionRequest(
        identity_key=payload.identity_key,
        subject_label=payload.identity_key or f"{len(payload.record_ids or [])} records",
        deletion_type=payload.deletion_type,
        method=payload.method,
        scope={"source": "selective"},
        record_ids=[r.id for r in records],
        requested_by=user["sub"],
    )
    request = await DeletionRepository(db).create(request)
    await AuditService(db).log(
        event_type="unlearning.requested",
        actor=user["sub"],
        subject=request.identity_key or request.subject_label,
        payload={"request_id": request.id, "type": payload.deletion_type, "method": payload.method, "records": len(records)},
    )
    await dispatch_unlearning(request.id)
    return DeletionRequestOut(**deletion_request_out(request))


@router.post("/full-reset", response_model=DeletionRequestOut, status_code=202)
async def full_identity_reset(
    payload: IdentityResetRequest, db: DbSession, user: CurrentUser
) -> DeletionRequestOut:
    """Complete identity reset: all records, embeddings, adapters, indexes."""
    service = UnlearningService(db)
    request = await service.full_identity_reset(
        identity_key=payload.identity_key, requested_by=user["sub"]
    )
    await dispatch_unlearning(request.id)
    return DeletionRequestOut(**deletion_request_out(request))


@router.get("/requests", response_model=list[DeletionRequestOut])
async def list_requests(db: DbSession, limit: int = Query(default=50, ge=1, le=500)) -> list[DeletionRequestOut]:
    requests = await DeletionRepository(db).list(limit=limit)
    return [DeletionRequestOut(**deletion_request_out(r)) for r in requests]


@router.get("/requests/{request_id}", response_model=DeletionRequestOut)
async def get_request(request_id: str, db: DbSession) -> DeletionRequestOut:
    request = await DeletionRepository(db).get(request_id)
    out = deletion_request_out(request)
    out["status"] = request.status if request.status in {"completed", "failed"} else (task_status(request_id) or request.status)
    return DeletionRequestOut(**out)
