"""Chat assistant API — server-side proxy to an OpenAI-compatible LLM."""
from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser
from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError, ValidationFailedError
from app.services.assistant import AssistantService
from app.services.chat_history import ChatHistoryService

router = APIRouter(prefix="/assistant", tags=["assistant"])


class ChatRequest(BaseModel):
    messages: list[dict] = Field(..., description="Chat history as [{role, content}, …]")
    session_id: str | None = Field(default=None, description="Existing chat session to append to")


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _extract_content(chunk: str) -> str:
    try:
        data = json.loads(chunk)
    except json.JSONDecodeError:
        return ""
    return data.get("choices", [{}])[0].get("delta", {}).get("content", "") or ""


@router.get("/status")
async def assistant_status(user: CurrentUser) -> dict:
    return {
        "configured": bool(settings.LLM_BASE_URL),
        "model": settings.LLM_MODEL,
    }


@router.get("/sessions")
async def list_sessions(
    user: CurrentUser,
    limit: int = Query(default=200, ge=1, le=500),
    search: str | None = Query(default=None, description="Filter by chat id / name / content"),
    from_ts: str | None = Query(default=None, alias="from", description="ISO datetime lower bound"),
    to_ts: str | None = Query(default=None, alias="to", description="ISO datetime upper bound"),
) -> dict:
    """List the current user's chat sessions (newest first) for the audit trail.

    Supports surgical-unlearning lookup by chat id and by date/time range via
    the ``search``, ``from`` and ``to`` query parameters.
    """
    from datetime import datetime, timezone

    def _parse(ts: str | None) -> datetime | None:
        if not ts:
            return None
        try:
            parsed = datetime.fromisoformat(ts)
        except ValueError:
            raise ValidationFailedError(f"Invalid datetime: {ts}")
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed

    sessions = await ChatHistoryService().list_sessions(
        user["sub"],
        limit=limit,
        search=search,
        from_ts=_parse(from_ts),
        to_ts=_parse(to_ts),
    )
    return {"sessions": sessions}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, user: CurrentUser) -> dict:
    """Return a single chat session belonging to the current user."""
    session = await ChatHistoryService().get_session(user["sub"], session_id)
    if session is None:
        raise ValidationFailedError(f"Chat session {session_id} not found")
    return {"session": session}


@router.post("/chat")
async def assistant_chat(
    user: CurrentUser,
    body: ChatRequest,
) -> StreamingResponse:
    """Proxy a chat conversation to the configured LLM and stream the reply as SSE.

    The conversation is persisted to the chat audit trail as it streams; the
    server streams ``data: {...}`` deltas and finishes with ``data: [DONE]``.
    """

    async def event_stream() -> AsyncIterator[str]:
        try:
            service = AssistantService()
        except ServiceUnavailableError as exc:
            yield _sse({"error": exc.message})
            yield "data: [DONE]\n\n"
            return

        assistant_text = ""
        try:
            async for chunk in service.stream_chat(body.messages):
                assistant_text += _extract_content(chunk)
                yield _sse({"chunk": chunk})
        except ServiceUnavailableError as exc:
            yield _sse({"error": exc.message})
        except Exception as exc:  # noqa: BLE001 - surface any proxy failure to the client
            yield _sse({"error": f"Assistant error: {type(exc).__name__}"})
        finally:
            yield "data: [DONE]\n\n"
            if assistant_text:
                await ChatHistoryService().persist(
                    user_id=user["sub"],
                    session_id=body.session_id,
                    messages=body.messages,
                    assistant_text=assistant_text,
                )

    return StreamingResponse(event_stream(), media_type="text/event-stream")