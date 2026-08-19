"""Analytics (Phase 7).

Operational analytics for the dashboards and exports: deletion trends,
privacy/risk trends, request usage, dataset growth, and certificate stats.
Computations are cached in ``analytics_cache`` with a TTL so dashboards stay
cheap; exports bypass the cache.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AnalyticsCache,
    Certificate,
    ComplianceReport,
    Dataset,
    DatasetRecord,
    DeletionRequest,
    PrivacyReport,
)
from app.repositories.base import BaseRepository

_CACHE_TTL_SECONDS = 60


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; normalise to UTC-aware."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class AnalyticsCacheRepository(BaseRepository[AnalyticsCache]):
    model = AnalyticsCache


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.cache = AnalyticsCacheRepository(session)

    async def _cached(self, key: str, ttl: int, compute) -> dict[str, Any]:
        row = await self.session.scalar(select(AnalyticsCache).where(AnalyticsCache.cache_key == key))
        if row is not None:
            age = (datetime.now(timezone.utc) - _aware(row.updated_at)).total_seconds()
            if age <= ttl:
                return row.payload
        payload = await compute()
        if row is None:
            row = AnalyticsCache(cache_key=key, payload=payload)
            self.session.add(row)
        else:
            row.payload = payload
        await self.session.flush()
        return payload

    # -------------------------------------------------------------- endpoints

    async def overview(self) -> dict[str, Any]:
        async def compute() -> dict[str, Any]:
            requests = await self._request_totals()
            certs = await self.session.scalar(select(func.count()).select_from(Certificate)) or 0
            datasets = await self.session.scalar(select(func.count()).select_from(Dataset)) or 0
            records = await self.session.scalar(select(func.count()).select_from(DatasetRecord)) or 0
            reports = await self.session.scalar(select(func.count()).select_from(ComplianceReport)) or 0
            return {
                "deletion_requests": requests,
                "certificates": certs,
                "datasets": datasets,
                "records": records,
                "compliance_reports": reports,
            }

        return await self._cached("analytics.overview", _CACHE_TTL_SECONDS, compute)

    async def deletion_trends(self, days: int = 30) -> dict[str, Any]:
        async def compute() -> dict[str, Any]:
            since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
            rows = (
                await self.session.execute(
                    select(DeletionRequest.requested_at, DeletionRequest.status).where(
                        DeletionRequest.requested_at >= since
                    )
                )
            ).all()
            by_day: dict[str, dict[str, int]] = {}
            for ts, status in rows:
                day = (ts or datetime.now(timezone.utc)).strftime("%Y-%m-%d")
                bucket = by_day.setdefault(day, {"day": day, "total": 0, "completed": 0, "failed": 0})
                bucket["total"] += 1
                bucket[status if status in ("completed", "failed") else "pending"] += 1
            return {"days": days, "series": sorted(by_day.values(), key=lambda r: r["day"])}

        return await self._cached(f"analytics.deletion.{days}", _CACHE_TTL_SECONDS, compute)

    async def privacy_trends(self, days: int = 90) -> dict[str, Any]:
        async def compute() -> dict[str, Any]:
            since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
            reports = (
                await self.session.execute(
                    select(ComplianceReport).where(ComplianceReport.created_at >= since).order_by(ComplianceReport.created_at)
                )
            ).scalars().all()
            scans = (
                await self.session.execute(
                    select(PrivacyReport).where(PrivacyReport.created_at >= since).order_by(PrivacyReport.created_at)
                )
            ).scalars().all()
            return {
                "days": days,
                "compliance": [
                    {
                        "at": r.created_at.isoformat() if r.created_at else None,
                        "gdpr": r.gdpr_score,
                        "dpdp": r.dpdp_score,
                        "risk": r.risk_score,
                    }
                    for r in reports
                ],
                "scans": [
                    {"at": s.created_at.isoformat() if s.created_at else None, "risk": s.risk_score, "critical": s.critical_count}
                    for s in scans
                ],
            }

        return await self._cached(f"analytics.privacy.{days}", _CACHE_TTL_SECONDS, compute)

    async def usage(self, days: int = 30) -> dict[str, Any]:
        async def compute() -> dict[str, Any]:
            since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
            requests = (
                await self.session.execute(
                    select(DeletionRequest.method, func.count()).where(DeletionRequest.requested_at >= since).group_by(DeletionRequest.method)
                )
            ).all()
            certs = (
                await self.session.execute(
                    select(Certificate.method, func.count()).where(Certificate.created_at >= since).group_by(Certificate.method)
                )
            ).all()
            return {
                "days": days,
                "deletions_by_method": [{"method": m or "unknown", "count": c} for m, c in requests],
                "certificates_by_method": [{"method": m or "unknown", "count": c} for m, c in certs],
            }

        return await self._cached(f"analytics.usage.{days}", _CACHE_TTL_SECONDS, compute)

    async def dataset_growth(self, days: int = 90) -> dict[str, Any]:
        async def compute() -> dict[str, Any]:
            since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
            datasets = (
                await self.session.execute(
                    select(Dataset).where(Dataset.created_at >= since).order_by(Dataset.created_at)
                )
            ).scalars().all()
            return {
                "days": days,
                "series": [
                    {
                        "at": d.created_at.isoformat() if d.created_at else None,
                        "name": d.name,
                        "records": d.record_count,
                        "status": d.status,
                    }
                    for d in datasets
                ],
            }

        return await self._cached(f"analytics.growth.{days}", _CACHE_TTL_SECONDS, compute)

    async def certificate_stats(self) -> dict[str, Any]:
        async def compute() -> dict[str, Any]:
            total = await self.session.scalar(select(func.count()).select_from(Certificate)) or 0
            valid = (
                await self.session.scalar(
                    select(func.count()).select_from(Certificate).where(Certificate.verification_status == "valid")
                )
                or 0
            )
            methods = (
                await self.session.execute(select(Certificate.method, func.count()).group_by(Certificate.method))
            ).all()
            return {
                "total": total,
                "valid": valid,
                "invalid": total - valid,
                "by_method": [{"method": m or "unknown", "count": c} for m, c in methods],
            }

        return await self._cached("analytics.certificates", _CACHE_TTL_SECONDS, compute)

    # ----------------------------------------------------------------- export

    async def _request_totals(self) -> dict[str, int]:
        total = await self.session.scalar(select(func.count()).select_from(DeletionRequest)) or 0
        completed = (
            await self.session.scalar(
                select(func.count()).select_from(DeletionRequest).where(DeletionRequest.status == "completed")
            )
            or 0
        )
        failed = (
            await self.session.scalar(
                select(func.count()).select_from(DeletionRequest).where(DeletionRequest.status == "failed")
            )
            or 0
        )
        return {"total": total, "completed": completed, "failed": failed, "pending": total - completed - failed}

    def export_csv(self, rows: list[dict[str, Any]], fieldnames: list[str]) -> str:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        return buf.getvalue()

    def export_json(self, payload: dict[str, Any]) -> str:
        return json.dumps(payload, indent=2, default=str)
