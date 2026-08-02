import logging
from typing import Optional

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import delete, select

from app.domain.chat.entities import ChatFolder, ChatSession, Message
from app.domain.chat.interfaces import (
    ChatFolderRepository,
    ChatSessionRepository,
    MessageRepository,
)
from app.infrastructure.database.models import ChatFolderModel, ChatMessageModel, ChatSessionModel

logger = logging.getLogger(__name__)


class SQLAlchemyChatSessionRepository(ChatSessionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, session: ChatSession) -> ChatSession:
        model = ChatSessionModel(
            id=session.id,
            user_id=session.user_id,
            tenant_id=session.tenant_id,
            title=session.title,
            folder_id=session.folder_id,
            ai_provider_id=session.ai_provider_id,
            model=session.model,
            system_prompt=session.system_prompt,
            temperature=session.temperature,
            max_tokens=session.max_tokens,
            is_pinned=session.is_pinned,
            is_archived=session.is_archived,
            is_deleted=session.is_deleted,
            deleted_at=session.deleted_at,
            message_count=session.message_count,
            total_tokens=session.total_tokens,
            total_cost=session.total_cost,
            metadata=session.metadata,
            last_activity_at=session.last_activity_at,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return session

    async def get_by_id(self, session_id: str, tenant_id: str) -> Optional[ChatSession]:
        stmt = select(ChatSessionModel).where(
            ChatSessionModel.id == session_id,
            ChatSessionModel.tenant_id == tenant_id,
            ChatSessionModel.is_deleted == False,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._model_to_entity(model)

    async def list_by_user(
        self, user_id: str, tenant_id: str, page: int = 1, page_size: int = 25,
        folder_id: Optional[str] = None, pinned: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> tuple[list[ChatSession], int]:
        query = select(ChatSessionModel).where(
            ChatSessionModel.user_id == user_id,
            ChatSessionModel.tenant_id == tenant_id,
            ChatSessionModel.is_deleted == False,
        )
        if folder_id is not None:
            query = query.where(ChatSessionModel.folder_id == folder_id)
        if pinned is not None:
            query = query.where(ChatSessionModel.is_pinned == pinned)
        if search:
            query = query.where(ChatSessionModel.title.ilike(f"%{search}%"))
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar() or 0
        query = query.order_by(ChatSessionModel.last_activity_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(query)
        models = result.scalars().all()
        return [self._model_to_entity(m) for m in models], total

    async def update(self, session: ChatSession) -> ChatSession:
        stmt = select(ChatSessionModel).where(ChatSessionModel.id == session.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            model.title = session.title
            model.folder_id = session.folder_id
            model.is_pinned = session.is_pinned
            model.is_archived = session.is_archived
            model.message_count = session.message_count
            model.total_tokens = session.total_tokens
            model.total_cost = session.total_cost
            model.last_activity_at = session.last_activity_at
            model.updated_at = session.updated_at
            await self._session.flush()
        return session

    async def soft_delete(self, session_id: str, tenant_id: str) -> None:
        from datetime import datetime, timezone
        stmt = select(ChatSessionModel).where(
            ChatSessionModel.id == session_id,
            ChatSessionModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            model.is_deleted = True
            model.deleted_at = datetime.now(timezone.utc)
            await self._session.flush()

    async def hard_delete(self, session_id: str, tenant_id: str) -> None:
        stmt = delete(ChatSessionModel).where(
            ChatSessionModel.id == session_id,
            ChatSessionModel.tenant_id == tenant_id,
        )
        await self._session.execute(stmt)
        await self._session.flush()

    @staticmethod
    def _model_to_entity(model: ChatSessionModel) -> ChatSession:
        return ChatSession(
            id=model.id,
            user_id=model.user_id,
            tenant_id=model.tenant_id,
            title=model.title,
            folder_id=model.folder_id,
            ai_provider_id=model.ai_provider_id,
            model=model.model,
            system_prompt=model.system_prompt,
            temperature=model.temperature,
            max_tokens=model.max_tokens,
            is_pinned=model.is_pinned,
            is_archived=model.is_archived,
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
            message_count=model.message_count,
            total_tokens=model.total_tokens,
            total_cost=model.total_cost,
            metadata=model.metadata or {},
            last_activity_at=model.last_activity_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SQLAlchemyMessageRepository(MessageRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, message: Message) -> Message:
        model = ChatMessageModel(
            id=message.id,
            session_id=message.session_id,
            parent_id=message.parent_id,
            role=message.role.value,
            content=message.content,
            content_type=message.content_type.value,
            content_rendered=message.content_rendered,
            metadata=message.metadata,
            is_streaming=message.is_streaming,
            is_regenerated=message.is_regenerated,
            is_edited=message.is_edited,
            feedback=message.feedback.value if message.feedback else None,
            tokens_input=message.tokens_input,
            tokens_output=message.tokens_output,
            cost=message.cost,
            latency_ms=message.latency_ms,
            model_used=message.model_used,
            provider_used=message.provider_used,
            created_at=message.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        return message

    async def get_by_id(self, message_id: str, tenant_id: str) -> Optional[Message]:
        stmt = select(ChatMessageModel).where(ChatMessageModel.id == message_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._model_to_entity(model)

    async def list_by_session(
        self, session_id: str, page: int = 1, page_size: int = 100,
    ) -> tuple[list[Message], int]:
        query = select(ChatMessageModel).where(ChatMessageModel.session_id == session_id)
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar() or 0
        query = query.order_by(ChatMessageModel.created_at.asc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(query)
        models = result.scalars().all()
        return [self._model_to_entity(m) for m in models], total

    async def delete_by_session(self, session_id: str, tenant_id: str) -> None:
        stmt = delete(ChatMessageModel).where(ChatMessageModel.session_id == session_id)
        await self._session.execute(stmt)
        await self._session.flush()

    @staticmethod
    def _model_to_entity(model: ChatMessageModel) -> Message:
        from app.domain.chat.entities import FeedbackType, MessageContentType, MessageRole
        feedback = None
        if model.feedback:
            try:
                feedback = FeedbackType(model.feedback)
            except ValueError:
                logger.warning("Invalid feedback value in DB: %s", model.feedback)
        return Message(
            id=model.id,
            session_id=model.session_id,
            parent_id=model.parent_id,
            role=MessageRole(model.role),
            content=model.content,
            content_type=MessageContentType(model.content_type),
            content_rendered=model.content_rendered,
            metadata=model.metadata or {},
            is_streaming=model.is_streaming,
            is_regenerated=model.is_regenerated,
            is_edited=model.is_edited,
            feedback=feedback,
            tokens_input=model.tokens_input,
            tokens_output=model.tokens_output,
            cost=model.cost,
            latency_ms=model.latency_ms,
            model_used=model.model_used,
            provider_used=model.provider_used,
            created_at=model.created_at,
        )


class SQLAlchemyChatFolderRepository(ChatFolderRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, folder: ChatFolder) -> ChatFolder:
        model = ChatFolderModel(
            id=folder.id,
            user_id=folder.user_id,
            tenant_id=folder.tenant_id,
            name=folder.name,
            parent_id=folder.parent_id,
            sort_order=folder.sort_order,
            is_deleted=folder.is_deleted,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return folder

    async def list_by_user(self, user_id: str, tenant_id: str) -> list[ChatFolder]:
        query = select(ChatFolderModel).where(
            ChatFolderModel.user_id == user_id,
            ChatFolderModel.is_deleted == False,
        )
        result = await self._session.execute(query)
        models = result.scalars().all()
        return [self._model_to_entity(m) for m in models]

    async def update(self, folder: ChatFolder) -> ChatFolder:
        stmt = select(ChatFolderModel).where(ChatFolderModel.id == folder.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            model.name = folder.name
            model.parent_id = folder.parent_id
            model.sort_order = folder.sort_order
            model.updated_at = folder.updated_at
            await self._session.flush()
        return folder

    async def soft_delete(self, folder_id: str, user_id: str) -> None:
        stmt = select(ChatFolderModel).where(
            ChatFolderModel.id == folder_id,
            ChatFolderModel.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            model.is_deleted = True
            await self._session.flush()

    @staticmethod
    def _model_to_entity(model: ChatFolderModel) -> ChatFolder:
        return ChatFolder(
            id=model.id,
            user_id=model.user_id,
            tenant_id=model.tenant_id,
            name=model.name,
            parent_id=model.parent_id,
            sort_order=model.sort_order,
            is_deleted=model.is_deleted,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
