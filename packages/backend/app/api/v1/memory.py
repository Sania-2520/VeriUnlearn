from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from typing import Optional

from app.api.deps import CurrentUser, DatabaseSession, default_rate_limiter, require_permission
from app.core.rbac import Permission

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


@router.get("")
async def list_memory(
    current_user: CurrentUser,
    session: DatabaseSession,
    memory_type: Optional[str] = Query(None, alias="type"),
    category: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    return {"data": [], "meta": {"page": page, "page_size": page_size, "total": 0}}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_memory(
    request: CreateMemoryRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    return {"memory": {}}


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    return {"message": "Memory deleted"}


@router.delete("/clear", status_code=status.HTTP_202_ACCEPTED)
async def clear_memory(
    request: ClearMemoryRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    return {"message": "Memory clear initiated"}


@router.patch("/config")
async def update_memory_config(
    request: MemoryConfigRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    return {"config": request}
