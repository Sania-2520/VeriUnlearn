from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit.entities import ActorType, AuditChainHead, AuditEvent, EventStatus, EventType
from app.domain.audit.interfaces import AuditEventRepository
from app.infrastructure.database.models import AuditChainHeadModel, AuditEventModel


class SQLAlchemyAuditEventRepository(AuditEventRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, event: AuditEvent) -> AuditEvent:
        model = AuditEventModel(
            id=event.id,
            tenant_id=event.tenant_id,
            event_type=event.event_type.value if isinstance(event.event_type, EventType) else event.event_type,
            event_version=event.event_version,
            actor_id=event.actor_id,
            actor_type=event.actor_type.value if isinstance(event.actor_type, ActorType) else event.actor_type,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            action=event.action,
            status=event.status.value if isinstance(event.status, EventStatus) else event.status,
            event_metadata=event.metadata,
            changes=event.changes,
            ip_address=event.ip_address,
            user_agent=event.user_agent,
            session_id=event.session_id,
            request_id=event.request_id,
            previous_event_hash=event.previous_event_hash,
            event_hash=event.event_hash,
            timestamp=event.timestamp.replace(tzinfo=timezone.utc) if event.timestamp and not event.timestamp.tzinfo else event.timestamp,
        )
        self._session.add(model)

        chain = await self._get_chain_head_for_update(event.tenant_id)
        if chain:
            chain.last_event_hash = event.event_hash
            chain.chain_length = (chain.chain_length or 0) + 1
            chain.updated_at = datetime.now(timezone.utc)
        else:
            chain_model = AuditChainHeadModel(
                id=event.tenant_id,
                tenant_id=event.tenant_id,
                last_event_hash=event.event_hash,
                chain_length=1,
            )
            self._session.add(chain_model)

        return event

    async def get_by_id(self, event_id: str) -> Optional[AuditEvent]:
        result = await self._session.execute(
            select(AuditEventModel).where(AuditEventModel.id == event_id)
        )
        model = result.scalar_one_or_none()
        return self._model_to_entity(model) if model else None

    async def list_by_tenant(
        self,
        tenant_id: str,
        limit: int = 25,
        offset: int = 0,
        event_type: Optional[str] = None,
        actor_id: Optional[str] = None,
        resource_type: Optional[str] = None,
    ) -> tuple[list[AuditEvent], int]:
        query = select(AuditEventModel).where(AuditEventModel.tenant_id == tenant_id)
        count_query = select(func.count(AuditEventModel.id)).where(AuditEventModel.tenant_id == tenant_id)

        if event_type:
            query = query.where(AuditEventModel.event_type == event_type)
            count_query = count_query.where(AuditEventModel.event_type == event_type)
        if actor_id:
            query = query.where(AuditEventModel.actor_id == actor_id)
            count_query = count_query.where(AuditEventModel.actor_id == actor_id)
        if resource_type:
            query = query.where(AuditEventModel.resource_type == resource_type)
            count_query = count_query.where(AuditEventModel.resource_type == resource_type)

        count_result = await self._session.execute(count_query)
        total = count_result.scalar() or 0

        query = query.order_by(desc(AuditEventModel.timestamp)).offset(offset).limit(limit)
        result = await self._session.execute(query)
        models = result.scalars().all()

        return [self._model_to_entity(m) for m in models], total

    async def get_chain_head(self, tenant_id: str) -> Optional[AuditChainHead]:
        result = await self._session.execute(
            select(AuditChainHeadModel).where(AuditChainHeadModel.tenant_id == tenant_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return AuditChainHead(
            id=model.id,
            tenant_id=model.tenant_id,
            last_event_hash=model.last_event_hash,
            chain_length=model.chain_length,
            merkle_root=model.merkle_root,
            blockchain_tx_hash=model.blockchain_tx_hash,
            blockchain_network=model.blockchain_network,
            anchored_at=model.anchored_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def update_chain_head_anchor(
        self,
        tenant_id: str,
        merkle_root: str,
        tx_hash: str,
        network: str,
    ) -> None:
        chain = await self._get_chain_head_for_update(tenant_id)
        if chain:
            chain.merkle_root = merkle_root
            chain.blockchain_tx_hash = tx_hash
            chain.blockchain_network = network
            chain.anchored_at = datetime.now(timezone.utc)
            chain.updated_at = datetime.now(timezone.utc)
        else:
            chain_model = AuditChainHeadModel(
                id=tenant_id,
                tenant_id=tenant_id,
                last_event_hash="",
                chain_length=0,
                merkle_root=merkle_root,
                blockchain_tx_hash=tx_hash,
                blockchain_network=network,
                anchored_at=datetime.now(timezone.utc),
            )
            self._session.add(chain_model)

    async def get_all_tenant_ids(self) -> list[str]:
        result = await self._session.execute(
            select(AuditChainHeadModel.tenant_id)
        )
        return [row[0] for row in result.fetchall()]

    async def _get_chain_head_for_update(self, tenant_id: str) -> Optional[AuditChainHeadModel]:
        result = await self._session.execute(
            select(AuditChainHeadModel).where(AuditChainHeadModel.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    def _model_to_entity(self, model: AuditEventModel) -> AuditEvent:
        return AuditEvent(
            id=model.id,
            tenant_id=model.tenant_id,
            event_type=EventType(model.event_type) if model.event_type else EventType.USER_LOGIN,
            event_version=model.event_version,
            actor_id=model.actor_id,
            actor_type=ActorType(model.actor_type) if model.actor_type else ActorType.USER,
            resource_type=model.resource_type,
            resource_id=model.resource_id,
            action=model.action,
            status=EventStatus(model.status) if model.status else EventStatus.SUCCESS,
            metadata=model.event_metadata or {},
            changes=model.changes,
            ip_address=model.ip_address,
            user_agent=model.user_agent,
            session_id=model.session_id,
            request_id=model.request_id,
            previous_event_hash=model.previous_event_hash,
            event_hash=model.event_hash,
            timestamp=model.timestamp,
        )
