import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class MemoryType(str, Enum):
    SESSION = "session"
    CONVERSATION = "conversation"
    PERSISTENT = "persistent"
    USER = "user"
    WORKSPACE = "workspace"


class MemoryCategory(str, Enum):
    FACT = "fact"
    PREFERENCE = "preference"
    CONTEXT = "context"
    SUMMARY = "summary"
    ENTITY = "entity"


@dataclass
class MemoryEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    memory_type: MemoryType = MemoryType.PERSISTENT
    category: Optional[str] = None
    content: dict = field(default_factory=dict)
    importance: float = 1.0
    access_count: int = 0
    last_accessed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
