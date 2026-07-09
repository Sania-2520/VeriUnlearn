import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class EventType(str, Enum):
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_CREATED = "user.created"
    USER_DELETED = "user.deleted"
    CHAT_CREATED = "chat.created"
    CHAT_DELETED = "chat.deleted"
    MESSAGE_CREATED = "message.created"
    MESSAGE_DELETED = "message.deleted"
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_DELETED = "document.deleted"
    UNLEARNING_REQUESTED = "unlearning.requested"
    UNLEARNING_STARTED = "unlearning.started"
    UNLEARNING_COMPLETED = "unlearning.completed"
    UNLEARNING_FAILED = "unlearning.failed"
    PROOF_GENERATED = "proof.generated"
    PROOF_VERIFIED = "proof.verified"
    CERTIFICATE_ISSUED = "certificate.issued"
    SECURITY_ASSESSMENT = "security.assessment"
    COMPLIANCE_REPORT = "compliance.report"
    SETTINGS_CHANGED = "settings.changed"
    ROLE_CHANGED = "role.changed"
    RATE_LIMITED = "rate.limited"


class ActorType(str, Enum):
    USER = "user"
    SYSTEM = "system"
    API_KEY = "api_key"
    ADMIN = "admin"


class EventStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"


@dataclass
class AuditEvent:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    event_type: EventType = EventType.USER_LOGIN
    event_version: str = "1.0"
    actor_id: Optional[str] = None
    actor_type: ActorType = ActorType.USER
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action: str = ""
    status: EventStatus = EventStatus.SUCCESS
    metadata: dict = field(default_factory=dict)
    changes: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    merkle_node_hash: Optional[str] = None
    previous_event_hash: Optional[str] = None
    event_hash: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AuditChainHead:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    last_event_hash: str = ""
    chain_length: int = 0
    merkle_root: Optional[str] = None
    blockchain_tx_hash: Optional[str] = None
    blockchain_network: Optional[str] = None
    anchored_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
