from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditEvent
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuditEvent]):
    model = AuditEvent

    async def latest_hash(self) -> str | None:
        result = await self.session.execute(
            select(AuditEvent.event_hash).order_by(AuditEvent.created_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def ordered_events(self) -> list[AuditEvent]:
        result = await self.session.execute(
            select(AuditEvent).order_by(AuditEvent.created_at.asc())
        )
        return list(result.scalars().all())
