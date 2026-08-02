from datetime import datetime, timezone
from typing import Any, Optional

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.domain.audit.entities import ActorType, EventStatus, EventType
from app.domain.audit.services import AuditService
from app.domain.unlearning.entities import (
    DeletionOperation,
    DeletionQueueItem,
    DeletionResourceType,
    ModelVersion,
    TargetType,
    UnlearningAlgorithm,
    UnlearningJob,
    UnlearningPriority,
    UnlearningRequest,
    UnlearningStatus,
)
from app.domain.unlearning.interfaces import (
    DeletionQueueRepository,
    ModelVersionRepository,
    UnlearningJobRepository,
    UnlearningRequestRepository,
)
from app.infrastructure.external.ml_engine import MLEngineClientError, ml_engine_client

logger = get_logger(__name__)


class UnlearningService:
    def __init__(
        self,
        request_repo: UnlearningRequestRepository,
        job_repo: UnlearningJobRepository,
        deletion_queue_repo: DeletionQueueRepository,
        model_version_repo: ModelVersionRepository,
        audit_service: AuditService,
    ) -> None:
        self._request_repo = request_repo
        self._job_repo = job_repo
        self._deletion_queue_repo = deletion_queue_repo
        self._model_version_repo = model_version_repo
        self._audit = audit_service

    async def create_request(
        self,
        tenant_id: str,
        requested_by: str,
        target_type: TargetType,
        target_id: str,
        reason: Optional[str] = None,
        gdpr_article: Optional[str] = None,
        priority: UnlearningPriority = UnlearningPriority.NORMAL,
        algorithm: UnlearningAlgorithm = UnlearningAlgorithm.HYBRID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> tuple[UnlearningRequest, Optional[UnlearningJob]]:
        request = UnlearningRequest(
            tenant_id=tenant_id,
            requested_by=requested_by,
            target_type=target_type,
            target_id=target_id,
            reason=reason,
            gdpr_article=gdpr_article,
            priority=priority,
            status=UnlearningStatus.QUEUED,
        )
        request = await self._request_repo.create(request)

        job = UnlearningJob(
            request_id=request.id,
            algorithm=algorithm,
            status=UnlearningStatus.PROCESSING,
            started_at=datetime.now(timezone.utc),
        )
        job = await self._job_repo.create(job)

        try:
            result = await ml_engine_client.execute_unlearning(
                target_data_ids=[target_id],
                model_type=target_type.value,
                model_name=settings.ml_default_llm,
                data_size=1,
                regulatory="gdpr",
            )

            job.progress = 1.0
            job.status = UnlearningStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            job.results = result
            job.processing_time_ms = result.get("processing_time_ms")
            await self._job_repo.update(job)

            request.status = UnlearningStatus.COMPLETED
            await self._request_repo.update(request)

            deletion_steps = result.get("deletion_steps", [])
            for step in deletion_steps:
                queue_item = DeletionQueueItem(
                    tenant_id=tenant_id,
                    job_id=job.id,
                    resource_type=DeletionResourceType(step.get("resource_type", "postgres")),
                    resource_id=step.get("resource_id", target_id),
                    operation=DeletionOperation(step.get("operation", "delete")),
                    priority=0,
                    status=UnlearningStatus.COMPLETED,
                    completed_at=datetime.now(timezone.utc),
                )
                await self._deletion_queue_repo.create(queue_item)

        except MLEngineClientError as e:
            job.status = UnlearningStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            await self._job_repo.update(job)
            request.status = UnlearningStatus.FAILED
            await self._request_repo.update(request)

        await self._audit.record(
            tenant_id=tenant_id,
            event_type=EventType.UNLEARNING_REQUESTED,
            actor_id=requested_by,
            actor_type=ActorType.USER,
            action="unlearning.request.created",
            status=EventStatus.SUCCESS,
            resource_type="unlearning_request",
            resource_id=request.id,
            metadata={
                "target_type": target_type.value,
                "target_id": target_id,
                "priority": priority.value,
                "algorithm": algorithm.value,
                "status": request.status.value,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        logger.info("Unlearning request created: %s (target: %s)", request.id, target_id)
        return request, job

    async def get_request(
        self, tenant_id: str, request_id: str
    ) -> UnlearningRequest:
        request = await self._request_repo.get_by_id(request_id)
        if not request or request.tenant_id != tenant_id:
            raise NotFoundError("Unlearning request not found")
        return request

    async def list_requests(
        self,
        tenant_id: str,
        page: int = 1,
        page_size: int = 25,
        status: Optional[str] = None,
        target_type: Optional[str] = None,
    ) -> tuple[list[UnlearningRequest], int]:
        return await self._request_repo.list_by_tenant(
            tenant_id, page, page_size, status, target_type
        )

    async def retry_request(
        self,
        tenant_id: str,
        request_id: str,
        requested_by: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> UnlearningJob:
        request = await self._request_repo.get_by_id(request_id)
        if not request or request.tenant_id != tenant_id:
            raise NotFoundError("Unlearning request not found")
        if request.status not in (UnlearningStatus.FAILED,):
            raise ConflictError("Only failed requests can be retried")

        request.status = UnlearningStatus.QUEUED
        await self._request_repo.update(request)

        job = UnlearningJob(
            request_id=request.id,
            algorithm=UnlearningAlgorithm.HYBRID,
            status=UnlearningStatus.PROCESSING,
            started_at=datetime.now(timezone.utc),
        )
        job = await self._job_repo.create(job)

        await self._audit.record(
            tenant_id=tenant_id,
            event_type=EventType.UNLEARNING_REQUESTED,
            actor_id=requested_by,
            actor_type=ActorType.USER,
            action="unlearning.request.retried",
            status=EventStatus.SUCCESS,
            resource_type="unlearning_request",
            resource_id=request.id,
            metadata={"status": "queued"},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        logger.info("Unlearning request retried: %s", request.id)
        return job

    async def get_job(
        self, job_id: str
    ) -> UnlearningJob:
        job = await self._job_repo.get_by_id(job_id)
        if not job:
            raise NotFoundError("Unlearning job not found")
        return job

    async def get_queue_status(
        self, tenant_id: str
    ) -> dict[str, Any]:
        pending = await self._deletion_queue_repo.count_by_status(tenant_id, "pending")
        processing = await self._deletion_queue_repo.count_by_status(tenant_id, "processing")
        completed = await self._deletion_queue_repo.count_by_status(tenant_id, "completed")
        failed = await self._deletion_queue_repo.count_by_status(tenant_id, "failed")

        return {
            "pending": pending,
            "processing": processing,
            "completed_today": completed,
            "failed": failed,
            "average_processing_time_ms": 0,
        }

    async def create_model_version(
        self,
        tenant_id: str,
        name: str,
        algorithm: Optional[str] = None,
        config: Optional[dict[str, Any]] = None,
        shard_count: int = 1,
    ) -> ModelVersion:
        latest = await self._model_version_repo.get_latest(tenant_id, name)
        next_version = (latest.version + 1) if latest else 1

        version = ModelVersion(
            tenant_id=tenant_id,
            name=name,
            version=next_version,
            parent_version_id=latest.id if latest else None,
            algorithm=algorithm,
            config=config or {},
            shard_count=shard_count,
        )
        version = await self._model_version_repo.create(version)
        logger.info("Model version created: %s v%d", name, next_version)
        return version

    async def get_model_version(self, version_id: str) -> ModelVersion:
        version = await self._model_version_repo.get_by_id(version_id)
        if not version:
            raise NotFoundError("Model version not found")
        return version
