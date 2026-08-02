from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import (
    ChatServiceDep,
    CurrentUser,
    default_rate_limiter,
    require_permission,
)
from app.core.logging import get_logger
from app.core.rbac import Permission
from app.domain.chat.entities import ChatSession, Message
from app.infrastructure.external.ml_engine import MLEngineClientError, ml_engine_client

logger = get_logger(__name__)

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


def _session_to_dict(s: ChatSession) -> dict:
    return {
        "id": s.id,
        "user_id": s.user_id,
        "tenant_id": s.tenant_id,
        "title": s.title,
        "folder_id": s.folder_id,
        "ai_provider_id": s.ai_provider_id,
        "model": s.model,
        "system_prompt": s.system_prompt,
        "temperature": s.temperature,
        "max_tokens": s.max_tokens,
        "is_pinned": s.is_pinned,
        "is_archived": s.is_archived,
        "message_count": s.message_count,
        "total_tokens": s.total_tokens,
        "total_cost": s.total_cost,
        "metadata": s.metadata,
        "last_activity_at": s.last_activity_at.isoformat() if s.last_activity_at else None,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


def _message_to_dict(m: "Message") -> dict:
    return {
        "id": m.id,
        "session_id": m.session_id,
        "parent_id": m.parent_id,
        "role": m.role.value if hasattr(m.role, "value") else m.role,
        "content": m.content,
        "content_type": m.content_type.value if hasattr(m.content_type, "value") else m.content_type,
        "metadata": m.metadata,
        "is_streaming": m.is_streaming,
        "is_regenerated": m.is_regenerated,
        "is_edited": m.is_edited,
        "feedback": m.feedback.value if m.feedback and hasattr(m.feedback, "value") else m.feedback,
        "tokens_input": m.tokens_input,
        "tokens_output": m.tokens_output,
        "cost": m.cost,
        "latency_ms": m.latency_ms,
        "model_used": m.model_used,
        "provider_used": m.provider_used,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


@router.get("/sessions")
async def list_sessions(
    current_user: CurrentUser,
    chat_service: ChatServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    folder_id: Optional[str] = None,
    pinned: Optional[bool] = None,
    search: Optional[str] = None,
):
    sessions, total = await chat_service.list_sessions(
        user_id=current_user["user_id"],
        tenant_id=current_user["tenant_id"],
        page=page, page_size=page_size,
        folder_id=folder_id, pinned=pinned, search=search,
    )
    return {"data": [_session_to_dict(s) for s in sessions], "meta": {"page": page, "page_size": page_size, "total": total}}


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_session(
    request: CreateSessionRequest,
    current_user: CurrentUser,
    chat_service: ChatServiceDep,
):
    session = await chat_service.create_session(
        user_id=current_user["user_id"],
        tenant_id=current_user["tenant_id"],
        title=request.title,
        folder_id=request.folder_id,
        ai_provider_id=request.ai_provider_id,
        model=request.model,
        system_prompt=request.system_prompt,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )
    return {"session": _session_to_dict(session)}


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    current_user: CurrentUser,
    chat_service: ChatServiceDep,
):
    session = await chat_service.get_session(session_id, current_user["tenant_id"])
    if not session or session.user_id != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    messages, _ = await chat_service.get_session_messages(session_id)
    return {"session": _session_to_dict(session), "messages": [_message_to_dict(m) for m in messages]}


@router.patch("/sessions/{session_id}")
async def update_session(
    session_id: str,
    request: UpdateSessionRequest,
    current_user: CurrentUser,
    chat_service: ChatServiceDep,
):
    kwargs = {}
    if request.title is not None:
        kwargs["title"] = request.title
    if request.is_pinned is not None:
        kwargs["is_pinned"] = request.is_pinned
    if request.folder_id is not None:
        kwargs["folder_id"] = request.folder_id
    session = await chat_service.update_session(session_id, current_user["tenant_id"], **kwargs)
    if not session or session.user_id != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return {"message": "Session updated"}


@router.delete("/sessions/{session_id}", status_code=status.HTTP_202_ACCEPTED)
async def delete_session(
    session_id: str,
    current_user: CurrentUser,
    chat_service: ChatServiceDep,
):
    session = await chat_service.get_session(session_id, current_user["tenant_id"])
    if not session or session.user_id != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    messages, _ = await chat_service.get_session_messages(session_id)
    user_turns = []
    for msg in messages:
        user_turns.append({"role": "user", "content": msg.content})
        if hasattr(msg, "assistant_content") and msg.assistant_content:
            user_turns.append({"role": "assistant", "content": msg.assistant_content})
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
    await chat_service.delete_session(session_id, current_user["tenant_id"])
    return {"message": "Deletion initiated", "unlearning_request_id": None, "estimated_completion": None}


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    current_user: CurrentUser,
    chat_service: ChatServiceDep,
):
    session = await chat_service.get_session(session_id, current_user["tenant_id"])
    if not session or session.user_id != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    user_msg = await chat_service.send_message(
        session_id=session_id, tenant_id=current_user["tenant_id"],
        content=request.content, parent_id=request.parent_id,
    )
    try:
        ml_response = await ml_engine_client.generate_text(
            prompt=request.content,
            max_new_tokens=session.max_tokens,
            temperature=session.temperature,
            stream=False,
            adapter_name=None,
            system_prompt=session.system_prompt,
        )
        assistant_content = ml_response.get("text", ml_response.get("generated_text", ml_response.get("output", "")))
        metadata = ml_response
    except MLEngineClientError as e:
        logger.error("ML engine inference failed for session %s: %s", session_id, str(e))
        assistant_content = f"Error: ML engine request failed - {str(e)}"
        metadata = {"error": str(e)}
    now = datetime.now(timezone.utc)
    import uuid

    from app.domain.chat.entities import Message, MessageContentType, MessageRole
    assistant_msg_id = str(uuid.uuid4())
    assistant_msg = Message(
        id=assistant_msg_id,
        session_id=session_id,
        parent_id=user_msg.id,
        role=MessageRole.ASSISTANT,
        content=assistant_content,
        content_type=MessageContentType.TEXT,
        metadata=metadata,
        created_at=now,
    )
    await chat_service._message_repo.create(assistant_msg)
    session.message_count += 1
    session.last_activity_at = now
    session.updated_at = now
    await chat_service._session_repo.update(session)
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
    return {"message_id": assistant_msg_id, "content": assistant_content}


