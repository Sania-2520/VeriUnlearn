import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class MessageContentType(str, Enum):
    TEXT = "text"
    MARKDOWN = "markdown"
    LATEX = "latex"
    CODE = "code"
    IMAGE = "image"
    AUDIO = "audio"


class FeedbackType(str, Enum):
    LIKE = "like"
    DISLIKE = "dislike"


@dataclass
class ChatFolder:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    tenant_id: str = ""
    name: str = ""
    parent_id: Optional[str] = None
    sort_order: int = 0
    is_deleted: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ChatSession:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    tenant_id: str = ""
    title: str = "New Chat"
    folder_id: Optional[str] = None
    ai_provider_id: Optional[str] = None
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    is_pinned: bool = False
    is_archived: bool = False
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    message_count: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    metadata: dict = field(default_factory=dict)
    last_activity_at: datetime = field(default_factory=datetime.utcnow)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Message:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    parent_id: Optional[str] = None
    role: MessageRole = MessageRole.USER
    content: str = ""
    content_type: MessageContentType = MessageContentType.TEXT
    content_rendered: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    is_streaming: bool = False
    is_regenerated: bool = False
    is_edited: bool = False
    feedback: Optional[FeedbackType] = None
    tokens_input: int = 0
    tokens_output: int = 0
    cost: float = 0.0
    latency_ms: Optional[int] = None
    model_used: Optional[str] = None
    provider_used: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
