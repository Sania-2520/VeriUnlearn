from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.unlearning import AuditLedger


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def log(self, user_id: int | None, event_type: str, event_data: dict, ip_address: str | None = None) -> None:
        entry = AuditLedger(
            event_type=event_type,
            event_data=event_data,
            user_id=user_id,
            ip_address=ip_address,
        )
        self.db.add(entry)

    async def get_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        event_type: str | None = None,
        user_id: int | None = None,
    ) -> list[AuditLedger]:
        query = select(AuditLedger).order_by(AuditLedger.created_at.desc())
        if event_type:
            query = query.where(AuditLedger.event_type == event_type)
        if user_id:
            query = query.where(AuditLedger.user_id == user_id)
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_logs(self, event_type: str | None = None, user_id: int | None = None) -> int:
        from sqlalchemy import func
        query = select(func.count(AuditLedger.id))
        if event_type:
            query = query.where(AuditLedger.event_type == event_type)
        if user_id:
            query = query.where(AuditLedger.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar() or 0
