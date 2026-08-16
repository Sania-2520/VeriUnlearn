from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MLModel, ModelShard
from app.repositories.base import BaseRepository


class ModelRepository(BaseRepository[MLModel]):
    model = MLModel

    async def get_active_for_dataset(self, dataset_id: str) -> MLModel | None:
        result = await self.session.execute(
            select(MLModel)
            .where(MLModel.dataset_id == dataset_id, MLModel.is_active.is_(True))
            .order_by(MLModel.version.desc())
        )
        return result.scalars().first()

    async def get_shards(self, model_id: str) -> list[ModelShard]:
        result = await self.session.execute(
            select(ModelShard)
            .where(ModelShard.model_id == model_id)
            .order_by(ModelShard.shard_index)
        )
        return list(result.scalars().all())

    async def get_shard(self, model_id: str, shard_index: int) -> ModelShard:
        result = await self.session.execute(
            select(ModelShard).where(
                ModelShard.model_id == model_id, ModelShard.shard_index == shard_index
            )
        )
        shard = result.scalar_one_or_none()
        if shard is None:
            raise LookupError(f"Shard {shard_index} not found for model {model_id}")
        return shard

    async def add_shard(self, shard: ModelShard) -> ModelShard:
        self.session.add(shard)
        await self.session.flush()
        return shard
