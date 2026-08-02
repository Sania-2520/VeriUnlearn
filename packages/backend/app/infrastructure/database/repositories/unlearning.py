from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import desc, func, select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.unlearning.entities import (
    DeletionOperation,
    DeletionResourceType,
    TargetType,
    UnlearningAlgorithm,
    UnlearningPriority,
    UnlearningStatus,
)
from app.domain.unlearning.entities import (
    DeletionQueueItem as DeletionQueueItemEntity,
)
from app.domain.unlearning.entities import (
    ModelVersion as ModelVersionEntity,
)
from app.domain.unlearning.entities import (
    UnlearningJob as UnlearningJobEntity,
)
from app.domain.unlearning.entities import (
    UnlearningRequest as UnlearningRequestEntity,
)
from app.domain.unlearning.interfaces import (
    DeletionQueueRepository,
    ModelVersionRepository,
    UnlearningJobRepository,
    UnlearningRequestRepository,
)
from app.infrastructure.database.models import (
    DeletionQueueItemModel,
    ModelVersionModel,
    UnlearningJobModel,
    UnlearningRequestModel,
)


class SQLAlchemyUnlearningRequestRepository(UnlearningRequestRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, request: UnlearningRequestEntity) -> UnlearningRequestEntity:
        model = UnlearningRequestModel(
            id=request.id,
            tenant_id=request.tenant_id,
            requested_by=request.requested_by,
            target_type=request.target_type.value if isinstance(request.target_type, TargetType) else request.target_type,
            target_id=request.target_id,
            reason=request.reason,
            gdpr_article=request.gdpr_article,
            status=request.status.value if isinstance(request.status, UnlearningStatus) else request.status,
            priority=request.priority.value if isinstance(request.priority, UnlearningPriority) else request.priority,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def get_by_id(self, request_id: str) -> Optional[UnlearningRequestEntity]:
        result = await self._session.execute(
            select(UnlearningRequestModel).where(UnlearningRequestModel.id == request_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_tenant(
        self, tenant_id: str, page: int, page_size: int,
        status: Optional[str] = None, target_type: Optional[str] = None,
    ) -> tuple[list[UnlearningRequestEntity], int]:
        query = select(UnlearningRequestModel).where(UnlearningRequestModel.tenant_id == tenant_id)
        count_query = select(func.count(UnlearningRequestModel.id)).where(UnlearningRequestModel.tenant_id == tenant_id)

        if status:
            query = query.where(UnlearningRequestModel.status == status)
            count_query = count_query.where(UnlearningRequestModel.status == status)
        if target_type:
            query = query.where(UnlearningRequestModel.target_type == target_type)
            count_query = count_query.where(UnlearningRequestModel.target_type == target_type)

        count_result = await self._session.execute(count_query)
        total = count_result.scalar() or 0

        offset = (page - 1) * page_size
        query = query.order_by(desc(UnlearningRequestModel.created_at)).offset(offset).limit(page_size)
        result = await self._session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(m) for m in models], total

    async def update(self, request: UnlearningRequestEntity) -> UnlearningRequestEntity:
        await self._session.execute(
            sa_update(UnlearningRequestModel)
            .where(UnlearningRequestModel.id == request.id)
            .values(
                status=request.status.value if isinstance(request.status, UnlearningStatus) else request.status,
                priority=request.priority.value if isinstance(request.priority, UnlearningPriority) else request.priority,
                reason=request.reason,
                gdpr_article=request.gdpr_article,
                updated_at=datetime.now(timezone.utc),
            )
        )
        return request

    @staticmethod
    def _to_entity(model: UnlearningRequestModel) -> UnlearningRequestEntity:
        return UnlearningRequestEntity(
            id=model.id,
            tenant_id=model.tenant_id,
            requested_by=model.requested_by,
            target_type=TargetType(model.target_type) if model.target_type else TargetType.CONVERSATION,
            target_id=model.target_id,
            reason=model.reason,
            gdpr_article=model.gdpr_article,
            status=UnlearningStatus(model.status) if model.status else UnlearningStatus.PENDING,
            priority=UnlearningPriority(model.priority) if model.priority else UnlearningPriority.NORMAL,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SQLAlchemyUnlearningJobRepository(UnlearningJobRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, job: UnlearningJobEntity) -> UnlearningJobEntity:
        model = UnlearningJobModel(
            id=job.id,
            request_id=job.request_id,
            algorithm=job.algorithm.value if isinstance(job.algorithm, UnlearningAlgorithm) else job.algorithm,
            model_id=job.model_id,
            status=job.status.value if isinstance(job.status, UnlearningStatus) else job.status,
            progress=job.progress,
            error_message=job.error_message,
            started_at=job.started_at,
            completed_at=job.completed_at,
            processing_time_ms=job.processing_time_ms,
            results=job.results,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def get_by_id(self, job_id: str) -> Optional[UnlearningJobEntity]:
        result = await self._session.execute(
            select(UnlearningJobModel).where(UnlearningJobModel.id == job_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def update(self, job: UnlearningJobEntity) -> UnlearningJobEntity:
        await self._session.execute(
            sa_update(UnlearningJobModel)
            .where(UnlearningJobModel.id == job.id)
            .values(
                status=job.status.value if isinstance(job.status, UnlearningStatus) else job.status,
                progress=job.progress,
                error_message=job.error_message,
                model_id=job.model_id,
                started_at=job.started_at,
                completed_at=job.completed_at,
                processing_time_ms=job.processing_time_ms,
                results=job.results,
            )
        )
        return job

    @staticmethod
    def _to_entity(model: UnlearningJobModel) -> UnlearningJobEntity:
        return UnlearningJobEntity(
            id=model.id,
            request_id=model.request_id,
            algorithm=UnlearningAlgorithm(model.algorithm) if model.algorithm else UnlearningAlgorithm.HYBRID,
            model_id=model.model_id,
            status=UnlearningStatus(model.status) if model.status else UnlearningStatus.PENDING,
            progress=model.progress,
            error_message=model.error_message,
            started_at=model.started_at,
            completed_at=model.completed_at,
            processing_time_ms=model.processing_time_ms,
            results=model.results,
            created_at=model.created_at,
        )


class SQLAlchemyDeletionQueueRepository(DeletionQueueRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, item: DeletionQueueItemEntity) -> DeletionQueueItemEntity:
        model = DeletionQueueItemModel(
            id=item.id,
            tenant_id=item.tenant_id,
            job_id=item.job_id,
            resource_type=item.resource_type.value if isinstance(item.resource_type, DeletionResourceType) else item.resource_type,
            resource_id=item.resource_id,
            operation=item.operation.value if isinstance(item.operation, DeletionOperation) else item.operation,
            priority=item.priority,
            status=item.status.value if isinstance(item.status, UnlearningStatus) else item.status,
            retry_count=item.retry_count,
            max_retries=item.max_retries,
            error_message=item.error_message,
            locked_until=item.locked_until,
            completed_at=item.completed_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def get_next_pending(self) -> Optional[DeletionQueueItemEntity]:
        result = await self._session.execute(
            select(DeletionQueueItemModel)
            .where(DeletionQueueItemModel.status == "pending")
            .order_by(DeletionQueueItemModel.priority.desc(), DeletionQueueItemModel.created_at.asc())
            .limit(1)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def update(self, item: DeletionQueueItemEntity) -> DeletionQueueItemEntity:
        await self._session.execute(
            sa_update(DeletionQueueItemModel)
            .where(DeletionQueueItemModel.id == item.id)
            .values(
                status=item.status.value if isinstance(item.status, UnlearningStatus) else item.status,
                retry_count=item.retry_count,
                error_message=item.error_message,
                locked_until=item.locked_until,
                completed_at=item.completed_at,
            )
        )
        return item

    async def count_by_status(self, tenant_id: str, status: str) -> int:
        result = await self._session.execute(
            select(func.count(DeletionQueueItemModel.id)).where(
                DeletionQueueItemModel.tenant_id == tenant_id,
                DeletionQueueItemModel.status == status,
            )
        )
        return result.scalar() or 0

    @staticmethod
    def _to_entity(model: DeletionQueueItemModel) -> DeletionQueueItemEntity:
        return DeletionQueueItemEntity(
            id=model.id,
            tenant_id=model.tenant_id,
            job_id=model.job_id,
            resource_type=DeletionResourceType(model.resource_type) if model.resource_type else DeletionResourceType.POSTGRES,
            resource_id=model.resource_id,
            operation=DeletionOperation(model.operation) if model.operation else DeletionOperation.DELETE,
            priority=model.priority,
            status=UnlearningStatus(model.status) if model.status else UnlearningStatus.PENDING,
            retry_count=model.retry_count,
            max_retries=model.max_retries,
            error_message=model.error_message,
            locked_until=model.locked_until,
            completed_at=model.completed_at,
            created_at=model.created_at,
        )


class SQLAlchemyModelVersionRepository(ModelVersionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, version: ModelVersionEntity) -> ModelVersionEntity:
        model = ModelVersionModel(
            id=version.id,
            tenant_id=version.tenant_id,
            name=version.name,
            version=version.version,
            parent_version_id=version.parent_version_id,
            algorithm=version.algorithm,
            checkpoint_path=version.checkpoint_path,
            model_weights_hash=version.model_weights_hash,
            metrics=version.metrics,
            config=version.config,
            status=version.status,
            is_unlearned=version.is_unlearned,
            shard_count=version.shard_count,
            total_data_points=version.total_data_points,
            removed_data_points=version.removed_data_points,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def get_by_id(self, version_id: str) -> Optional[ModelVersionEntity]:
        result = await self._session.execute(
            select(ModelVersionModel).where(ModelVersionModel.id == version_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_latest(self, tenant_id: str, name: str) -> Optional[ModelVersionEntity]:
        result = await self._session.execute(
            select(ModelVersionModel)
            .where(
                ModelVersionModel.tenant_id == tenant_id,
                ModelVersionModel.name == name,
            )
            .order_by(desc(ModelVersionModel.version))
            .limit(1)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def update(self, version: ModelVersionEntity) -> ModelVersionEntity:
        await self._session.execute(
            sa_update(ModelVersionModel)
            .where(ModelVersionModel.id == version.id)
            .values(
                status=version.status,
                is_unlearned=version.is_unlearned,
                checkpoint_path=version.checkpoint_path,
                model_weights_hash=version.model_weights_hash,
                metrics=version.metrics,
                total_data_points=version.total_data_points,
                removed_data_points=version.removed_data_points,
            )
        )
        return version

    @staticmethod
    def _to_entity(model: ModelVersionModel) -> ModelVersionEntity:
        return ModelVersionEntity(
            id=model.id,
            tenant_id=model.tenant_id,
            name=model.name,
            version=model.version,
            parent_version_id=model.parent_version_id,
            algorithm=model.algorithm,
            checkpoint_path=model.checkpoint_path,
            model_weights_hash=model.model_weights_hash,
            metrics=model.metrics or {},
            config=model.config or {},
            status=model.status or "active",
            is_unlearned=model.is_unlearned,
            shard_count=model.shard_count,
            total_data_points=model.total_data_points,
            removed_data_points=model.removed_data_points,
            created_at=model.created_at,
        )
