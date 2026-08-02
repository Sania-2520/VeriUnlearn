from abc import ABC, abstractmethod
from typing import Optional

from app.domain.chat.entities import ChatFolder, ChatSession, Message


class ChatSessionRepository(ABC):
    @abstractmethod
    async def create(self, session: ChatSession) -> ChatSession:
        ...

    @abstractmethod
    async def get_by_id(self, session_id: str, tenant_id: str) -> Optional[ChatSession]:
        ...

    @abstractmethod
    async def list_by_user(
        self, user_id: str, tenant_id: str, page: int, page_size: int,
        folder_id: Optional[str] = None, pinned: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> tuple[list[ChatSession], int]:
        ...

    @abstractmethod
    async def update(self, session: ChatSession) -> ChatSession:
        ...

    @abstractmethod
    async def soft_delete(self, session_id: str, tenant_id: str) -> None:
        ...

    @abstractmethod
    async def hard_delete(self, session_id: str, tenant_id: str) -> None:
        ...


class MessageRepository(ABC):
    @abstractmethod
    async def create(self, message: Message) -> Message:
        ...

    @abstractmethod
    async def get_by_id(self, message_id: str, tenant_id: str) -> Optional[Message]:
        ...

    @abstractmethod
    async def list_by_session(
        self, session_id: str, page: int, page_size: int,
    ) -> tuple[list[Message], int]:
        ...

    @abstractmethod
    async def delete_by_session(self, session_id: str, tenant_id: str) -> None:
        ...


class ChatFolderRepository(ABC):
    @abstractmethod
    async def create(self, folder: ChatFolder) -> ChatFolder:
        ...

    @abstractmethod
    async def list_by_user(self, user_id: str, tenant_id: str) -> list[ChatFolder]:
        ...

    @abstractmethod
    async def update(self, folder: ChatFolder) -> ChatFolder:
        ...

    @abstractmethod
    async def soft_delete(self, folder_id: str, user_id: str) -> None:
        ...
