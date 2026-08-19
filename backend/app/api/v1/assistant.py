"""Chat assistant API — server-side proxy to an OpenAI-compatible LLM."""
from __future__ import annotations

import json
from typing import Annotated, AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser
from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError
from app.services.assistant import AssistantService

router = APIRouter(prefix="/assistant", tags=["assistant"])


class ChatRequest(BaseModel):
    messages: list[dict] = Field(..., description="Chat history as [{role, content}, …]")


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@router.get("/status")
async def assistant_status(user: CurrentUser) -> dict:
    return {
        "configured": bool(settings.LLM_BASE_URL),
        "model": settings.LLM_MODEL,
    }


@router.post("/chat")
async def assistant_chat(
    user: CurrentUser,
    body: ChatRequest,
) -> StreamingResponse:
    """Proxy a chat conversation to the configured LLM and stream the reply as SSE.

    Client sends ``[{"role": "user", "content": "..."}, ...]``; the server streams
    ``data: {...}`` deltas and finishes with ``data: [DONE]``.
    """

    async def event_stream() -> AsyncIterator[str]:
        try:
            service = AssistantService()
        except ServiceUnavailableError as exc:
            yield _sse({"error": exc.message})
            yield "data: [DONE]\n\n"
            return

        try:
            async for chunk in service.stream_chat(body.messages):
                yield _sse({"chunk": chunk})
        except ServiceUnavailableError as exc:
            yield _sse({"error": exc.message})
        except Exception as exc:  # noqa: BLE001 - surface any proxy failure to the client
            yield _sse({"error": f"Assistant error: {type(exc).__name__}"})
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")