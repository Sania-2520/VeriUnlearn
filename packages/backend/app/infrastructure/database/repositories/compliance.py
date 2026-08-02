from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, desc, func, select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.compliance.entities import (
    DeliveryStatus,
    WebhookStatus,
)
from app.domain.compliance.entities import (
    Webhook as WebhookEntity,
)
from app.domain.compliance.entities import (
    WebhookEventLog as WebhookEventLogEntity,
)
from app.domain.compliance.interfaces import WebhookEventLogRepository, WebhookRepository
from app.infrastructure.database.models import WebhookEventLogModel, WebhookModel


class SQLAlchemyWebhookRepository(WebhookRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, webhook: WebhookEntity) -> WebhookEntity:
        model = WebhookModel(
            id=webhook.id,
            tenant_id=webhook.tenant_id,
            name=webhook.name,
            url=webhook.url,
            secret=webhook.secret,
            events=webhook.events,
            is_active=webhook.is_active,
            status=webhook.status.value if isinstance(webhook.status, WebhookStatus) else webhook.status,
            headers=webhook.headers,
            retry_count=webhook.retry_count,
            timeout_ms=webhook.timeout_ms,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def get_by_id(self, webhook_id: str) -> Optional[WebhookEntity]:
        result = await self._session.execute(
            select(WebhookModel).where(WebhookModel.id == webhook_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_tenant(self, tenant_id: str) -> list[WebhookEntity]:
        result = await self._session.execute(
            select(WebhookModel)
            .where(WebhookModel.tenant_id == tenant_id)
            .order_by(desc(WebhookModel.created_at))
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def update(self, webhook: WebhookEntity) -> WebhookEntity:
        await self._session.execute(
            sa_update(WebhookModel)
            .where(WebhookModel.id == webhook.id)
            .values(
                name=webhook.name,
                url=webhook.url,
                secret=webhook.secret,
                events=webhook.events,
                is_active=webhook.is_active,
                status=webhook.status.value if isinstance(webhook.status, WebhookStatus) else webhook.status,
                headers=webhook.headers,
                retry_count=webhook.retry_count,
                timeout_ms=webhook.timeout_ms,
                last_success_at=webhook.last_success_at,
                last_failure_at=webhook.last_failure_at,
                consecutive_failures=webhook.consecutive_failures,
            )
        )
        return webhook

    async def delete(self, webhook_id: str) -> None:
        await self._session.execute(
            sa_update(WebhookModel)
            .where(WebhookModel.id == webhook_id)
            .values(is_active=False, status=WebhookStatus.DISABLED.value)
        )

    @staticmethod
    def _to_entity(model: WebhookModel) -> WebhookEntity:
        return WebhookEntity(
            id=model.id,
            tenant_id=model.tenant_id,
            name=model.name,
            url=model.url,
            secret=model.secret,
            events=model.events or [],
            is_active=model.is_active,
            status=WebhookStatus(model.status) if model.status else WebhookStatus.ACTIVE,
            headers=model.headers or {},
            retry_count=model.retry_count,
            timeout_ms=model.timeout_ms,
            last_success_at=model.last_success_at,
            last_failure_at=model.last_failure_at,
            consecutive_failures=model.consecutive_failures,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SQLAlchemyWebhookEventLogRepository(WebhookEventLogRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, log: WebhookEventLogEntity) -> WebhookEventLogEntity:
        model = WebhookEventLogModel(
            id=log.id,
            webhook_id=log.webhook_id,
            event_type=log.event_type,
            payload=log.payload,
            status=log.status.value if isinstance(log.status, DeliveryStatus) else log.status,
            response_code=log.response_code,
            response_body=log.response_body,
            error_message=log.error_message,
            attempt_count=log.attempt_count,
            max_attempts=log.max_attempts,
            next_retry_at=log.next_retry_at,
            completed_at=log.completed_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def get_by_id(self, log_id: str) -> Optional[WebhookEventLogEntity]:
        result = await self._session.execute(
            select(WebhookEventLogModel).where(WebhookEventLogModel.id == log_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_webhook(
        self, webhook_id: str, page: int = 1, page_size: int = 25
    ) -> tuple[list[WebhookEventLogEntity], int]:
        query = select(WebhookEventLogModel).where(WebhookEventLogModel.webhook_id == webhook_id)
        count_query = select(func.count(WebhookEventLogModel.id)).where(WebhookEventLogModel.webhook_id == webhook_id)

        count_result = await self._session.execute(count_query)
        total = count_result.scalar() or 0

        offset = (page - 1) * page_size
        query = query.order_by(desc(WebhookEventLogModel.created_at)).offset(offset).limit(page_size)
        result = await self._session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(m) for m in models], total

    async def update(self, log: WebhookEventLogEntity) -> WebhookEventLogEntity:
        await self._session.execute(
            sa_update(WebhookEventLogModel)
            .where(WebhookEventLogModel.id == log.id)
            .values(
                status=log.status.value if isinstance(log.status, DeliveryStatus) else log.status,
                response_code=log.response_code,
                response_body=log.response_body,
                error_message=log.error_message,
                attempt_count=log.attempt_count,
                next_retry_at=log.next_retry_at,
                completed_at=log.completed_at,
            )
        )
        return log

    async def get_pending_retries(self, max_attempts: int = 3) -> list[WebhookEventLogEntity]:
        now = datetime.now(timezone.utc)
        result = await self._session.execute(
            select(WebhookEventLogModel)
            .where(
                and_(
                    WebhookEventLogModel.status.in_(["pending", "retrying"]),
                    WebhookEventLogModel.attempt_count < WebhookEventLogModel.max_attempts,
                    WebhookEventLogModel.next_retry_at <= now,
                )
            )
            .order_by(WebhookEventLogModel.next_retry_at.asc())
            .limit(50)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    @staticmethod
    def _to_entity(model: WebhookEventLogModel) -> WebhookEventLogEntity:
        return WebhookEventLogEntity(
            id=model.id,
            webhook_id=model.webhook_id,
            event_type=model.event_type,
            payload=model.payload or {},
            status=DeliveryStatus(model.status) if model.status else DeliveryStatus.PENDING,
            response_code=model.response_code,
            response_body=model.response_body,
            error_message=model.error_message,
            attempt_count=model.attempt_count,
            max_attempts=model.max_attempts,
            next_retry_at=model.next_retry_at,
            completed_at=model.completed_at,
            created_at=model.created_at,
        )
