import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from app.core.config import settings
from app.core.exceptions import NotFoundError, ConflictError
from app.core.logging import get_logger
from app.domain.auth.entities import Tenant
from app.domain.auth.interfaces import TenantRepository
from app.domain.compliance.entities import (
    TenantSettings,
    Webhook,
    WebhookEventLog,
    WebhookStatus,
    WebhookEventType,
    DeliveryStatus,
)
from app.domain.compliance.interfaces import WebhookRepository, WebhookEventLogRepository
from app.domain.audit.entities import EventType, ActorType, EventStatus
from app.domain.audit.services import AuditService

logger = get_logger(__name__)


DEFAULT_SETTINGS = TenantSettings()


class TenantService:
    def __init__(
        self,
        tenant_repo: TenantRepository,
        webhook_repo: WebhookRepository,
        webhook_log_repo: WebhookEventLogRepository,
        audit_service: AuditService,
    ) -> None:
        self._tenant_repo = tenant_repo
        self._webhook_repo = webhook_repo
        self._webhook_log_repo = webhook_log_repo
        self._audit = audit_service

    # ─── Settings ────────────────────────────────────────────

    async def get_settings(self, tenant_id: str) -> TenantSettings:
        tenant = await self._tenant_repo.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundError("Tenant not found")
        return self._dict_to_settings(tenant.settings)

    async def update_settings(
        self,
        tenant_id: str,
        settings_data: dict[str, Any],
        actor_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TenantSettings:
        tenant = await self._tenant_repo.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundError("Tenant not found")

        current = self._dict_to_settings(tenant.settings)
        for key, value in settings_data.items():
            if hasattr(current, key):
                setattr(current, key, value)

        tenant.settings = self._settings_to_dict(current)
        await self._tenant_repo.update(tenant)

        await self._audit.record(
            tenant_id=tenant_id,
            event_type=EventType.SETTINGS_CHANGED,
            actor_id=actor_id or "system",
            actor_type=ActorType.USER if actor_id else ActorType.SYSTEM,
            action="compliance.settings.updated",
            status=EventStatus.SUCCESS,
            resource_type="tenant_settings",
            resource_id=tenant_id,
            metadata={"updated_fields": list(settings_data.keys())},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        logger.info("Tenant settings updated: %s", tenant_id)
        return current

    # ─── Webhooks ────────────────────────────────────────────

    async def create_webhook(
        self,
        tenant_id: str,
        name: str,
        url: str,
        events: list[str],
        secret: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
        retry_count: int = 3,
        timeout_ms: int = 5000,
        actor_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Webhook:
        webhook = Webhook(
            tenant_id=tenant_id,
            name=name,
            url=url,
            secret=secret or secrets.token_hex(32),
            events=events,
            headers=headers or {},
            retry_count=retry_count,
            timeout_ms=timeout_ms,
        )
        webhook = await self._webhook_repo.create(webhook)

        await self._audit.record(
            tenant_id=tenant_id,
            event_type=EventType.SETTINGS_CHANGED,
            actor_id=actor_id or "system",
            actor_type=ActorType.USER if actor_id else ActorType.SYSTEM,
            action="compliance.webhook.created",
            status=EventStatus.SUCCESS,
            resource_type="webhook",
            resource_id=webhook.id,
            metadata={"name": name, "url": url, "events": events},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        logger.info("Webhook created: %s (%s)", webhook.id, name)
        return webhook

    async def list_webhooks(self, tenant_id: str) -> list[Webhook]:
        return await self._webhook_repo.list_by_tenant(tenant_id)

    async def get_webhook(self, tenant_id: str, webhook_id: str) -> Webhook:
        webhook = await self._webhook_repo.get_by_id(webhook_id)
        if not webhook or webhook.tenant_id != tenant_id:
            raise NotFoundError("Webhook not found")
        return webhook

    async def update_webhook(
        self,
        tenant_id: str,
        webhook_id: str,
        name: Optional[str] = None,
        url: Optional[str] = None,
        events: Optional[list[str]] = None,
        is_active: Optional[bool] = None,
        headers: Optional[dict[str, str]] = None,
        retry_count: Optional[int] = None,
        timeout_ms: Optional[int] = None,
        actor_id: Optional[str] = None,
    ) -> Webhook:
        webhook = await self.get_webhook(tenant_id, webhook_id)

        if name is not None:
            webhook.name = name
        if url is not None:
            webhook.url = url
        if events is not None:
            webhook.events = events
        if is_active is not None:
            webhook.is_active = is_active
            webhook.status = WebhookStatus.ACTIVE if is_active else WebhookStatus.INACTIVE
        if headers is not None:
            webhook.headers = headers
        if retry_count is not None:
            webhook.retry_count = retry_count
        if timeout_ms is not None:
            webhook.timeout_ms = timeout_ms

        webhook.updated_at = datetime.now(timezone.utc)
        webhook = await self._webhook_repo.update(webhook)

        logger.info("Webhook updated: %s", webhook.id)
        return webhook

    async def delete_webhook(
        self,
        tenant_id: str,
        webhook_id: str,
        actor_id: Optional[str] = None,
    ) -> None:
        webhook = await self.get_webhook(tenant_id, webhook_id)
        await self._webhook_repo.delete(webhook.id)

        await self._audit.record(
            tenant_id=tenant_id,
            event_type=EventType.SETTINGS_CHANGED,
            actor_id=actor_id or "system",
            actor_type=ActorType.USER if actor_id else ActorType.SYSTEM,
            action="compliance.webhook.deleted",
            status=EventStatus.SUCCESS,
            resource_type="webhook",
            resource_id=webhook_id,
            metadata={"name": webhook.name},
        )

        logger.info("Webhook deleted: %s", webhook.id)

    async def test_webhook(
        self, tenant_id: str, webhook_id: str
    ) -> dict[str, Any]:
        webhook = await self.get_webhook(tenant_id, webhook_id)

        payload = {
            "event": "webhook.test",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {"message": "Test webhook from VeriUnlearn"},
        }

        status_code, response_body = await self._send_webhook(webhook, payload)

        return {
            "status_code": status_code,
            "response": response_body,
            "success": 200 <= (status_code or 0) < 300,
        }

    async def get_webhook_logs(
        self, tenant_id: str, webhook_id: str, page: int = 1, page_size: int = 25
    ) -> tuple[list[WebhookEventLog], int]:
        webhook = await self.get_webhook(tenant_id, webhook_id)
        return await self._webhook_log_repo.list_by_webhook(webhook.id, page, page_size)

    # ─── Webhook Dispatch ────────────────────────────────────

    async def dispatch_event(
        self,
        tenant_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> list[WebhookEventLog]:
        webhooks = await self._webhook_repo.list_by_tenant(tenant_id)
        matching = [w for w in webhooks if w.is_active and event_type in w.events]

        logs: list[WebhookEventLog] = []
        for webhook in matching:
            log = WebhookEventLog(
                webhook_id=webhook.id,
                event_type=event_type,
                payload=payload,
                max_attempts=webhook.retry_count,
            )
            log = await self._webhook_log_repo.create(log)
            logs.append(log)

            status_code, response_body = await self._send_webhook(webhook, payload)
            log.attempt_count = 1
            log.response_code = status_code
            log.response_body = response_body

            if status_code and 200 <= status_code < 300:
                log.status = DeliveryStatus.DELIVERED
                log.completed_at = datetime.now(timezone.utc)
                webhook.last_success_at = datetime.now(timezone.utc)
                webhook.consecutive_failures = 0
            else:
                log.status = DeliveryStatus.FAILED
                log.error_message = f"HTTP {status_code}: {response_body}" if status_code else "Connection failed"
                webhook.last_failure_at = datetime.now(timezone.utc)
                webhook.consecutive_failures += 1
                if webhook.consecutive_failures >= 5:
                    webhook.status = WebhookStatus.FAILING

            await self._webhook_log_repo.update(log)
            await self._webhook_repo.update(webhook)

        return logs

    # ─── Internal ────────────────────────────────────────────

    @staticmethod
    def _dict_to_settings(data: dict[str, Any]) -> TenantSettings:
        settings_obj = TenantSettings()
        for key, value in data.items():
            if hasattr(settings_obj, key):
                setattr(settings_obj, key, value)
        return settings_obj

    @staticmethod
    def _settings_to_dict(settings_obj: TenantSettings) -> dict[str, Any]:
        return {
            "timezone": settings_obj.timezone,
            "date_format": settings_obj.date_format,
            "notification_email": settings_obj.notification_email,
            "gdpr_contact_email": settings_obj.gdpr_contact_email,
            "data_retention_days": settings_obj.data_retention_days,
            "max_failed_login_attempts": settings_obj.max_failed_login_attempts,
            "session_timeout_minutes": settings_obj.session_timeout_minutes,
            "mfa_enforced": settings_obj.mfa_enforced,
            "audit_retention_days": settings_obj.audit_retention_days,
            "webhook_retry_max_attempts": settings_obj.webhook_retry_max_attempts,
            "webhook_retry_delay_seconds": settings_obj.webhook_retry_delay_seconds,
            "webhook_timeout_ms": settings_obj.webhook_timeout_ms,
            "allowed_ip_ranges": settings_obj.allowed_ip_ranges,
            "custom_branding": settings_obj.custom_branding,
        }

    @staticmethod
    def _sign_payload(payload: dict[str, Any], secret: str) -> str:
        body = json.dumps(payload, separators=(",", ":")).encode()
        return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    async def _send_webhook(
        self, webhook: Webhook, payload: dict[str, Any]
    ) -> tuple[Optional[int], Optional[str]]:
        signature = self._sign_payload(payload, webhook.secret)
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-Event": payload.get("event", "unknown"),
            "User-Agent": "VeriUnlearn-Webhook/1.0",
            **webhook.headers,
        }

        try:
            async with httpx.AsyncClient(timeout=webhook.timeout_ms / 1000) as client:
                resp = await client.post(webhook.url, json=payload, headers=headers)
                return resp.status_code, resp.text[:2000]
        except httpx.TimeoutException:
            return None, "Request timed out"
        except httpx.RequestError as e:
            return None, str(e)[:2000]
