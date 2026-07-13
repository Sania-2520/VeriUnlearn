import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.domain.chat.entities import ChatFolder, ChatSession, Message, MessageRole
from app.domain.chat.interfaces import ChatSessionRepository, MessageRepository, ChatFolderRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class ChatService:
    def __init__(
        self,
        session_repo: ChatSessionRepository,
        message_repo: MessageRepository,
        folder_repo: ChatFolderRepository,
    ) -> None:
        self._session_repo = session_repo
        self._message_repo = message_repo
        self._folder_repo = folder_repo

    async def create_session(self, user_id: str, tenant_id: str, **kwargs: Any) -> ChatSession:
        session = ChatSession(
            user_id=user_id,
            tenant_id=tenant_id,
            title=kwargs.get("title", "New Chat"),
            folder_id=kwargs.get("folder_id"),
            ai_provider_id=kwargs.get("ai_provider_id"),
            model=kwargs.get("model"),
            system_prompt=kwargs.get("system_prompt"),
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 4096),
        )
        created = await self._session_repo.create(session)
        logger.info("Chat session created: %s", created.id)
        return created

    async def get_session(self, session_id: str, tenant_id: str) -> Optional[ChatSession]:
        return await self._session_repo.get_by_id(session_id, tenant_id)

    async def list_sessions(
        self, user_id: str, tenant_id: str, page: int = 1, page_size: int = 25,
        folder_id: Optional[str] = None, pinned: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> tuple[list[ChatSession], int]:
        return await self._session_repo.list_by_user(
            user_id, tenant_id, page, page_size, folder_id, pinned, search,
        )

    async def update_session(self, session_id: str, tenant_id: str, **kwargs: Any) -> Optional[ChatSession]:
        session = await self._session_repo.get_by_id(session_id, tenant_id)
        if not session:
            return None
        for key in ("title", "is_pinned", "folder_id"):
            if key in kwargs:
                setattr(session, key, kwargs[key])
        session.updated_at = datetime.now(timezone.utc)
        return await self._session_repo.update(session)

    async def delete_session(self, session_id: str, tenant_id: str) -> bool:
        session = await self._session_repo.get_by_id(session_id, tenant_id)
        if not session:
            return False
        await self._session_repo.soft_delete(session_id, tenant_id)
        return True

    async def send_message(
        self, session_id: str, tenant_id: str, content: str, parent_id: Optional[str] = None,
    ) -> Message:
        now = datetime.now(timezone.utc)
        msg = Message(
            session_id=session_id,
            parent_id=parent_id,
            role=MessageRole.USER,
            content=content,
            created_at=now,
        )
        created = await self._message_repo.create(msg)
        session = await self._session_repo.get_by_id(session_id, tenant_id)
        if session:
            session.message_count += 1
            session.last_activity_at = now
            session.updated_at = now
            await self._session_repo.update(session)
        return created

    async def get_session_messages(
        self, session_id: str, page: int = 1, page_size: int = 100,
    ) -> tuple[list[Message], int]:
        return await self._message_repo.list_by_session(session_id, page, page_size)

    async def create_folder(self, user_id: str, tenant_id: str, name: str = "New Folder") -> ChatFolder:
        folder = ChatFolder(user_id=user_id, tenant_id=tenant_id, name=name)
        return await self._folder_repo.create(folder)

    async def list_folders(self, user_id: str, tenant_id: str) -> list[ChatFolder]:
        return await self._folder_repo.list_by_user(user_id, tenant_id)

    async def update_folder(self, folder_id: str, user_id: str, **kwargs: Any) -> Optional[ChatFolder]:
        folders = await self._folder_repo.list_by_user(user_id, "")
        folder = next((f for f in folders if f.id == folder_id), None)
        if not folder:
            return None
        if "name" in kwargs:
            folder.name = kwargs["name"]
        folder.updated_at = datetime.now(timezone.utc)
        return await self._folder_repo.update(folder)

    async def delete_folder(self, folder_id: str, user_id: str) -> bool:
        folders = await self._folder_repo.list_by_user(user_id, "")
        folder = next((f for f in folders if f.id == folder_id), None)
        if not folder:
            return False
        await self._folder_repo.soft_delete(folder_id, user_id)
        return True
