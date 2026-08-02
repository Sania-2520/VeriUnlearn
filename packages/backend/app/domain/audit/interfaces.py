from abc import ABC, abstractmethod
from typing import Optional

from app.domain.audit.entities import AuditChainHead, AuditEvent


class AuditEventRepository(ABC):
    @abstractmethod
    async def create(self, event: AuditEvent) -> AuditEvent: ...

    @abstractmethod
    async def get_by_id(self, event_id: str) -> Optional[AuditEvent]: ...

    @abstractmethod
    async def list_by_tenant(
        self,
        tenant_id: str,
        limit: int = 25,
        offset: int = 0,
        event_type: Optional[str] = None,
        actor_id: Optional[str] = None,
    ) -> tuple[list[AuditEvent], int]: ...

    @abstractmethod
    async def get_chain_head(self, tenant_id: str) -> Optional[AuditChainHead]: ...

    @abstractmethod
    async def update_chain_head_anchor(
        self,
        tenant_id: str,
        merkle_root: str,
        tx_hash: str,
        network: str,
    ) -> None: ...

    @abstractmethod
    async def get_all_tenant_ids(self) -> list[str]: ...
