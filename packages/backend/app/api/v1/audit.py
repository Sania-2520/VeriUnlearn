from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Any, Optional

from app.api.deps import CurrentUser, DatabaseSession, AuditServiceDep, default_rate_limiter, require_permission
from app.core.rbac import Permission
from app.domain.audit.entities import EventType, ActorType, EventStatus
from app.domain.audit.services import AuditService
from app.infrastructure.database.repositories.audit import SQLAlchemyAuditEventRepository

router = APIRouter(dependencies=[Depends(default_rate_limiter), Depends(require_permission(Permission.AUDIT_READ))])


def _event_to_response(event: Any) -> dict:
    return {
        "id": event.id,
        "event_type": event.event_type.value if hasattr(event.event_type, "value") else event.event_type,
        "event_version": event.event_version,
        "actor": {
            "id": event.actor_id,
            "type": event.actor_type.value if hasattr(event.actor_type, "value") else event.actor_type,
        },
        "resource": {
            "type": event.resource_type,
            "id": event.resource_id,
        },
        "action": event.action,
        "status": event.status.value if hasattr(event.status, "value") else event.status,
        "metadata": event.metadata,
        "changes": event.changes,
        "ip_address": event.ip_address,
        "session_id": event.session_id,
        "request_id": event.request_id,
        "event_hash": event.event_hash,
        "previous_event_hash": event.previous_event_hash,
        "timestamp": event.timestamp.isoformat() if event.timestamp else None,
    }


@router.get("/events")
async def list_events(
    current_user: CurrentUser,
    session: DatabaseSession,
    event_type: Optional[str] = None,
    resource_type: Optional[str] = None,
    actor_id: Optional[str] = None,
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    repo = SQLAlchemyAuditEventRepository(session)
    events, total = await repo.list_by_tenant(
        tenant_id=current_user["tenant_id"],
        limit=page_size,
        offset=(page - 1) * page_size,
        event_type=event_type,
        actor_id=actor_id,
    )
    return {
        "data": [_event_to_response(e) for e in events],
        "meta": {"page": page, "page_size": page_size, "total": total},
    }


@router.get("/events/{event_id}")
async def get_event(
    event_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    repo = SQLAlchemyAuditEventRepository(session)
    event = await repo.get_by_id(event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event.tenant_id != current_user["tenant_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return _event_to_response(event)


@router.get("/chain/status")
async def get_chain_status(
    current_user: CurrentUser,
    session: DatabaseSession,
):
    repo = SQLAlchemyAuditEventRepository(session)
    chain = await repo.get_chain_head(current_user["tenant_id"])
    if not chain:
        return {
            "chain_length": 0,
            "last_event_hash": "",
            "merkle_root": "",
            "blockchain_anchored": False,
        }
    return {
        "chain_length": chain.chain_length,
        "last_event_hash": chain.last_event_hash,
        "merkle_root": chain.merkle_root,
        "blockchain_tx_hash": chain.blockchain_tx_hash,
        "blockchain_network": chain.blockchain_network,
        "anchored_at": chain.anchored_at.isoformat() if chain.anchored_at else None,
        "blockchain_anchored": chain.blockchain_tx_hash is not None,
    }


@router.post("/chain/anchor", status_code=status.HTTP_201_CREATED)
async def anchor_chain(
    current_user: CurrentUser,
    audit: AuditServiceDep,
):
    result = await audit.anchor_chain(current_user["tenant_id"])
    return result
