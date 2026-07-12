from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.conversation import Message
from app.models.training import TrainingDataset, TrainingSample, ModelVersion


class TrainingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_dataset(self, name: str, description: str | None = None) -> TrainingDataset:
        dataset = TrainingDataset(name=name, description=description, status="pending")
        self.db.add(dataset)
        await self.db.flush()
        await self.db.refresh(dataset)
        return dataset

    async def get_datasets(self) -> list[TrainingDataset]:
        result = await self.db.execute(
            select(TrainingDataset).order_by(TrainingDataset.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_dataset(self, dataset_id: int) -> TrainingDataset | None:
        result = await self.db.execute(select(TrainingDataset).where(TrainingDataset.id == dataset_id))
        return result.scalar_one_or_none()

    async def build_dataset_from_conversations(
        self, dataset_id: int, user_id: int | None = None
    ) -> int:
        query = select(Message).join(Message.conversation).where(
            Message.role == "assistant"
        )
        if user_id:
            query = query.where(Message.conversation.has(user_id=user_id))

        result = await self.db.execute(query)
        messages = result.scalars().all()

        count = 0
        for msg in messages:
            conv = msg.conversation

            user_prompt = None
            prev_msg_result = await self.db.execute(
                select(Message)
                .where(Message.conversation_id == msg.conversation_id)
                .where(Message.created_at < msg.created_at)
                .order_by(Message.created_at.desc())
                .limit(1)
            )
            prev_msg = prev_msg_result.scalar_one_or_none()
            if prev_msg and prev_msg.role == "user":
                user_prompt = prev_msg.content

            sample = TrainingSample(
                dataset_id=dataset_id,
                conversation_id=msg.conversation_id,
                message_id=msg.id,
                user_id=conv.user_id,
                content=msg.content,
                user_prompt=user_prompt,
                version=1,
            )
            self.db.add(sample)
            count += 1

        await self.db.flush()

        dataset = await self.get_dataset(dataset_id)
        if dataset:
            dataset.status = "ready"
            await self.db.flush()

        return count

    def write_dataset_json(self, dataset_id: int) -> Path:
        import sqlite3
        adapter_dir = Path(settings.adapter_dir)
        adapter_dir.mkdir(parents=True, exist_ok=True)
        json_path = adapter_dir / f"dataset_{dataset_id}.json"

        conn = sqlite3.connect(settings.sqlite_path)
        cursor = conn.execute(
            "SELECT user_prompt, content FROM training_samples WHERE dataset_id = ? AND user_prompt IS NOT NULL",
            (dataset_id,),
        )
        rows = cursor.fetchall()
        conn.close()

        samples = []
        for user_prompt, assistant_content in rows:
            samples.append({"role": "user", "content": user_prompt})
            samples.append({"role": "assistant", "content": assistant_content})

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(samples, f, indent=2, ensure_ascii=False)

        return json_path

    async def get_model_versions(self) -> list[ModelVersion]:
        result = await self.db.execute(
            select(ModelVersion).order_by(ModelVersion.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_model_version(self, version_id: int) -> ModelVersion | None:
        result = await self.db.execute(select(ModelVersion).where(ModelVersion.id == version_id))
        return result.scalar_one_or_none()

    async def get_active_model_version(self) -> ModelVersion | None:
        result = await self.db.execute(
            select(ModelVersion).where(ModelVersion.status == "active").order_by(ModelVersion.created_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_sample_count(self, dataset_id: int) -> int:
        result = await self.db.execute(
            select(func.count(TrainingSample.id)).where(TrainingSample.dataset_id == dataset_id)
        )
        return result.scalar() or 0

    async def activate_model_version(self, version_id: int) -> ModelVersion | None:
        result = await self.db.execute(select(ModelVersion).where(ModelVersion.id == version_id))
        version = result.scalar_one_or_none()
        if version is None:
            return None

        old_active = await self.db.execute(
            select(ModelVersion).where(ModelVersion.status == "active")
        )
        for old in old_active.scalars().all():
            old.status = "archived"

        version.status = "active"
        await self.db.flush()
        return version

    async def create_model_version(
        self,
        dataset_id: int,
        adapter_path: str,
        model_hash: str,
        num_samples: int,
        train_loss: float | None = None,
    ) -> ModelVersion:
        version = ModelVersion(
            dataset_id=dataset_id,
            base_model=settings.base_model_name,
            adapter_path=adapter_path,
            hash=model_hash,
            status="pending",
            num_samples=num_samples,
            train_loss=train_loss,
        )
        self.db.add(version)
        await self.db.flush()
        await self.db.refresh(version)
        return version

    async def update_version_with_result(self, version_id: int, task_result: dict) -> ModelVersion | None:
        result = await self.db.execute(select(ModelVersion).where(ModelVersion.id == version_id))
        version = result.scalar_one_or_none()
        if version is None:
            return None
        version.status = task_result.get("status", "completed")
        version.adapter_path = task_result.get("adapter_path", version.adapter_path)
        version.hash = task_result.get("model_hash", version.hash)
        version.train_loss = task_result.get("train_loss", version.train_loss)
        if task_result.get("num_samples"):
            version.num_samples = task_result["num_samples"]
        await self.db.flush()
        return version
