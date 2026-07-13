import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class WebhookStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILING = "failing"
    DISABLED = "disabled"


class WebhookEventType(str, Enum):
    UNLEARNING_COMPLETED = "unlearning.completed"
    UNLEARNING_FAILED = "unlearning.failed"
    PROOF_GENERATED = "proof.generated"
    PROOF_VERIFIED = "proof.verified"
    USER_CREATED = "user.created"
    USER_DELETED = "user.deleted"


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class TenantSettings:
    timezone: str = "UTC"
    date_format: str = "YYYY-MM-DD"
    notification_email: Optional[str] = None
    gdpr_contact_email: Optional[str] = None
    data_retention_days: int = 365
    max_failed_login_attempts: int = 5
    session_timeout_minutes: int = 60
    mfa_enforced: bool = False
    audit_retention_days: int = 3650
    webhook_retry_max_attempts: int = 3
    webhook_retry_delay_seconds: int = 60
    webhook_timeout_ms: int = 5000
    allowed_ip_ranges: list[str] = field(default_factory=list)
    custom_branding: dict = field(default_factory=dict)


@dataclass
class Webhook:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    name: str = ""
    url: str = ""
    secret: str = ""
    events: list[str] = field(default_factory=list)
    is_active: bool = True
    status: WebhookStatus = WebhookStatus.ACTIVE
    headers: dict = field(default_factory=dict)
    retry_count: int = 3
    timeout_ms: int = 5000
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    consecutive_failures: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WebhookEventLog:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    webhook_id: str = ""
    event_type: str = ""
    payload: dict = field(default_factory=dict)
    status: DeliveryStatus = DeliveryStatus.PENDING
    response_code: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    attempt_count: int = 0
    max_attempts: int = 3
    next_retry_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
