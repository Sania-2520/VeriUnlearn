from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, DatabaseSession, default_rate_limiter, require_permission
from app.core.logging import get_logger
from app.core.rbac import Permission

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(default_rate_limiter), Depends(require_permission(Permission.MEMORY))])

_memory_store: dict[str, dict] = {}
_memory_config: dict[str, dict] = {}


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


@router.get("")
async def list_memory(
    current_user: CurrentUser,
    session: DatabaseSession,
    memory_type: Optional[str] = Query(None, alias="type"),
    category: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    user_id = current_user["user_id"]
    tenant_id = current_user["tenant_id"]
    user_memories = [
        m for m in _memory_store.values()
        if m["user_id"] == user_id and m["tenant_id"] == tenant_id
    ]
    if memory_type:
        user_memories = [m for m in user_memories if m.get("type") == memory_type]
    if category:
        user_memories = [m for m in user_memories if m.get("category") == category]
    user_memories.sort(key=lambda m: m.get("created_at", ""), reverse=True)
    total = len(user_memories)
    start = (page - 1) * page_size
    end = start + page_size
    return {"data": user_memories[start:end], "meta": {"page": page, "page_size": page_size, "total": total}}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_memory(
    request: CreateMemoryRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    user_id = current_user["user_id"]
    tenant_id = current_user["tenant_id"]
    memory_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    config = _memory_config.get(tenant_id, {})
    max_entries = config.get("max_entries", 1000)
    tenant_memories = [
        m for m in _memory_store.values()
        if m["tenant_id"] == tenant_id
    ]
    if len(tenant_memories) >= max_entries:
        tenant_memories.sort(key=lambda m: m.get("importance", 0))
        oldest = tenant_memories[0]
        del _memory_store[oldest["id"]]
    memory_data = {
        "id": memory_id,
        "type": request.type,
        "category": request.category,
        "content": request.content,
        "importance": request.importance,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "created_at": now,
        "updated_at": now,
    }
    _memory_store[memory_id] = memory_data
    logger.info("Created memory %s (type=%s, category=%s) for user %s", memory_id, request.type, request.category, user_id)
    return {"memory": memory_data}


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    memory = _memory_store.get(memory_id)
    if not memory or memory["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    del _memory_store[memory_id]
    logger.info("Deleted memory %s for user %s", memory_id, current_user["user_id"])
    return {"message": "Memory deleted"}


@router.delete("/clear", status_code=status.HTTP_202_ACCEPTED)
async def clear_memory(
    request: ClearMemoryRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    user_id = current_user["user_id"]
    tenant_id = current_user["tenant_id"]
    cleared_count = 0
    to_delete = []
    for memory_id, memory in _memory_store.items():
        if (
            memory["user_id"] == user_id
            and memory["tenant_id"] == tenant_id
            and memory.get("type") in request.types
        ):
            to_delete.append(memory_id)
    for memory_id in to_delete:
        del _memory_store[memory_id]
        cleared_count += 1
    logger.info("Cleared %d memory entries (types=%s) for user %s", cleared_count, request.types, user_id)
    return {"message": "Memory clear initiated", "cleared_count": cleared_count}


@router.patch("/config")
async def update_memory_config(
    request: MemoryConfigRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    tenant_id = current_user["tenant_id"]
    config = {
        "persistent_memory_enabled": request.persistent_memory_enabled,
        "retention_days": request.retention_days,
        "max_entries": request.max_entries,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": current_user["user_id"],
    }
    _memory_config[tenant_id] = config
    return {"config": config}
