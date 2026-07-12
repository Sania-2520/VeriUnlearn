from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, DatabaseSession, default_rate_limiter, require_permission
from app.core.logging import get_logger
from app.core.rbac import Permission
from app.infrastructure.external.ml_engine import ml_engine_client, MLEngineClientError

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(default_rate_limiter), Depends(require_permission(Permission.CHAT))])

_sessions: dict[str, dict] = {}
_messages: dict[str, dict[str, dict]] = {}
_folders: dict[str, dict] = {}


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
    user_sessions = [
        s for s in _sessions.values()
        if s["user_id"] == current_user["user_id"] and s["tenant_id"] == current_user["tenant_id"]
    ]
    if folder_id:
        user_sessions = [s for s in user_sessions if s.get("folder_id") == folder_id]
    if pinned is not None:
        user_sessions = [s for s in user_sessions if s.get("is_pinned") == pinned]
    if search:
        user_sessions = [s for s in user_sessions if search.lower() in s.get("title", "").lower()]
    user_sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
    total = len(user_sessions)
    start = (page - 1) * page_size
    end = start + page_size
    return {"data": user_sessions[start:end], "meta": {"page": page, "page_size": page_size, "total": total}}


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_session(
    request: CreateSessionRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    session_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    session_data = {
        "id": session_id,
        "title": request.title,
        "folder_id": request.folder_id,
        "ai_provider_id": request.ai_provider_id,
        "model": request.model,
        "system_prompt": request.system_prompt,
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
        "is_pinned": False,
        "user_id": current_user["user_id"],
        "tenant_id": current_user["tenant_id"],
        "message_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    _sessions[session_id] = session_data
    _messages[session_id] = {}
    return {"session": session_data}


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    session_data = _sessions.get(session_id)
    if not session_data or session_data["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    session_messages = list(_messages.get(session_id, {}).values())
    session_messages.sort(key=lambda m: m.get("created_at", ""))
    return {"session": session_data, "messages": session_messages}


@router.patch("/sessions/{session_id}")
async def update_session(
    session_id: str,
    request: UpdateSessionRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    session_data = _sessions.get(session_id)
    if not session_data or session_data["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if request.title is not None:
        session_data["title"] = request.title
    if request.is_pinned is not None:
        session_data["is_pinned"] = request.is_pinned
    if request.folder_id is not None:
        session_data["folder_id"] = request.folder_id
    session_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    return {"message": "Session updated"}


@router.delete("/sessions/{session_id}", status_code=status.HTTP_202_ACCEPTED)
async def delete_session(
    session_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    session_data = _sessions.get(session_id)
    if not session_data or session_data["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    messages = list(_messages.get(session_id, {}).values())
    user_turns = []
    for msg in messages:
        user_turns.append({"role": "user", "content": msg.get("content", "")})
        if msg.get("assistant_content"):
            user_turns.append({"role": "assistant", "content": msg["assistant_content"]})
    if user_turns:
        try:
            await ml_engine_client.record_conversation(
                user_id=current_user["user_id"],
                tenant_id=current_user["tenant_id"],
                turns=user_turns,
                feedback={"action": "session_deleted", "session_id": session_id},
            )
        except MLEngineClientError:
            logger.warning("Failed to record conversation before deletion for session %s", session_id)
    del _sessions[session_id]
    _messages.pop(session_id, None)
    return {
        "message": "Deletion initiated",
        "unlearning_request_id": None,
        "estimated_completion": None,
    }


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    session_data = _sessions.get(session_id)
    if not session_data or session_data["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session_id not in _messages:
        _messages[session_id] = {}
    now = datetime.now(timezone.utc).isoformat()
    user_msg_id = str(uuid4())
    user_message = {
        "id": user_msg_id,
        "session_id": session_id,
        "role": "user",
        "content": request.content,
        "parent_id": request.parent_id,
        "created_at": now,
    }
    _messages[session_id][user_msg_id] = user_message
    assistant_msg_id = str(uuid4())
    try:
        ml_response = await ml_engine_client.generate_text(
            prompt=request.content,
            max_new_tokens=session_data.get("max_tokens", 4096),
            temperature=session_data.get("temperature", 0.7),
            stream=False,
            adapter_name=None,
            system_prompt=session_data.get("system_prompt"),
        )
        assistant_content = ml_response.get("text", ml_response.get("generated_text", ml_response.get("output", "")))
        metadata = ml_response
    except MLEngineClientError as e:
        logger.error("ML engine inference failed for session %s: %s", session_id, str(e))
        assistant_content = f"Error: ML engine request failed - {str(e)}"
        metadata = {"error": str(e)}
    assistant_message = {
        "id": assistant_msg_id,
        "session_id": session_id,
        "role": "assistant",
        "content": assistant_content,
        "parent_id": user_msg_id,
        "metadata": metadata,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _messages[session_id][assistant_msg_id] = assistant_message
    session_data["message_count"] = session_data.get("message_count", 0) + 2
    session_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    try:
        await ml_engine_client.record_conversation(
            user_id=current_user["user_id"],
            tenant_id=current_user["tenant_id"],
            turns=[
                {"role": "user", "content": request.content},
                {"role": "assistant", "content": assistant_content},
            ],
        )
    except MLEngineClientError:
        logger.warning("Failed to record conversation turn for session %s", session_id)
    return {"message_id": assistant_msg_id}


@router.post("/sessions/{session_id}/messages/{message_id}/regenerate")
async def regenerate_message(
    session_id: str,
    message_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    session_data = _sessions.get(session_id)
    if not session_data or session_data["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    session_messages = _messages.get(session_id, {})
    target_msg = session_messages.get(message_id)
    if not target_msg or target_msg.get("role") != "assistant":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found or not an assistant message")
    parent_id = target_msg.get("parent_id")
    parent_msg = session_messages.get(parent_id) if parent_id else None
    prompt = parent_msg["content"] if parent_msg else target_msg.get("content", "")
    try:
        ml_response = await ml_engine_client.generate_text(
            prompt=prompt,
            max_new_tokens=session_data.get("max_tokens", 4096),
            temperature=session_data.get("temperature", 0.7),
            stream=False,
            adapter_name=None,
            system_prompt=session_data.get("system_prompt"),
        )
        new_content = ml_response.get("text", ml_response.get("generated_text", ml_response.get("output", "")))
    except MLEngineClientError as e:
        logger.error("ML engine regeneration failed for session %s: %s", session_id, str(e))
        new_content = f"Error: ML engine request failed - {str(e)}"
    target_msg["content"] = new_content
    target_msg["regenerated"] = True
    target_msg["updated_at"] = datetime.now(timezone.utc).isoformat()
    session_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    return {"message_id": message_id}


@router.post("/sessions/{session_id}/messages/{message_id}/feedback")
async def message_feedback(
    session_id: str,
    message_id: str,
    feedback: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    session_messages = _messages.get(session_id, {})
    target_msg = session_messages.get(message_id)
    if not target_msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    target_msg["feedback"] = feedback
    target_msg["feedback_at"] = datetime.now(timezone.utc).isoformat()
    try:
        await ml_engine_client.record_conversation(
            user_id=current_user["user_id"],
            tenant_id=current_user["tenant_id"],
            turns=[{"role": "assistant", "content": target_msg.get("content", ""), "message_id": message_id}],
            feedback={"rating": feedback, "message_id": message_id},
        )
    except MLEngineClientError:
        logger.warning("Failed to record feedback for message %s", message_id)
    return {"message": "Feedback recorded"}


@router.get("/sessions/{session_id}/export")
async def export_session(
    session_id: str,
    current_user: CurrentUser,
    format: str = "markdown",
):
    session_data = _sessions.get(session_id)
    if not session_data or session_data["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    session_messages = list(_messages.get(session_id, {}).values())
    session_messages.sort(key=lambda m: m.get("created_at", ""))
    if format == "markdown":
        lines = [f"# {session_data.get('title', 'Chat Session')}", ""]
        for msg in session_messages:
            role = msg.get("role", "unknown").capitalize()
            lines.append(f"**{role}:** {msg.get('content', '')}")
            lines.append("")
        export_content = "\n".join(lines)
    elif format == "json":
        import json
        export_content = json.dumps({"session": session_data, "messages": session_messages}, indent=2, default=str)
    else:
        export_content = str({"session": session_data, "messages": session_messages})
    return {"content": export_content, "format": format}


@router.post("/sessions/import", status_code=status.HTTP_201_CREATED)
async def import_session(
    current_user: CurrentUser,
    session: DatabaseSession,
):
    session_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    session_data = {
        "id": session_id,
        "title": "Imported Session",
        "user_id": current_user["user_id"],
        "tenant_id": current_user["tenant_id"],
        "is_pinned": False,
        "message_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    _sessions[session_id] = session_data
    _messages[session_id] = {}
    return {"session": session_data}


@router.get("/folders")
async def list_folders(current_user: CurrentUser, session: DatabaseSession):
    user_folders = [
        f for f in _folders.values()
        if f["user_id"] == current_user["user_id"] and f["tenant_id"] == current_user["tenant_id"]
    ]
    return {"data": user_folders}


@router.post("/folders", status_code=status.HTTP_201_CREATED)
async def create_folder(current_user: CurrentUser, session: DatabaseSession):
    folder_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    folder_data = {
        "id": folder_id,
        "name": "New Folder",
        "user_id": current_user["user_id"],
        "tenant_id": current_user["tenant_id"],
        "created_at": now,
        "updated_at": now,
    }
    _folders[folder_id] = folder_data
    return {"folder": folder_data}


@router.patch("/folders/{folder_id}")
async def update_folder(folder_id: str, current_user: CurrentUser, session: DatabaseSession):
    folder_data = _folders.get(folder_id)
    if not folder_data or folder_data["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    folder_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    return {"folder": folder_data}


@router.delete("/folders/{folder_id}")
async def delete_folder(folder_id: str, current_user: CurrentUser, session: DatabaseSession):
    folder_data = _folders.get(folder_id)
    if not folder_data or folder_data["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    del _folders[folder_id]
    return {"message": "Folder deleted"}
