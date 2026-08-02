import hashlib
import json
from typing import Any, Optional

from app.core.logging import get_logger
from app.domain.audit.entities import (
    ActorType,
    AuditEvent,
    EventStatus,
    EventType,
)
from app.domain.audit.interfaces import AuditEventRepository

logger = get_logger(__name__)


def _compute_event_hash(event: AuditEvent) -> str:
    data = {
        "id": event.id,
        "tenant_id": event.tenant_id,
        "event_type": event.event_type.value,
        "actor_id": event.actor_id,
        "actor_type": event.actor_type.value,
        "resource_type": event.resource_type,
        "resource_id": event.resource_id,
        "action": event.action,
        "status": event.status.value,
        "metadata": event.metadata,
        "ip_address": event.ip_address,
        "previous_event_hash": event.previous_event_hash,
        "timestamp": event.timestamp.isoformat() if event.timestamp else None,
    }
    raw = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


class AuditService:
    def __init__(self, repo: AuditEventRepository) -> None:
        self._repo = repo

    async def record(
        self,
        tenant_id: str,
        event_type: EventType,
        actor_id: Optional[str] = None,
        actor_type: ActorType = ActorType.USER,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: str = "",
        status: EventStatus = EventStatus.SUCCESS,
        metadata: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> AuditEvent:
        chain_head = await self._repo.get_chain_head(tenant_id)
        previous_hash = chain_head.last_event_hash if chain_head else None

        event = AuditEvent(
            tenant_id=tenant_id,
            event_type=event_type,
            actor_id=actor_id,
            actor_type=actor_type,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            status=status,
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            request_id=request_id,
            previous_event_hash=previous_hash,
        )

        event.event_hash = _compute_event_hash(event)
        created = await self._repo.create(event)

        logger.info(
            "Audit event: %s | actor=%s | resource=%s/%s | status=%s",
            event_type.value, actor_id, resource_type, resource_id, status.value,
        )
        return created

    async def anchor_chain(
        self,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Compute Merkle root of audit events and anchor it to the blockchain."""
        from app.infrastructure.external.blockchain import blockchain_anchor_service

        events, _ = await self._repo.list_by_tenant(tenant_id, limit=100000)
        if not events:
            return {"anchored": False, "reason": "no events to anchor"}

        event_dicts = [
            {
                "id": e.id,
                "event_type": e.event_type.value if hasattr(e.event_type, "value") else e.event_type,
                "actor_id": e.actor_id,
                "action": e.action,
                "status": e.status.value if hasattr(e.status, "value") else e.status,
                "event_hash": e.event_hash,
                "previous_event_hash": e.previous_event_hash,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            }
            for e in events
        ]
        merkle_root = blockchain_anchor_service.compute_merkle_root(event_dicts)

        result = await blockchain_anchor_service.anchor(merkle_root, tenant_id)
        if result.get("anchored"):
            await self._repo.update_chain_head_anchor(
                tenant_id=tenant_id,
                merkle_root=merkle_root,
                tx_hash=result["tx_hash"],
                network=result["network"],
            )

        return result
