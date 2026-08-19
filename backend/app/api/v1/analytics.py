from __future__ import annotations

from fastapi import APIRouter, Query, Response

from app.api.deps import CurrentUser, DbSession
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
async def analytics_overview(db: DbSession, user: CurrentUser) -> dict:
    return await AnalyticsService(db).overview()


@router.get("/deletion-trends")
async def deletion_trends(db: DbSession, user: CurrentUser, days: int = Query(default=30, ge=1, le=365)) -> dict:
    return await AnalyticsService(db).deletion_trends(days)


@router.get("/privacy-trends")
async def privacy_trends(db: DbSession, user: CurrentUser, days: int = Query(default=90, ge=1, le=730)) -> dict:
    return await AnalyticsService(db).privacy_trends(days)


@router.get("/usage")
async def usage(db: DbSession, user: CurrentUser, days: int = Query(default=30, ge=1, le=365)) -> dict:
    return await AnalyticsService(db).usage(days)


@router.get("/dataset-growth")
async def dataset_growth(db: DbSession, user: CurrentUser, days: int = Query(default=90, ge=1, le=730)) -> dict:
    return await AnalyticsService(db).dataset_growth(days)


@router.get("/certificates")
async def certificate_stats(db: DbSession, user: CurrentUser) -> dict:
    return await AnalyticsService(db).certificate_stats()


@router.get("/export")
async def export_analytics(
    db: DbSession,
    user: CurrentUser,
    format: str = Query(default="csv", pattern="^(csv|json)$"),
) -> Response:
    """Export analytics overview + trends as CSV or JSON."""
    service = AnalyticsService(db)
    overview = await service.overview()
    trends = await service.deletion_trends(30)
    certs = await service.certificate_stats()
    if format == "json":
        body = service.export_json({"overview": overview, "deletion_trends": trends, "certificates": certs})
        return Response(
            content=body,
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="veriunlearn-analytics.json"'},
        )
    rows: list[dict] = []
    for point in trends["series"]:
        rows.append({"metric": "deletion", **point})
    rows.append({"metric": "overview", "day": "", "total": overview["deletion_requests"]["total"], "completed": overview["deletion_requests"]["completed"], "failed": overview["deletion_requests"]["failed"]})
    rows.append({"metric": "certificates", "day": "", "total": certs["total"], "completed": certs["valid"], "failed": certs["invalid"]})
    body = service.export_csv(rows, ["metric", "day", "total", "completed", "failed"])
    return Response(
        content=body,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="veriunlearn-analytics.csv"'},
    )
