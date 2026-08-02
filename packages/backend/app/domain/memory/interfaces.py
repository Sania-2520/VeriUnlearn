from abc import ABC, abstractmethod
from typing import Optional

from app.domain.memory.entities import MemoryEntry


class MemoryRepository(ABC):
    @abstractmethod
    async def create(self, entry: MemoryEntry) -> MemoryEntry:
        ...

    @abstractmethod
    async def get_by_id(self, entry_id: str, tenant_id: str) -> Optional[MemoryEntry]:
        ...

    @abstractmethod
    async def list_by_user(
        self, user_id: str, tenant_id: str, memory_type: Optional[str] = None,
        category: Optional[str] = None, page: int = 1, page_size: int = 50,
    ) -> tuple[list[MemoryEntry], int]:
        ...

    @abstractmethod
    async def soft_delete(self, entry_id: str, tenant_id: str) -> None:
        ...

    @abstractmethod
    async def clear_by_type(self, tenant_id: str, user_id: str, types: list[str]) -> int:
        ...

    @abstractmethod
    async def get_config(self, tenant_id: str) -> Optional[dict]:
        ...

    @abstractmethod
    async def set_config(self, tenant_id: str, config: dict) -> None:
        ...
