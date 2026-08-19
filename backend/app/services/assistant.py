"""Chat assistant — proxies an OpenAI-compatible chat/completions endpoint.

The provider (OpenAI, Groq, OpenRouter, vLLM, …) is configured via
``LLM_BASE_URL`` / ``LLM_API_KEY`` / ``LLM_MODEL`` and consumed through a
server-side streaming proxy so the API key never reaches the browser.
"""
from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError


class AssistantService:
    def __init__(self) -> None:
        if not settings.LLM_BASE_URL:
            raise ServiceUnavailableError(
                "LLM is not configured. Set LLM_BASE_URL, LLM_API_KEY and LLM_MODEL "
                "in backend/.env and restart the API."
            )
        self.base_url = settings.LLM_BASE_URL.rstrip("/")
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL

    async def stream_chat(self, messages: list[dict]) -> AsyncIterator[str]:
        """Yield raw ``data:`` payloads from the provider's SSE stream."""
        url = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": settings.LLM_TEMPERATURE,
            "max_tokens": settings.LLM_MAX_TOKENS,
        }
        timeout = httpx.Timeout(settings.LLM_TIMEOUT_SECONDS, read=settings.LLM_TIMEOUT_SECONDS)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    detail = body.decode("utf-8", "replace")[:500]
                    raise ServiceUnavailableError(
                        f"LLM provider error ({resp.status_code}): {detail}"
                    )
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[len("data: "):].strip()
                    if data == "[DONE]":
                        break
                    try:
                        json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    yield data