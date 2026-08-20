"""Chat session persistence for the Assistant audit trail."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChatSession
from app.repositories.base import BaseRepository


class ChatSessionRepository(BaseRepository[ChatSession]):
    model = ChatSession

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_id(self, session_id: str) -> ChatSession | None:
        result = await self.session.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def create(self, *, user_id: str, name: str) -> ChatSession:
        session = ChatSession(user_id=user_id, name=name, content="", messages_json="", sensitive_data="")
        return await self.add(session)

    async def append(
        self,
        session: ChatSession,
        *,
        transcript: str,
        messages_json: str,
        sensitive_data: str,
        message_count: int,
    ) -> ChatSession:
        session.content = transcript
        session.messages_json = messages_json
        session.sensitive_data = sensitive_data
        session.message_count = message_count
        await self.add(session)
        return session

    async def list_for_user(
        self,
        user_id: str,
        limit: int = 200,
        *,
        search: str | None = None,
        from_ts: datetime | None = None,
        to_ts: datetime | None = None,
    ) -> list[ChatSession]:
        stmt = select(ChatSession).where(ChatSession.user_id == user_id)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                or_(
                    ChatSession.id.ilike(like),
                    ChatSession.name.ilike(like),
                    ChatSession.content.ilike(like),
                )
            )
        if from_ts is not None:
            stmt = stmt.where(ChatSession.updated_at >= from_ts)
        if to_ts is not None:
            stmt = stmt.where(ChatSession.updated_at <= to_ts)
        stmt = stmt.order_by(ChatSession.updated_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())