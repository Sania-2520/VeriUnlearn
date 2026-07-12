from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message
from app.models.document import Document
from app.models.training import TrainingSample, ModelVersion
from app.models.unlearning import UnlearningRequest


class UsageQuota:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_usage(self, user_id: int) -> dict:
        conv_count = await self._count(Conversation, Conversation.user_id == user_id)
        msg_count = await self._count(
            Message, Message.conversation_id.in_(
                select(Conversation.id).where(Conversation.user_id == user_id)
            )
        )
        doc_count = await self._count(Document, Document.user_id == user_id)
        sample_count = await self._count(TrainingSample, TrainingSample.user_id == user_id)
        version_count = await self._count(
            ModelVersion, ModelVersion.dataset_id.in_(
                select(TrainingSample.dataset_id).where(
                    TrainingSample.user_id == user_id,
                    TrainingSample.dataset_id.isnot(None),
                ).distinct()
            )
        )
        unlearn_count = await self._count(UnlearningRequest, UnlearningRequest.user_id == user_id)

        return {
            "conversations": {"used": conv_count, "limit": 500},
            "messages": {"used": msg_count, "limit": 10000},
            "documents": {"used": doc_count, "limit": 100},
            "training_samples": {"used": sample_count, "limit": 10000},
            "model_versions": {"used": version_count, "limit": 50},
            "unlearning_requests": {"used": unlearn_count, "limit": 50},
        }

    async def _count(self, model, *filters) -> int:
        query = select(func.count(model.id)).where(*filters)
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def check_quota(self, user_id: int, resource: str, quantity: int = 1) -> bool:
        usage = await self.get_usage(user_id)
        if resource not in usage:
            return True
        return usage[resource]["used"] + quantity <= usage[resource]["limit"]
