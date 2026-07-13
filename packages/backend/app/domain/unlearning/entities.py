import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class UnlearningStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFIED = "verified"


class UnlearningPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class UnlearningAlgorithm(str, Enum):
    SISA = "sisa"
    INFLUENCE_FUNCTION = "influence_function"
    CERTIFIED_REMOVAL = "certified_removal"
    APPROXIMATE = "approximate"
    HYBRID = "hybrid"


class TargetType(str, Enum):
    CONVERSATION = "conversation"
    MESSAGE = "message"
    DOCUMENT = "document"
    EMBEDDING = "embedding"
    MEMORY = "memory"
    USER_DATA = "user_data"


class DeletionResourceType(str, Enum):
    POSTGRES = "postgres"
    REDIS = "redis"
    QDRANT = "qdrant"
    MINIO = "minio"
    CACHE = "cache"
    MEMORY = "memory"
    MODEL = "model"


class DeletionOperation(str, Enum):
    DELETE = "delete"
    NULLIFY = "nullify"
    FORGET = "forget"
    PRUNE = "prune"


@dataclass
class UnlearningRequest:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    requested_by: str = ""
    target_type: TargetType = TargetType.CONVERSATION
    target_id: str = ""
    reason: Optional[str] = None
    gdpr_article: Optional[str] = None
    status: UnlearningStatus = UnlearningStatus.PENDING
    priority: UnlearningPriority = UnlearningPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class UnlearningJob:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = ""
    algorithm: UnlearningAlgorithm = UnlearningAlgorithm.HYBRID
    model_id: Optional[str] = None
    status: UnlearningStatus = UnlearningStatus.PENDING
    progress: float = 0.0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_time_ms: Optional[int] = None
    results: Optional[dict] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DeletionQueueItem:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    job_id: Optional[str] = None
    resource_type: DeletionResourceType = DeletionResourceType.POSTGRES
    resource_id: str = ""
    operation: DeletionOperation = DeletionOperation.DELETE
    priority: int = 0
    status: UnlearningStatus = UnlearningStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    locked_until: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ModelVersion:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    name: str = ""
    version: int = 1
    parent_version_id: Optional[str] = None
    algorithm: Optional[str] = None
    checkpoint_path: Optional[str] = None
    model_weights_hash: Optional[str] = None
    metrics: dict = field(default_factory=dict)
    config: dict = field(default_factory=dict)
    status: str = "active"
    is_unlearned: bool = False
    shard_count: int = 1
    total_data_points: int = 0
    removed_data_points: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ModelShard:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    model_version_id: str = ""
    shard_index: int = 0
    checkpoint_path: Optional[str] = None
    data_range: dict = field(default_factory=dict)
    data_point_count: int = 0
    metrics: dict = field(default_factory=dict)
    status: str = "active"
    created_at: datetime = field(default_factory=datetime.utcnow)