@router.post("/sessions/{session_id}/messages/{message_id}/regenerate")
async def regenerate_message(
    session_id: str,
    message_id: str,
    current_user: CurrentUser,
    chat_service: ChatServiceDep,
):
    session = await chat_service.get_session(session_id, current_user["tenant_id"])
    if not session or session.user_id != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    messages, _ = await chat_service.get_session_messages(session_id)
    target_msg = next((m for m in messages if m.id == message_id), None)
    if not target_msg or target_msg.role.value != "assistant":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found or not an assistant message")
    parent_msg = next((m for m in messages if m.id == target_msg.parent_id), None)
    prompt = parent_msg.content if parent_msg else target_msg.content
    try:
        ml_response = await ml_engine_client.generate_text(
            prompt=prompt,
            max_new_tokens=session.max_tokens,
            temperature=session.temperature,
            stream=False,
            adapter_name=None,
            system_prompt=session.system_prompt,
        )
        new_content = ml_response.get("text", ml_response.get("generated_text", ml_response.get("output", "")))
    except MLEngineClientError as e:
        logger.error("ML engine regeneration failed for session %s: %s", session_id, str(e))
        new_content = f"Error: ML engine request failed - {str(e)}"
    target_msg.content = new_content
    target_msg.is_regenerated = True
    return {"message_id": message_id}


@router.post("/sessions/{session_id}/messages/{message_id}/feedback")
async def message_feedback(
    session_id: str,
    message_id: str,
    feedback: str,
    current_user: CurrentUser,
    chat_service: ChatServiceDep,
):
    messages, _ = await chat_service.get_session_messages(session_id)
    target_msg = next((m for m in messages if m.id == message_id), None)
    if not target_msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    from app.domain.chat.entities import FeedbackType
    try:
        target_msg.feedback = FeedbackType(feedback)
    except ValueError:
        target_msg.feedback = None
    try:
        await ml_engine_client.record_conversation(
            user_id=current_user["user_id"],
            tenant_id=current_user["tenant_id"],
            turns=[{"role": "assistant", "content": target_msg.content, "message_id": message_id}],
            feedback={"rating": feedback, "message_id": message_id},
        )
    except MLEngineClientError:
        logger.warning("Failed to record feedback for message %s", message_id)
    return {"message": "Feedback recorded"}


@router.get("/sessions/{session_id}/export")
async def export_session(
    session_id: str,
    current_user: CurrentUser,
    chat_service: ChatServiceDep,
    format: str = "markdown",
):
    session = await chat_service.get_session(session_id, current_user["tenant_id"])
    if not session or session.user_id != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    messages, _ = await chat_service.get_session_messages(session_id)
    if format == "markdown":
        lines = [f"# {session.title}", ""]
        for msg in messages:
            role = msg.role.value.capitalize()
            lines.append(f"**{role}:** {msg.content}")
            lines.append("")
        export_content = "\n".join(lines)
    elif format == "json":
        import json
        export_content = json.dumps(
            {"session": _session_to_dict(session), "messages": [_message_to_dict(m) for m in messages]},
            indent=2, default=str,
        )
    else:
        export_content = str({"session": _session_to_dict(session), "messages": [_message_to_dict(m) for m in messages]})
    return {"content": export_content, "format": format}


@router.get("/folders")
async def list_folders(current_user: CurrentUser, chat_service: ChatServiceDep):
    folders = await chat_service.list_folders(current_user["user_id"], current_user["tenant_id"])
    return {"data": [{"id": f.id, "user_id": f.user_id, "name": f.name, "created_at": f.created_at.isoformat() if f.created_at else None, "updated_at": f.updated_at.isoformat() if f.updated_at else None} for f in folders]}


@router.post("/folders", status_code=status.HTTP_201_CREATED)
async def create_folder(
    name: Optional[str] = None,
    current_user: CurrentUser = ...,
    chat_service: ChatServiceDep = ...,
):
    folder = await chat_service.create_folder(current_user["user_id"], current_user["tenant_id"], name=name or "New Folder")
    return {"folder": {"id": folder.id, "name": folder.name, "created_at": folder.created_at.isoformat() if folder.created_at else None}}


@router.patch("/folders/{folder_id}")
async def update_folder(
    folder_id: str,
    name: Optional[str] = None,
    current_user: CurrentUser = ...,
    chat_service: ChatServiceDep = ...,
):
    kwargs = {}
    if name is not None:
        kwargs["name"] = name
    folder = await chat_service.update_folder(folder_id, current_user["user_id"], **kwargs)
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    return {"folder": {"id": folder.id, "name": folder.name}}


@router.delete("/folders/{folder_id}")
async def delete_folder(folder_id: str, current_user: CurrentUser, chat_service: ChatServiceDep):
    deleted = await chat_service.delete_folder(folder_id, current_user["user_id"])
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    return {"message": "Folder deleted"}
