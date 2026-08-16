from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models import Dataset, DatasetRecord
from app.repositories.base import BaseRepository


class DatasetRepository(BaseRepository[Dataset]):
    model = Dataset

    async def get_records(
        self, dataset_id: str, *, shard_id: int | None = None, include_deleted: bool = False
    ) -> list[DatasetRecord]:
        stmt = select(DatasetRecord).where(DatasetRecord.dataset_id == dataset_id)
        if shard_id is not None:
            stmt = stmt.where(DatasetRecord.shard_id == shard_id)
        if not include_deleted:
            stmt = stmt.where(DatasetRecord.is_deleted.is_(False))
        stmt = stmt.order_by(DatasetRecord.record_index)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_record(self, record_id: str) -> DatasetRecord:
        record = await self.session.get(DatasetRecord, record_id)
        if record is None:
            raise NotFoundError(f"Record {record_id} not found")
        return record

    async def get_records_by_ids(self, record_ids: list[str]) -> list[DatasetRecord]:
        if not record_ids:
            return []
        stmt = select(DatasetRecord).where(DatasetRecord.id.in_(record_ids))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_records(self, dataset_id: str, *, include_deleted: bool = False) -> int:
        stmt = select(func.count()).select_from(DatasetRecord).where(
            DatasetRecord.dataset_id == dataset_id
        )
        if not include_deleted:
            stmt = stmt.where(DatasetRecord.is_deleted.is_(False))
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def list_shard_sizes(self, dataset_id: str) -> dict[int, int]:
        stmt = (
            select(DatasetRecord.shard_id, func.count())
            .where(
                DatasetRecord.dataset_id == dataset_id,
                DatasetRecord.is_deleted.is_(False),
            )
            .group_by(DatasetRecord.shard_id)
        )
        result = await self.session.execute(stmt)
        return {int(shard): int(count) for shard, count in result.all()}

    async def delete_records(self, records: list[DatasetRecord]) -> None:
        for record in records:
            await self.session.delete(record)
        await self.session.flush()
