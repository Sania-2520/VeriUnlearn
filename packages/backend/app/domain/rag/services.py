from typing import Optional

from app.core.logging import get_logger
from app.domain.rag.entities import Document, SearchResult
from app.domain.rag.interfaces import (
    DocumentChunkRepository,
    DocumentRepository,
    VectorSearchService,
)

logger = get_logger(__name__)


class RagService:
    def __init__(
        self,
        doc_repo: DocumentRepository,
        chunk_repo: DocumentChunkRepository,
        vector_service: VectorSearchService,
    ) -> None:
        self._doc_repo = doc_repo
        self._chunk_repo = chunk_repo
        self._vector_service = vector_service

    async def create_document(
        self, tenant_id: str, user_id: str, filename: str,
        original_filename: str, file_type: str, file_size_bytes: int,
        storage_path: str = "", content: str = "", metadata: dict = None,
    ) -> Document:
        doc = Document(
            tenant_id=tenant_id, user_id=user_id,
            filename=filename, original_filename=original_filename,
            file_type=file_type, file_size_bytes=file_size_bytes,
            storage_path=storage_path, metadata=metadata or {},
        )
        created = await self._doc_repo.create(doc)
        logger.info("RAG document created: %s", created.id)
        return created

    async def get_document(self, document_id: str) -> Optional[Document]:
        return await self._doc_repo.get_by_id(document_id)

    async def list_documents(
        self, tenant_id: str, page: int = 1, page_size: int = 25,
        status: Optional[str] = None, file_type: Optional[str] = None,
    ) -> tuple[list[Document], int]:
        return await self._doc_repo.list_by_tenant(tenant_id, page, page_size, status, file_type)

    async def delete_document(self, document_id: str, tenant_id: str) -> bool:
        doc = await self._doc_repo.get_by_id(document_id)
        if not doc or doc.tenant_id != tenant_id:
            return False
        await self._doc_repo.soft_delete(document_id, tenant_id)
        await self._chunk_repo.delete_by_document(document_id)
        try:
            await self._vector_service.delete_by_filter("documents", {"document_id": document_id})
        except Exception:
            logger.warning("Failed to delete vectors for document %s", document_id)
        return True

    async def search(
        self, query: str, tenant_id: str, top_k: int = 5,
        filters: dict = None, hybrid: bool = True,
    ) -> list[SearchResult]:
        return await self._vector_service.search(query, tenant_id, top_k, filters or {}, hybrid)
