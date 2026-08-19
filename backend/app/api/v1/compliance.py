from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import CurrentUser, DbSession, require_permission
from app.repositories.audit_repo import AuditRepository
from app.services.audit import AuditService
from app.services.compliance import ComplianceService

router = APIRouter(tags=["compliance"])

ReportUser = Annotated[dict, Depends(require_permission("compliance:report"))]


@router.get("/compliance/overview")
async def compliance_overview(db: DbSession, user: CurrentUser) -> dict:
    return await ComplianceService(db).overview()


@router.post("/compliance/report")
async def run_compliance_report(db: DbSession, user: ReportUser) -> dict:
    """Capture and persist a GDPR/DPDP compliance snapshot (Phase 7)."""
    report = await ComplianceService(db).run_report(created_by=user["sub"])
    return {
        "report": {
            "id": report.id,
            "gdpr_score": report.gdpr_score,
            "gdpr_status": report.gdpr_status,
            "dpdp_score": report.dpdp_score,
            "dpdp_status": report.dpdp_status,
            "risk_score": report.risk_score,
            "risk_level": report.risk_level,
            "created_at": report.created_at.isoformat() if report.created_at else None,
        }
    }


@router.get("/compliance/reports")
async def compliance_history(db: DbSession, user: CurrentUser, limit: int = Query(default=100, ge=1, le=500)) -> dict:
    """Persisted compliance snapshots (trending / export)."""
    return {"reports": await ComplianceService(db).history(limit=limit)}


@router.get("/compliance/export")
async def compliance_export(
    db: DbSession,
    user: CurrentUser,
    format: str = Query(default="csv", pattern="^(csv|json)$"),
) -> Response:
    """Export compliance history as CSV or JSON."""
    import json

    reports = await ComplianceService(db).history(limit=500)
    if format == "json":
        return Response(
            content=json.dumps(reports, indent=2, default=str),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="veriunlearn-compliance.json"'},
        )
    import csv as _csv
    import io

    buf = io.StringIO()
    writer = _csv.DictWriter(
        buf,
        fieldnames=["id", "created_at", "gdpr_score", "gdpr_status", "dpdp_score", "dpdp_status", "risk_score", "risk_level", "open_requests", "completed_requests", "certs_valid"],
        extrasaction="ignore",
    )
    writer.writeheader()
    for r in reports:
        writer.writerow(r)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="veriunlearn-compliance.csv"'},
    )


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
