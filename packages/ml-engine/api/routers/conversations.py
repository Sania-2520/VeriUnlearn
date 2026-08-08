"""Conversational learning endpoints."""

from fastapi import APIRouter, HTTPException

from api import deps
from api.schemas import ConversationRecordRequest

router = APIRouter()


@router.post("/conversations/record")
async def record_conversation(request: ConversationRecordRequest):
    from training.conversational_pipeline import Conversation

    pipeline = deps.get_conversational_pipeline()
    conversation = Conversation(
        user_id=request.user_id,
        tenant_id=request.tenant_id,
        turns=request.turns,
        feedback=request.feedback,
    )
    result = pipeline.record_conversation(conversation)
    return result


@router.post("/conversations/record/turn")
async def record_turn(request: ConversationRecordRequest):
    pipeline = deps.get_conversational_pipeline()
    if not request.turns:
        raise HTTPException(status_code=400, detail="turns list cannot be empty")
    turn = request.turns[-1]
    result = pipeline.record_turn(
        user_id=request.user_id,
        tenant_id=request.tenant_id,
        turn=turn,
    )
    return result


@router.post("/conversations/feedback")
async def submit_feedback(request: ConversationRecordRequest):
    pipeline = deps.get_conversational_pipeline()
    if request.feedback is None:
        raise HTTPException(status_code=400, detail="feedback cannot be None")
    result = pipeline.submit_feedback(
        user_id=request.user_id,
        tenant_id=request.tenant_id,
        feedback=request.feedback,
    )
    return result


@router.get("/conversations/stats")
async def conversation_stats():
    pipeline = deps.get_conversational_pipeline()
    return pipeline.get_stats()


@router.post("/conversations/train")
async def train_from_conversations():
    pipeline = deps.get_conversational_pipeline()
    result = pipeline.trigger_training()
    return result
