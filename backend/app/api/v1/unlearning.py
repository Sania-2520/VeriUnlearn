from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DbSession
from app.api.serializers import deletion_request_out
from app.core.exceptions import ValidationFailedError
from app.db.models import DeletionRequest
from app.repositories.deletion_repo import DeletionRepository
from app.repositories.privacy_repo import DeletionHistoryRepository
from app.schemas.unlearning import (
    DeletionHistoryOut,
    DeletionRequestOut,
    IdentityResetRequest,
    ImpactRequest,
    SelectiveDeletionRequest,
)
from app.services.audit import AuditService
from app.services.chat_deletion import ChatDeletionService
from app.services.unlearning import UnlearningService
from app.workers.tasks import dispatch_unlearning, task_status

router = APIRouter(prefix="/unlearning", tags=["unlearning"])

_VALID_METHODS = {"retrain", "certified", "influence"}


class ChatDeletionRequest(BaseModel):
    mode: str = Field(..., description="'full' deletes the whole chat; 'sensitive' only scrubs PII")


@router.post("/impact")
async def impact_analysis(payload: ImpactRequest, db: DbSession, user: CurrentUser) -> dict:
    """Phase 4 STEP 2 — impact report before any deletion."""
    if payload.scope not in {"records", "chat", "dataset"}:
        raise ValidationFailedError("scope must be records | chat | dataset")
    report = await UnlearningService(db).analyze_impact(
        identity_key=payload.identity_key,
        record_ids=payload.record_ids,
        chat_id=payload.chat_id,
        dataset_id=payload.dataset_id,
        scope=payload.scope,
    )
    return report


@router.get("/history", response_model=list[DeletionHistoryOut])
async def deletion_history(db: DbSession, user: CurrentUser, limit: int = 50) -> list[DeletionHistoryOut]:
    """Phase 4 STEP 7 — persisted deletion reports."""
    reports = await DeletionHistoryRepository(db).list_reports(limit=limit)
    return [
        DeletionHistoryOut(
            id=r.id,
            request_id=r.request_id,
            scope=r.scope,
            subject=r.subject,
            method=r.method,
            status=r.status,
            record_count=r.record_count,
            shard_ids=r.shard_ids,
            duration_seconds=r.duration_seconds,
            model_id=r.model_id,
            model_version=r.model_version,
            dataset_id=r.dataset_id,
            dataset_version=r.dataset_version,
            records_before=r.records_before,
            records_after=r.records_after,
            embeddings_before=r.embeddings_before,
            embeddings_after=r.embeddings_after,
            vectors_removed=r.vectors_removed,
            certified_bound=r.certified_bound,
            certificate_id=r.certificate_id,
            before=r.before,
            after=r.after,
            created_at=r.created_at,
        )
        for r in reports
    ]


@router.post("/selective", response_model=DeletionRequestOut, status_code=202)
async def selective_unlearning(
    payload: SelectiveDeletionRequest, db: DbSession, user: CurrentUser
) -> DeletionRequestOut:
    """Selective surgical unlearning: single record / multiple / chat / user / dataset."""
    if payload.method not in _VALID_METHODS:
        raise ValidationFailedError(f"method must be one of {sorted(_VALID_METHODS)}")
    if payload.scope not in {"records", "chat", "dataset"}:
        raise ValidationFailedError("scope must be records | chat | dataset")
    if not payload.identity_key and not payload.record_ids and not payload.chat_id and not payload.dataset_id:
        raise ValidationFailedError("Provide identity_key, record_ids, chat_id (scope=chat) or dataset_id (scope=dataset)")
    if payload.method == "certified" and payload.record_ids and len(payload.record_ids) > 200:
        raise ValidationFailedError("certified method supports up to 200 records per call")

    service = UnlearningService(db)
    records = await service.resolve_records(
        identity_key=payload.identity_key,
        record_ids=payload.record_ids,
        chat_id=payload.chat_id,
        dataset_id=payload.dataset_id,
        scope=payload.scope,
    )
    request = DeletionRequest(
        identity_key=payload.identity_key,
        subject_label=(
            payload.identity_key
            or (f"chat:{payload.chat_id}" if payload.chat_id else None)
            or (f"dataset:{payload.dataset_id}" if payload.dataset_id else None)
            or f"{len(payload.record_ids or [])} records"
        ),
        deletion_type=payload.deletion_type,
        method=payload.method,
        scope={"source": "selective", "scope": payload.scope, "chat_id": payload.chat_id, "dataset_id": payload.dataset_id},
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


@router.post("/chats/{chat_session_id}/delete")
async def delete_chat_session(
    chat_session_id: str,
    payload: ChatDeletionRequest,
    db: DbSession,
    user: CurrentUser,
) -> dict:
    """Surgically delete a chat session — either the whole conversation
    (``mode=full``) or only the sensitive data inside it (``mode=sensitive``).

    Every deletion mints a signed certificate stored in Certificates and fed
    into the verification engine.
    """
    return await ChatDeletionService(db).delete(
        user_id=user["sub"],
        chat_session_id=chat_session_id,
        mode=payload.mode,
        actor=user["sub"],
    )


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
