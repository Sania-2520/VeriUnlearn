from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DeletionRequest
from app.repositories.base import BaseRepository


class DeletionRepository(BaseRepository[DeletionRequest]):
    model = DeletionRequest

    async def create(self, request: DeletionRequest) -> DeletionRequest:
        return await self.add(request)
