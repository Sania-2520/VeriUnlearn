from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.repositories.audit_repo import AuditRepository
from app.services.audit import AuditService
from app.services.compliance import ComplianceService

router = APIRouter(tags=["compliance"])


@router.get("/compliance/overview")
async def compliance_overview(db: DbSession, user: CurrentUser) -> dict:
    return await ComplianceService(db).overview()


@router.get("/audit")
async def audit_trail(db: DbSession, user: CurrentUser, limit: int = 200) -> dict:
    repo = AuditRepository(db)
    events = await repo.list(limit=limit)
    return {
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "actor": e.actor,
                "subject": e.subject,
                "certificate_id": e.certificate_id,
                "prev_hash": e.prev_hash,
                "event_hash": e.event_hash,
                "payload": e.payload,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ]
    }


@router.get("/audit/verify")
async def verify_audit_chain(db: DbSession, user: CurrentUser) -> dict:
    """Tamper detection: recompute the hash chain end-to-end."""
    return await AuditService(db).verify_chain()
