from abc import ABC, abstractmethod
from typing import Optional

from app.domain.unlearning.entities import (
    DeletionQueueItem,
    ModelVersion,
    UnlearningJob,
    UnlearningRequest,
)


class UnlearningRequestRepository(ABC):
    @abstractmethod
    async def create(self, request: UnlearningRequest) -> UnlearningRequest:
        ...

    @abstractmethod
    async def get_by_id(self, request_id: str) -> Optional[UnlearningRequest]:
        ...

    @abstractmethod
    async def list_by_tenant(
        self, tenant_id: str, page: int, page_size: int,
        status: Optional[str] = None, target_type: Optional[str] = None,
    ) -> tuple[list[UnlearningRequest], int]:
        ...

    @abstractmethod
    async def update(self, request: UnlearningRequest) -> UnlearningRequest:
        ...


class UnlearningJobRepository(ABC):
    @abstractmethod
    async def create(self, job: UnlearningJob) -> UnlearningJob:
        ...

    @abstractmethod
    async def get_by_id(self, job_id: str) -> Optional[UnlearningJob]:
        ...

    @abstractmethod
    async def update(self, job: UnlearningJob) -> UnlearningJob:
        ...


class DeletionQueueRepository(ABC):
    @abstractmethod
    async def create(self, item: DeletionQueueItem) -> DeletionQueueItem:
        ...

    @abstractmethod
    async def get_next_pending(self) -> Optional[DeletionQueueItem]:
        ...

    @abstractmethod
    async def update(self, item: DeletionQueueItem) -> DeletionQueueItem:
        ...

    @abstractmethod
    async def count_by_status(self, tenant_id: str, status: str) -> int:
        ...


class ModelVersionRepository(ABC):
    @abstractmethod
    async def create(self, version: ModelVersion) -> ModelVersion:
        ...

    @abstractmethod
    async def get_by_id(self, version_id: str) -> Optional[ModelVersion]:
        ...

    @abstractmethod
    async def get_latest(self, tenant_id: str, name: str) -> Optional[ModelVersion]:
        ...

    @abstractmethod
    async def update(self, version: ModelVersion) -> ModelVersion:
        ...
