from __future__ import annotations

import hashlib
import json
from typing import AsyncGenerator

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.conversation import Conversation, Message
from app.models.training import ModelVersion, TrainingSample
from app.models.user import User
from app.ml.inference import InferenceEngine
from app.services.rag_service import RAGService


class ChatService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.inference = InferenceEngine()

    async def create_conversation(self, user: User, title: str = "New Conversation") -> Conversation:
        conv = Conversation(user_id=user.id, title=title)
        self.db.add(conv)
        await self.db.flush()
        await self.db.refresh(conv)
        return conv

    async def get_conversations(self, user: User) -> list[dict]:
        result = await self.db.execute(
            select(
                Conversation.id,
                Conversation.title,
                Conversation.is_active,
                Conversation.created_at,
                Conversation.updated_at,
                func.count(Message.id).label("message_count"),
            )
            .outerjoin(Message, Message.conversation_id == Conversation.id)
            .where(Conversation.user_id == user.id)
            .group_by(Conversation.id)
            .order_by(Conversation.updated_at.desc().nullslast(), Conversation.created_at.desc())
        )
        rows = result.all()
        return [
            {
                "id": r.id,
                "title": r.title,
                "is_active": r.is_active,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
                "message_count": r.message_count,
            }
            for r in rows
        ]

    async def get_messages(self, conversation_id: int, user: User) -> list[Message]:
        result = await self.db.execute(
            select(Message)
            .join(Conversation)
            .where(Message.conversation_id == conversation_id, Conversation.user_id == user.id)
            .order_by(Message.created_at)
        )
        messages = list(result.scalars().all())
        if not messages:
            conv_result = await self.db.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            conv = conv_result.scalar_one_or_none()
            if conv is None:
                raise ValueError("Conversation not found")
            if conv.user_id != user.id:
                raise ValueError("Conversation not found")
        return messages

    async def rename_conversation(self, conversation_id: int, user: User, title: str) -> Conversation:
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user.id)
        )
        conv = result.scalar_one_or_none()
        if conv is None:
            raise ValueError("Conversation not found")
        conv.title = title
        await self.db.flush()
        await self.db.refresh(conv)
        return conv

    async def delete_conversation(self, conversation_id: int, user: User) -> None:
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user.id)
        )
        conv = result.scalar_one_or_none()
        if conv is None:
            raise ValueError("Conversation not found")
        await self.db.delete(conv)
        await self.db.flush()

    async def send_message(
        self, conversation_id: int, user: User, content: str, stream: bool = False
    ) -> dict:
        conv_result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user.id)
        )
        conv = conv_result.scalar_one_or_none()
        if conv is None:
            raise ValueError("Conversation not found")

        user_msg = Message(conversation_id=conversation_id, role="user", content=content)
        self.db.add(user_msg)
        await self.db.flush()
        await self.db.refresh(user_msg)

        history = await self._build_history(conversation_id)

        rag_context = await self._retrieve_rag_context(content, user.id)

        model_version = await self._get_active_model_version()

        adapter_path = model_version.adapter_path if model_version and model_version.adapter_path else None
        self.inference._reload_with_adapter(adapter_path)

        assistant_content = await self.inference.generate(
            prompt=content,
            history=history,
            rag_context=rag_context,
            stream=stream,
        )

        assistant_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_content,
            tokens=len(assistant_content.split()),
        )
        self.db.add(assistant_msg)
        await self.db.flush()
        await self.db.refresh(assistant_msg)

        conv.title = content[:80] + "..." if len(content) > 80 else content
        await self.db.flush()

        conv_hash = hashlib.sha256(str(conversation_id).encode()).hexdigest()

        sample = await self._create_training_sample(
            conversation_id, user, assistant_msg, conv_hash, user_prompt=content
        )

        return {
            "message": assistant_msg,
            "model_version": f"{model_version.base_model}/v{model_version.id}" if model_version else None,
            "sample_id": sample.id if sample else None,
        }

    async def send_message_stream(
        self, conversation_id: int, user: User, content: str
    ) -> AsyncGenerator[str, None]:
        conv_result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user.id)
        )
        conv = conv_result.scalar_one_or_none()
        if conv is None:
            yield f"data: {json.dumps({'error': 'Conversation not found'})}\n\n"
            return

        user_msg = Message(conversation_id=conversation_id, role="user", content=content)
        self.db.add(user_msg)
        await self.db.flush()
        await self.db.refresh(user_msg)

        history = await self._build_history(conversation_id)

        rag_context = await self._retrieve_rag_context(content, user.id)

        model_version = await self._get_active_model_version()

        adapter_path = model_version.adapter_path if model_version and model_version.adapter_path else None
        self.inference._reload_with_adapter(adapter_path)

        full_response = ""
        async for token in self.inference.generate_stream(
            prompt=content,
            history=history,
            rag_context=rag_context,
        ):
            full_response += token
            yield f"data: {json.dumps({'token': token})}\n\n"

        assistant_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=full_response,
            tokens=len(full_response.split()),
        )
        self.db.add(assistant_msg)
        await self.db.flush()
        await self.db.refresh(assistant_msg)

        conv.title = content[:80] + "..." if len(content) > 80 else content
        await self.db.flush()

        conv_hash = hashlib.sha256(str(conversation_id).encode()).hexdigest()
        await self._create_training_sample(conversation_id, user, assistant_msg, conv_hash, user_prompt=content)

        yield f"data: {json.dumps({'done': True, 'message_id': assistant_msg.id, 'model_version': model_version.base_model + '/v' + str(model_version.id) if model_version else None})}\n\n"

    async def _retrieve_rag_context(self, query: str, user_id: int) -> str:
        try:
            rag = RAGService(self.db)
            results = await rag.retrieve(query, top_k=3, user_id=user_id)
            if not results:
                return ""
            context_parts = []
            for r in results:
                context_parts.append(f"[Document chunk (score: {r['score']:.2f})]\n{r['content']}")
            return "\n\n".join(context_parts)
        except Exception:
            return ""

    async def _get_active_model_version(self) -> ModelVersion | None:
        result = await self.db.execute(
            select(ModelVersion).where(ModelVersion.status == "active").order_by(ModelVersion.created_at.desc()).limit(1)
        )
        version = result.scalar_one_or_none()
        if version is not None:
            return version
        return ModelVersion(
            id=0,
            base_model=settings.base_model_name,
            adapter_path="",
            hash="",
            status="active",
            num_samples=0,
        )

    async def _create_training_sample(
        self, conversation_id: int, user: User, assistant_msg: Message, conv_hash: str,
        user_prompt: str | None = None,
    ) -> TrainingSample:
        sample = TrainingSample(
            dataset_id=None,
            conversation_id=conversation_id,
            message_id=assistant_msg.id,
            user_id=user.id,
            shard_id=conv_hash[:8],
            slice_id=None,
            content=assistant_msg.content,
            user_prompt=user_prompt,
            version=1,
        )
        self.db.add(sample)
        await self.db.flush()
        return sample

    async def _build_history(self, conversation_id: int) -> list[dict]:
        result = await self.db.execute(
            select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
        )
        messages = result.scalars().all()
        return [
            {"role": m.role, "content": m.content}
            for m in messages[-10:]
        ]
