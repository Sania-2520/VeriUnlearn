from __future__ import annotations

from sqlalchemy import select

from app.core.exceptions import NotFoundError
from app.db.models import DeletionHistory, PrivacyReport, SearchHistory
from app.repositories.base import BaseRepository


class PrivacyRepository(BaseRepository[PrivacyReport]):
    """Privacy reports + search history."""

    model = PrivacyReport

    async def create_report(self, report: PrivacyReport) -> PrivacyReport:
        return await self.add(report)

    async def get_report(self, report_id: str) -> PrivacyReport:
        report = await self.get_or_none(report_id)
        if report is None:
            raise NotFoundError(f"Privacy report {report_id} not found")
        return report

    async def list_reports(self, limit: int = 50) -> list[PrivacyReport]:
        result = await self.session.execute(
            select(PrivacyReport).order_by(PrivacyReport.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def add_search(self, entry: SearchHistory) -> SearchHistory:
        return await self.add(entry)

    async def list_searches(self, user_id: str, limit: int = 50) -> list[SearchHistory]:
        result = await self.session.execute(
            select(SearchHistory)
            .where(SearchHistory.user_id == user_id)
            .order_by(SearchHistory.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class DeletionHistoryRepository(BaseRepository[DeletionHistory]):
    """Deletion reports (Phase 4 STEP 7)."""

    model = DeletionHistory

    async def list_reports(self, limit: int = 50) -> list[DeletionHistory]:
        result = await self.session.execute(
            select(DeletionHistory).order_by(DeletionHistory.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_request(self, request_id: str) -> DeletionHistory | None:
        result = await self.session.execute(
            select(DeletionHistory).where(DeletionHistory.request_id == request_id)
        )
        return result.scalars().first()
