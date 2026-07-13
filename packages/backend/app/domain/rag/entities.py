import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"
    DELETED = "deleted"


class DocumentType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    CSV = "csv"
    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"


@dataclass
class Document:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    user_id: Optional[str] = None
    filename: str = ""
    original_filename: str = ""
    file_type: str = ""
    file_size_bytes: int = 0
    storage_path: str = ""
    storage_bucket: str = ""
    mime_type: Optional[str] = None
    page_count: Optional[int] = None
    status: DocumentStatus = DocumentStatus.PENDING
    error_message: Optional[str] = None
    chunk_count: int = 0
    metadata: dict = field(default_factory=dict)
    content_hash: Optional[str] = None
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DocumentChunk:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = ""
    chunk_index: int = 0
    content: str = ""
    content_hash: str = ""
    token_count: int = 0
    metadata: dict = field(default_factory=dict)
    embedding_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class OCRResult:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = ""
    page_number: int = 0
    raw_text: str = ""
    confidence: Optional[float] = None
    bounding_boxes: Optional[dict] = None
    language: Optional[str] = None
    processing_time_ms: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SearchResult:
    chunk_id: str = ""
    document_id: str = ""
    content: str = ""
    score: float = 0.0
    metadata: dict = field(default_factory=dict)
