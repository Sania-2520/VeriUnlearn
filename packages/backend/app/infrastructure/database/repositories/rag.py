from typing import Optional

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select, delete

from app.domain.rag.entities import Document, DocumentChunk, DocumentStatus, SearchResult
from app.domain.rag.interfaces import DocumentRepository, DocumentChunkRepository, VectorSearchService
from app.infrastructure.database.models import RagDocumentModel, RagDocumentChunkModel
from app.infrastructure.external.ml_engine import ml_engine_client, MLEngineClientError


class SQLAlchemyDocumentRepository(DocumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, document: Document) -> Document:
        model = RagDocumentModel(
            id=document.id,
            tenant_id=document.tenant_id,
            user_id=document.user_id,
            filename=document.filename,
            original_filename=document.original_filename,
            file_type=document.file_type,
            file_size_bytes=document.file_size_bytes,
            storage_path=document.storage_path,
            storage_bucket=document.storage_bucket,
            mime_type=document.mime_type,
            page_count=document.page_count,
            status=document.status.value if hasattr(document.status, "value") else document.status,
            error_message=document.error_message,
            chunk_count=document.chunk_count,
            event_metadata=document.metadata,
            content_hash=document.content_hash,
            is_deleted=document.is_deleted,
            deleted_at=document.deleted_at,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return document

    async def get_by_id(self, document_id: str) -> Optional[Document]:
        stmt = select(RagDocumentModel).where(RagDocumentModel.id == document_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._model_to_entity(model)

    async def list_by_tenant(
        self, tenant_id: str, page: int = 1, page_size: int = 25,
        status: Optional[str] = None, file_type: Optional[str] = None,
    ) -> tuple[list[Document], int]:
        query = select(RagDocumentModel).where(
            RagDocumentModel.tenant_id == tenant_id,
            RagDocumentModel.is_deleted == False,
        )
        if status:
            query = query.where(RagDocumentModel.status == status)
        if file_type:
            query = query.where(RagDocumentModel.file_type == file_type)
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar() or 0
        query = query.order_by(RagDocumentModel.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(query)
        models = result.scalars().all()
        return [self._model_to_entity(m) for m in models], total

    async def update(self, document: Document) -> Document:
        stmt = select(RagDocumentModel).where(RagDocumentModel.id == document.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            model.status = document.status.value if hasattr(document.status, "value") else document.status
            model.chunk_count = document.chunk_count
            model.error_message = document.error_message
            model.updated_at = document.updated_at
            await self._session.flush()
        return document

    async def soft_delete(self, document_id: str, tenant_id: str) -> None:
        from datetime import datetime, timezone
        stmt = select(RagDocumentModel).where(
            RagDocumentModel.id == document_id,
            RagDocumentModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            model.is_deleted = True
            model.deleted_at = datetime.now(timezone.utc)
            await self._session.flush()

    @staticmethod
    def _model_to_entity(model: "RagDocumentModel") -> Document:
        try:
            status = DocumentStatus(model.status)
        except ValueError:
            status = DocumentStatus.PENDING
        return Document(
            id=model.id,
            tenant_id=model.tenant_id,
            user_id=model.user_id,
            filename=model.filename,
            original_filename=model.original_filename,
            file_type=model.file_type,
            file_size_bytes=model.file_size_bytes,
            storage_path=model.storage_path,
            storage_bucket=model.storage_bucket,
            mime_type=model.mime_type,
            page_count=model.page_count,
            status=status,
            error_message=model.error_message,
            chunk_count=model.chunk_count,
            metadata=model.event_metadata or {},
            content_hash=model.content_hash,
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SQLAlchemyDocumentChunkRepository(DocumentChunkRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_many(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        for chunk in chunks:
            model = RagDocumentChunkModel(
                id=chunk.id,
                document_id=chunk.document_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                content_hash=chunk.content_hash,
                token_count=chunk.token_count,
                event_metadata=chunk.metadata,
                embedding_id=chunk.embedding_id,
                created_at=chunk.created_at,
            )
            self._session.add(model)
        await self._session.flush()
        return chunks

    async def delete_by_document(self, document_id: str) -> None:
        stmt = delete(RagDocumentChunkModel).where(RagDocumentChunkModel.document_id == document_id)
        await self._session.execute(stmt)
        await self._session.flush()


class MLEngineVectorSearchService(VectorSearchService):
    async def search(
        self, query: str, tenant_id: str, top_k: int = 5,
        filters: Optional[dict] = None, hybrid: bool = True,
    ) -> list[SearchResult]:
        try:
            result = await ml_engine_client.search_semantic(
                query=query, top_k=top_k, filters=filters or {},
            )
            items = result.get("results", result.get("items", []))
            if not items and isinstance(result, list):
                items = result
            return [
                SearchResult(
                    chunk_id=item.get("chunk_id", item.get("id", "")),
                    document_id=item.get("document_id", ""),
                    content=item.get("content", item.get("text", "")),
                    score=item.get("score", item.get("relevance", 0.0)),
                    metadata=item.get("metadata", {}),
                )
                for item in items
            ]
        except MLEngineClientError:
            logger = __import__("logging").getLogger(__name__)
            logger.warning("ML Engine search unavailable, returning empty results")
            return []

    async def upsert_embedding(self, collection: str, point_id: str, vector: list[float], payload: dict) -> None:
        try:
            await ml_engine_client.upsert_embedding(collection, point_id, vector, payload)
        except MLEngineClientError:
            logger = __import__("logging").getLogger(__name__)
            logger.warning("Failed to upsert embedding to ML Engine")

    async def delete_by_filter(self, collection: str, filter_: dict) -> None:
        try:
            await ml_engine_client.delete_vectors(collection, filter_)
        except MLEngineClientError:
            logger = __import__("logging").getLogger(__name__)
            logger.warning("Failed to delete vectors from ML Engine")
