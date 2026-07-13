import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select

from app.domain.memory.entities import MemoryEntry, MemoryType, MemoryCategory
from app.domain.memory.interfaces import MemoryRepository
from app.infrastructure.database.models import MemoryEntryModel, MemoryConfigModel


class SQLAlchemyMemoryRepository(MemoryRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, entry: MemoryEntry) -> MemoryEntry:
        model = MemoryEntryModel(
            id=entry.id,
            tenant_id=entry.tenant_id,
            user_id=entry.user_id,
            session_id=entry.session_id,
            memory_type=entry.memory_type.value if hasattr(entry.memory_type, "value") else entry.memory_type,
            category=entry.category,
            content=entry.content,
            importance=entry.importance,
            access_count=entry.access_count,
            last_accessed_at=entry.last_accessed_at,
            expires_at=entry.expires_at,
            event_metadata=entry.metadata,
            is_deleted=entry.is_deleted,
            deleted_at=entry.deleted_at,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return entry

    async def get_by_id(self, entry_id: str, tenant_id: str) -> Optional[MemoryEntry]:
        stmt = select(MemoryEntryModel).where(
            MemoryEntryModel.id == entry_id,
            MemoryEntryModel.tenant_id == tenant_id,
            MemoryEntryModel.is_deleted == False,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._model_to_entity(model)

    async def list_by_user(
        self, user_id: str, tenant_id: str, memory_type: Optional[str] = None,
        category: Optional[str] = None, page: int = 1, page_size: int = 50,
    ) -> tuple[list[MemoryEntry], int]:
        query = select(MemoryEntryModel).where(
            MemoryEntryModel.tenant_id == tenant_id,
            MemoryEntryModel.user_id == user_id,
            MemoryEntryModel.is_deleted == False,
        )
        if memory_type:
            query = query.where(MemoryEntryModel.memory_type == memory_type)
        if category:
            query = query.where(MemoryEntryModel.category == category)
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar() or 0
        query = query.order_by(MemoryEntryModel.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(query)
        models = result.scalars().all()
        return [self._model_to_entity(m) for m in models], total

    async def soft_delete(self, entry_id: str, tenant_id: str) -> None:
        stmt = select(MemoryEntryModel).where(
            MemoryEntryModel.id == entry_id,
            MemoryEntryModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            model.is_deleted = True
            model.deleted_at = datetime.now(timezone.utc)
            await self._session.flush()

    async def clear_by_type(self, tenant_id: str, user_id: str, types: list[str]) -> int:
        stmt = select(MemoryEntryModel).where(
            MemoryEntryModel.tenant_id == tenant_id,
            MemoryEntryModel.user_id == user_id,
            MemoryEntryModel.memory_type.in_(types),
            MemoryEntryModel.is_deleted == False,
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        now = datetime.now(timezone.utc)
        for model in models:
            model.is_deleted = True
            model.deleted_at = now
        await self._session.flush()
        return len(models)

    async def get_config(self, tenant_id: str) -> Optional[dict]:
        stmt = select(MemoryConfigModel).where(MemoryConfigModel.tenant_id == tenant_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return {
            "persistent_memory_enabled": model.persistent_memory_enabled,
            "retention_days": model.retention_days,
            "max_entries": model.max_entries,
        }

    async def set_config(self, tenant_id: str, config: dict) -> None:
        stmt = select(MemoryConfigModel).where(MemoryConfigModel.tenant_id == tenant_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            model = MemoryConfigModel(id=str(uuid.uuid4()), tenant_id=tenant_id)
            self._session.add(model)
        if "persistent_memory_enabled" in config:
            model.persistent_memory_enabled = config["persistent_memory_enabled"]
        if "retention_days" in config:
            model.retention_days = config["retention_days"]
        if "max_entries" in config:
            model.max_entries = config["max_entries"]
        model.updated_at = datetime.now(timezone.utc)
        await self._session.flush()

    @staticmethod
    def _model_to_entity(model: MemoryEntryModel) -> MemoryEntry:
        try:
            mtype = MemoryType(model.memory_type)
        except ValueError:
            mtype = MemoryType.PERSISTENT
        return MemoryEntry(
            id=model.id,
            tenant_id=model.tenant_id,
            user_id=model.user_id,
            session_id=model.session_id,
            memory_type=mtype,
            category=model.category,
            content=model.content or {},
            importance=model.importance,
            access_count=model.access_count,
            last_accessed_at=model.last_accessed_at,
            expires_at=model.expires_at,
            metadata=model.event_metadata or {},
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
