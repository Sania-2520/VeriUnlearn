from typing import Optional

from app.core.logging import get_logger
from app.domain.memory.entities import MemoryEntry, MemoryType
from app.domain.memory.interfaces import MemoryRepository

logger = get_logger(__name__)


class MemoryService:
    def __init__(self, repo: MemoryRepository) -> None:
        self._repo = repo

    async def create_entry(
        self, user_id: str, tenant_id: str, memory_type: str = "persistent",
        category: str = "fact", content: dict = None, importance: float = 0.8,
    ) -> MemoryEntry:
        try:
            mtype = MemoryType(memory_type)
        except ValueError:
            mtype = MemoryType.PERSISTENT
        entry = MemoryEntry(
            tenant_id=tenant_id, user_id=user_id,
            memory_type=mtype, category=category,
            content=content or {}, importance=importance,
        )
        created = await self._repo.create(entry)
        logger.info("Memory entry created: %s type=%s", created.id, memory_type)
        return created

    async def list_entries(
        self, user_id: str, tenant_id: str, memory_type: Optional[str] = None,
        category: Optional[str] = None, page: int = 1, page_size: int = 50,
    ) -> tuple[list[MemoryEntry], int]:
        return await self._repo.list_by_user(
            user_id, tenant_id, memory_type, category, page, page_size,
        )

    async def get_entry(self, entry_id: str, tenant_id: str) -> Optional[MemoryEntry]:
        return await self._repo.get_by_id(entry_id, tenant_id)

    async def delete_entry(self, entry_id: str, tenant_id: str) -> bool:
        entry = await self._repo.get_by_id(entry_id, tenant_id)
        if not entry:
            return False
        await self._repo.soft_delete(entry_id, tenant_id)
        return True

    async def clear_memory(self, tenant_id: str, user_id: str, types: list[str]) -> int:
        count = await self._repo.clear_by_type(tenant_id, user_id, types)
        logger.info("Cleared %d memory entries for user %s types=%s", count, user_id, types)
        return count

    async def get_config(self, tenant_id: str) -> dict:
        return await self._repo.get_config(tenant_id) or {
            "persistent_memory_enabled": True,
            "retention_days": 90,
            "max_entries": 1000,
        }

    async def update_config(self, tenant_id: str, config: dict) -> dict:
        await self._repo.set_config(tenant_id, config)
        return config
