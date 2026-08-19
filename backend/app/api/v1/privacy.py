from __future__ import annotations

from fastapi import APIRouter, Body, Query
from fastapi.responses import JSONResponse

from app.api.deps import CurrentUser, DbSession
from app.core.exceptions import NotFoundError
from app.repositories.privacy_repo import PrivacyRepository
from app.schemas.privacy import ExportRequest, ScanRequest, SearchRequest
from app.services.audit import AuditService
from app.services.privacy import PrivacyService

router = APIRouter(prefix="/privacy", tags=["privacy"])


@router.post("/search")
async def search_identities(
    db: DbSession,
    user: CurrentUser,
    query: str = Query(default="", description="Free-text query across identity fields"),
    limit: int = Query(default=50, ge=1, le=500),
    payload: SearchRequest | None = Body(default=None),
) -> dict:
    """Privacy Audit: scan all shards/datasets for an identity.

    Compatible with the original ``?query=`` form; an optional JSON body adds
    structured filters (name, email, phone, aadhaar, pan, passport, record_id,
    chat_id, ...).
    """
    body = payload or SearchRequest()
    effective_query = body.query or query
    matches = await PrivacyService(db).search_identities(
        effective_query,
        limit=limit,
        identity_key_filter=body.identity_key,
        filters=body.filters,
        user_id=user["sub"],
    )
    return {
        "query": effective_query,
        "filters": body.filters or {},
        "match_count": len(matches),
        "matches": matches,
        "scanned": "all_shards",
    }


@router.post("/scan")
async def scan_datasets(db: DbSession, user: CurrentUser, payload: ScanRequest | None = Body(default=None)) -> dict:
    """Full privacy scan: detect PII categories + severity across records."""
    body = payload or ScanRequest()
    service = PrivacyService(db)
    report = await service.scan_all(
        dataset_id=body.dataset_id, identity_key_filter=body.identity_key, created_by=user["sub"]
    )
    await AuditService(db).log(
        event_type="privacy.scan.completed",
        actor=user["sub"],
        subject=body.identity_key or body.dataset_id or "all",
        payload={
            "report_id": report.id,
            "scanned_records": report.scanned_records,
            "findings": report.findings_count,
            "risk_score": report.risk_score,
        },
    )
    return {
        "report_id": report.id,
        "scanned_records": report.scanned_records,
        "findings_count": report.findings_count,
        "risk_score": report.risk_score,
        "counts_by_severity": {
            "critical": report.critical_count,
            "high": report.high_count,
            "medium": report.medium_count,
            "low": report.low_count,
        },
        "categories": report.categories,
    }


@router.get("/reports")
async def list_reports(db: DbSession, user: CurrentUser, limit: int = Query(default=50, ge=1, le=200)) -> dict:
    reports = await PrivacyRepository(db).list_reports(limit=limit)
    return {
        "reports": [
            {
                "id": r.id,
                "scope": r.scope,
                "subject": r.subject,
                "dataset_id": r.dataset_id,
                "scanned_records": r.scanned_records,
                "findings_count": r.findings_count,
                "critical_count": r.critical_count,
                "high_count": r.high_count,
                "medium_count": r.medium_count,
                "low_count": r.low_count,
                "risk_score": r.risk_score,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reports
        ]
    }


@router.get("/report/{report_id}")
async def get_report(report_id: str, db: DbSession, user: CurrentUser) -> dict:
    report = await PrivacyRepository(db).get_report(report_id)
    return {
        "id": report.id,
        "scope": report.scope,
        "subject": report.subject,
        "dataset_id": report.dataset_id,
        "scanned_records": report.scanned_records,
        "findings_count": report.findings_count,
        "critical_count": report.critical_count,
        "high_count": report.high_count,
        "medium_count": report.medium_count,
        "low_count": report.low_count,
        "categories": report.categories,
        "risk_score": report.risk_score,
        "findings": report.findings,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


@router.get("/records/{record_id}")
async def get_record(record_id: str, db: DbSession, user: CurrentUser) -> dict:
    """Record viewer: text, metadata, file, dataset, chunk/embedding/hash."""
    return await PrivacyService(db).get_record_detail(record_id)


@router.get("/footprint/{identity_key}")
async def identity_footprint(identity_key: str, db: DbSession, user: CurrentUser) -> dict:
    """Identity Footprint Analysis: full memory profile of an identity."""
    try:
        return await PrivacyService(db).identity_footprint(identity_key)
    except LookupError as exc:
        raise NotFoundError(str(exc)) from exc


@router.get("/history")
async def search_history(db: DbSession, user: CurrentUser, limit: int = Query(default=50, ge=1, le=200)) -> dict:
    entries = await PrivacyRepository(db).list_searches(user["sub"], limit=limit)
    return {
        "history": [
            {
                "id": e.id,
                "query": e.query,
                "filters": e.filters,
                "result_count": e.result_count,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entries
        ]
    }


@router.get("/overview")
async def privacy_overview(db: DbSession, user: CurrentUser) -> dict:
    return await PrivacyService(db).privacy_overview()


@router.post("/export")
async def export_search(
    db: DbSession, user: CurrentUser, payload: ExportRequest | None = Body(default=None)
) -> JSONResponse:
    """Export identity search results as a downloadable JSON file."""
    body = payload or ExportRequest()
    service = PrivacyService(db)
    matches = await service.search_identities(
        body.query or "", identity_key_filter=body.identity_key, filters=body.filters, limit=500
    )
    return JSONResponse(
        content={"query": body.query or "", "filters": body.filters or {}, "match_count": len(matches), "matches": matches},
        headers={"Content-Disposition": 'attachment; filename="privacy-export.json"'},
    )
