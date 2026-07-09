from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from typing import Optional

from app.api.deps import CurrentUser, DatabaseSession, default_rate_limiter, require_permission
from app.core.rbac import Permission

router = APIRouter(dependencies=[Depends(default_rate_limiter), Depends(require_permission(Permission.CHAT))])


class CreateSessionRequest(BaseModel):
    title: str = "New Chat"
    folder_id: Optional[str] = None
    ai_provider_id: Optional[str] = None
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096


class UpdateSessionRequest(BaseModel):
    title: Optional[str] = None
    is_pinned: Optional[bool] = None
    folder_id: Optional[str] = None


class SendMessageRequest(BaseModel):
    content: str
    parent_id: Optional[str] = None


@router.get("/sessions")
async def list_sessions(
    current_user: CurrentUser,
    session: DatabaseSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    folder_id: Optional[str] = None,
    pinned: Optional[bool] = None,
    search: Optional[str] = None,
):
    return {"data": [], "meta": {"page": page, "page_size": page_size, "total": 0}}


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_session(
    request: CreateSessionRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    return {"session": {"id": "placeholder", "title": request.title}}


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    return {"session": {}, "messages": []}


@router.patch("/sessions/{session_id}")
async def update_session(
    session_id: str,
    request: UpdateSessionRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    return {"message": "Session updated"}


@router.delete("/sessions/{session_id}", status_code=status.HTTP_202_ACCEPTED)
async def delete_session(
    session_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    return {
        "message": "Deletion initiated",
        "unlearning_request_id": "placeholder",
        "estimated_completion": None,
    }


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    return {"message_id": "placeholder"}


@router.post("/sessions/{session_id}/messages/{message_id}/regenerate")
async def regenerate_message(
    session_id: str,
    message_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    return {"message_id": "placeholder"}


@router.post("/sessions/{session_id}/messages/{message_id}/feedback")
async def message_feedback(
    session_id: str,
    message_id: str,
    feedback: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    return {"message": "Feedback recorded"}


@router.get("/sessions/{session_id}/export")
async def export_session(
    session_id: str,
    current_user: CurrentUser,
    format: str = "markdown",
):
    return {"message": f"Export in {format} format - to be implemented"}


@router.post("/sessions/import", status_code=status.HTTP_201_CREATED)
async def import_session(
    current_user: CurrentUser,
    session: DatabaseSession,
):
    return {"session": {}}


@router.get("/folders")
async def list_folders(current_user: CurrentUser, session: DatabaseSession):
    return {"data": []}


@router.post("/folders", status_code=status.HTTP_201_CREATED)
async def create_folder(current_user: CurrentUser, session: DatabaseSession):
    return {"folder": {}}


@router.patch("/folders/{folder_id}")
async def update_folder(folder_id: str, current_user: CurrentUser, session: DatabaseSession):
    return {"folder": {}}


@router.delete("/folders/{folder_id}")
async def delete_folder(folder_id: str, current_user: CurrentUser, session: DatabaseSession):
    return {"message": "Folder deleted"}
