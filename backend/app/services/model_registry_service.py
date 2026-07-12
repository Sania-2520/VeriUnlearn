from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.training import ModelVersion


class ModelRegistryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_model_lineage(self, version_id: int) -> list[dict]:
        lineage = []
        current_id = version_id

        while current_id is not None:
            result = await self.db.execute(
                select(ModelVersion).where(ModelVersion.id == current_id)
            )
            version = result.scalar_one_or_none()
            if version is None:
                break

            lineage.append({
                "id": version.id,
                "base_model": version.base_model,
                "status": version.status,
                "hash": version.hash,
                "parent_version_id": version.parent_version_id,
                "created_at": str(version.created_at) if version.created_at else None,
            })
            current_id = version.parent_version_id

        return list(reversed(lineage))

    async def get_version_children(self, version_id: int) -> list[dict]:
        result = await self.db.execute(
            select(ModelVersion).where(ModelVersion.parent_version_id == version_id)
        )
        children = result.scalars().all()
        return [
            {
                "id": v.id,
                "base_model": v.base_model,
                "status": v.status,
                "hash": v.hash,
                "created_at": str(v.created_at) if v.created_at else None,
            }
            for v in children
        ]

    async def compare_versions(self, v1_id: int, v2_id: int) -> dict:
        v1_result = await self.db.execute(select(ModelVersion).where(ModelVersion.id == v1_id))
        v2_result = await self.db.execute(select(ModelVersion).where(ModelVersion.id == v2_id))

        v1 = v1_result.scalar_one_or_none()
        v2 = v2_result.scalar_one_or_none()

        if not v1 or not v2:
            return {"error": "Version not found"}

        return {
            "version_1": {
                "id": v1.id,
                "hash": v1.hash,
                "status": v1.status,
                "num_samples": v1.num_samples,
                "train_loss": v1.train_loss,
            },
            "version_2": {
                "id": v2.id,
                "hash": v2.hash,
                "status": v2.status,
                "num_samples": v2.num_samples,
                "train_loss": v2.train_loss,
            },
            "hash_match": v1.hash == v2.hash,
        }

    async def get_version_stats(self) -> dict:
        total = await self._count(ModelVersion)
        active = await self._count(ModelVersion, ModelVersion.status == "active")
        completed = await self._count(ModelVersion, ModelVersion.status == "completed")
        training = await self._count(ModelVersion, ModelVersion.status == "training")
        failed = await self._count(ModelVersion, ModelVersion.status == "failed")

        return {
            "total": total,
            "active": active,
            "completed": completed,
            "training": training,
            "failed": failed,
        }

    async def _count(self, model, *filters) -> int:
        query = select(func.count(model.id))
        if filters:
            query = query.where(*filters)
        result = await self.db.execute(query)
        return result.scalar() or 0
