from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any
from urllib.parse import urlparse

import httpx
from loguru import logger
from pydantic import BaseModel


class WebhookConfig(BaseModel):
    url: str
    secret: str | None = None
    events: list[str] = ["training.completed", "training.failed", "unlearning.completed"]
    enabled: bool = True


class WebhookPayload(BaseModel):
    event: str
    timestamp: float
    data: dict[str, Any]


class WebhookService:
    def __init__(self) -> None:
        self._webhooks: list[WebhookConfig] = []
        self._delivery_log: list[dict] = []

    def register(self, config: WebhookConfig) -> None:
        if not self._is_valid_url(config.url):
            raise ValueError(f"Invalid webhook URL: {config.url}")
        self._webhooks.append(config)
        logger.info(f"Webhook registered: {config.url}")

    def unregister(self, url: str) -> bool:
        before = len(self._webhooks)
        self._webhooks = [w for w in self._webhooks if w.url != url]
        return len(self._webhooks) < before

    def get_webhooks(self) -> list[WebhookConfig]:
        return list(self._webhooks)

    async def dispatch(self, event: str, data: dict[str, Any]) -> list[dict]:
        results = []
        payload = WebhookPayload(
            event=event,
            timestamp=time.time(),
            data=data,
        )

        for webhook in self._webhooks:
            if not webhook.enabled:
                continue
            if event not in webhook.events and "*" not in webhook.events:
                continue

            result = await self._deliver(webhook, payload)
            results.append(result)

        return results

    async def _deliver(self, webhook: WebhookConfig, payload: WebhookPayload) -> dict:
        body = payload.model_dump_json()
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Event": payload.event,
            "X-Webhook-Timestamp": str(int(payload.timestamp)),
        }

        if webhook.secret:
            signature = hmac.new(
                webhook.secret.encode(),
                body.encode(),
                hashlib.sha256,
            ).hexdigest()
            headers["X-Webhook-Signature"] = f"sha256={signature}"

        delivery = {
            "url": webhook.url,
            "event": payload.event,
            "timestamp": payload.timestamp,
            "status": "pending",
            "response_code": None,
            "error": None,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    webhook.url,
                    content=body,
                    headers=headers,
                )
                delivery["response_code"] = response.status_code
                delivery["status"] = "delivered" if response.status_code < 400 else "failed"
        except Exception as e:
            delivery["status"] = "failed"
            delivery["error"] = str(e)
            logger.warning(f"Webhook delivery failed: {webhook.url} - {e}")

        self._delivery_log.append(delivery)
        if len(self._delivery_log) > 1000:
            self._delivery_log = self._delivery_log[-500:]

        return delivery

    def get_delivery_log(self, limit: int = 50) -> list[dict]:
        return list(reversed(self._delivery_log[-limit:]))

    def verify_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        expected = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", signature)

    def _is_valid_url(self, url: str) -> bool:
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False


webhook_service = WebhookService()
