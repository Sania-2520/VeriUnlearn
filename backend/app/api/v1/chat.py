from __future__ import annotations


from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.dependencies import DatabaseDep, CurrentUser
from app.schemas.chat import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    MessageResponse,
    ChatRequest,
    ChatResponse,
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(body: ConversationCreate, user: CurrentUser, db: DatabaseDep):
    service = ChatService(db)
    conv = await service.create_conversation(user, title=body.title)
    return conv


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(user: CurrentUser, db: DatabaseDep):
    service = ChatService(db)
    return await service.get_conversations(user)


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def rename_conversation(conversation_id: int, body: ConversationUpdate, user: CurrentUser, db: DatabaseDep):
    service = ChatService(db)
    try:
        conv = await service.rename_conversation(conversation_id, user, body.title)
        return conv
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation_id: int, user: CurrentUser, db: DatabaseDep):
    service = ChatService(db)
    try:
        await service.delete_conversation(conversation_id, user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(conversation_id: int, user: CurrentUser, db: DatabaseDep):
    service = ChatService(db)
    try:
        messages = await service.get_messages(conversation_id, user)
        return messages
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: int,
    body: ChatRequest,
    user: CurrentUser,
    db: DatabaseDep,
):
    service = ChatService(db)
    if body.stream:
        return StreamingResponse(
            service.send_message_stream(conversation_id, user, body.message),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    try:
        result = await service.send_message(conversation_id, user, body.message, stream=False)
        msg = result["message"]
        return ChatResponse(
            message_id=msg.id,
            role=msg.role,
            content=msg.content,
            tokens=msg.tokens,
            model_version=result["model_version"] or settings.base_model_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
