from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, MemoryServiceDep, default_rate_limiter, require_permission
from app.core.logging import get_logger
from app.core.rbac import Permission
from app.domain.memory.entities import MemoryEntry

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(default_rate_limiter), Depends(require_permission(Permission.MEMORY))])


class CreateMemoryRequest(BaseModel):
    type: str = "persistent"
    category: str = "fact"
    content: dict = {}
    importance: float = 0.8


class ClearMemoryRequest(BaseModel):
    types: list[str] = ["session", "conversation", "persistent"]


class MemoryConfigRequest(BaseModel):
    persistent_memory_enabled: bool = True
    retention_days: int = 90
    max_entries: int = 1000


def _entry_to_dict(e: MemoryEntry) -> dict:
    return {
        "id": e.id,
        "user_id": e.user_id,
        "tenant_id": e.tenant_id,
        "session_id": e.session_id,
        "type": e.memory_type.value if hasattr(e.memory_type, "value") else e.memory_type,
        "category": e.category,
        "content": e.content,
        "importance": e.importance,
        "access_count": e.access_count,
        "last_accessed_at": e.last_accessed_at.isoformat() if e.last_accessed_at else None,
        "expires_at": e.expires_at.isoformat() if e.expires_at else None,
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "updated_at": e.updated_at.isoformat() if e.updated_at else None,
    }


@router.get("")
async def list_memory(
    current_user: CurrentUser,
    memory_service: MemoryServiceDep,
    memory_type: Optional[str] = Query(None, alias="type"),
    category: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    entries, total = await memory_service.list_entries(
        user_id=current_user["user_id"],
        tenant_id=current_user["tenant_id"],
        memory_type=memory_type, category=category,
        page=page, page_size=page_size,
    )
    return {"data": [_entry_to_dict(e) for e in entries], "meta": {"page": page, "page_size": page_size, "total": total}}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_memory(
    request: CreateMemoryRequest,
    current_user: CurrentUser,
    memory_service: MemoryServiceDep,
):
    entry = await memory_service.create_entry(
        user_id=current_user["user_id"],
        tenant_id=current_user["tenant_id"],
        memory_type=request.type,
        category=request.category,
        content=request.content,
        importance=request.importance,
    )
    return {"entry": _entry_to_dict(entry)}


@router.get("/{entry_id}")
async def get_memory(
    entry_id: str,
    current_user: CurrentUser,
    memory_service: MemoryServiceDep,
):
    entry = await memory_service.get_entry(entry_id, current_user["tenant_id"])
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory entry not found")
    return _entry_to_dict(entry)


@router.delete("/{entry_id}")
async def delete_memory(
    entry_id: str,
    current_user: CurrentUser,
    memory_service: MemoryServiceDep,
):
    deleted = await memory_service.delete_entry(entry_id, current_user["tenant_id"])
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory entry not found")
    return {"message": "Memory entry deleted"}


@router.post("/clear", status_code=status.HTTP_202_ACCEPTED)
async def clear_memory(
    request: ClearMemoryRequest,
    current_user: CurrentUser,
    memory_service: MemoryServiceDep,
):
    count = await memory_service.clear_memory(
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        types=request.types,
    )
    return {"message": "Memory cleared", "entries_deleted": count}


@router.get("/config")
async def get_memory_config(
    current_user: CurrentUser,
    memory_service: MemoryServiceDep,
):
    config = await memory_service.get_config(current_user["tenant_id"])
    return config


@router.put("/config")
async def update_memory_config(
    request: MemoryConfigRequest,
    current_user: CurrentUser,
    memory_service: MemoryServiceDep,
):
    config = await memory_service.update_config(
        current_user["tenant_id"],
        request.model_dump(),
    )
    return config
