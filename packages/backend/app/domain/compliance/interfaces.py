from abc import ABC, abstractmethod
from typing import Optional

from app.domain.compliance.entities import Webhook, WebhookEventLog


class WebhookRepository(ABC):
    @abstractmethod
    async def create(self, webhook: Webhook) -> Webhook:
        ...

    @abstractmethod
    async def get_by_id(self, webhook_id: str) -> Optional[Webhook]:
        ...

    @abstractmethod
    async def list_by_tenant(self, tenant_id: str) -> list[Webhook]:
        ...

    @abstractmethod
    async def update(self, webhook: Webhook) -> Webhook:
        ...

    @abstractmethod
    async def delete(self, webhook_id: str) -> None:
        ...


class WebhookEventLogRepository(ABC):
    @abstractmethod
    async def create(self, log: WebhookEventLog) -> WebhookEventLog:
        ...

    @abstractmethod
    async def get_by_id(self, log_id: str) -> Optional[WebhookEventLog]:
        ...

    @abstractmethod
    async def list_by_webhook(
        self, webhook_id: str, page: int = 1, page_size: int = 25
    ) -> tuple[list[WebhookEventLog], int]:
        ...

    @abstractmethod
    async def update(self, log: WebhookEventLog) -> WebhookEventLog:
        ...

    @abstractmethod
    async def get_pending_retries(self, max_attempts: int = 3) -> list[WebhookEventLog]:
        ...
