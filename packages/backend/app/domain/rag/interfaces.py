from abc import ABC, abstractmethod
from typing import Optional

from app.domain.rag.entities import Document, DocumentChunk, SearchResult


class DocumentRepository(ABC):
    @abstractmethod
    async def create(self, document: Document) -> Document:
        ...

    @abstractmethod
    async def get_by_id(self, document_id: str) -> Optional[Document]:
        ...

    @abstractmethod
    async def list_by_tenant(
        self, tenant_id: str, page: int, page_size: int,
        status: Optional[str] = None, file_type: Optional[str] = None,
    ) -> tuple[list[Document], int]:
        ...

    @abstractmethod
    async def update(self, document: Document) -> Document:
        ...

    @abstractmethod
    async def soft_delete(self, document_id: str, tenant_id: str) -> None:
        ...


class DocumentChunkRepository(ABC):
    @abstractmethod
    async def create_many(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        ...

    @abstractmethod
    async def delete_by_document(self, document_id: str) -> None:
        ...


class VectorSearchService(ABC):
    @abstractmethod
    async def search(
        self, query: str, tenant_id: str, top_k: int = 5,
        filters: Optional[dict] = None, hybrid: bool = True,
    ) -> list[SearchResult]:
        ...

    @abstractmethod
    async def upsert_embedding(
        self, collection: str, point_id: str, vector: list[float],
        payload: dict,
    ) -> None:
        ...

    @abstractmethod
    async def delete_by_filter(self, collection: str, filter_: dict) -> None:
        ...
