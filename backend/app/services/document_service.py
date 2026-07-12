from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import BinaryIO

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document import Document, DocumentChunk
from app.models.user import User
from app.ml.embeddings import EmbeddingEngine


CHUNK_SIZE = 512
CHUNK_OVERLAP = 64


class DocumentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.embedder = EmbeddingEngine()

    async def upload_document(
        self, user: User, filename: str, content_type: str, file_obj: BinaryIO | bytes
    ) -> Document:
        content = file_obj.read() if hasattr(file_obj, "read") else file_obj
        size_bytes = len(content)
        storage_dir = Path(settings.adapter_storage_dir) / "documents" / str(user.id)
        storage_dir.mkdir(parents=True, exist_ok=True)
        file_hash = hashlib.sha256(content).hexdigest()[:16]
        safe_name = f"{file_hash}_{filename}"
        storage_path = str(storage_dir / safe_name)
        with open(storage_path, "wb") as f:
            f.write(content)

        doc = Document(
            user_id=user.id,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            storage_path=storage_path,
            status="uploaded",
        )
        self.db.add(doc)
        await self.db.flush()
        await self.db.refresh(doc)
        logger.info(f"Document uploaded: id={doc.id}, filename={filename}, size={size_bytes}")
        return doc

    async def process_document(self, document_id: int) -> int:
        result = await self.db.execute(select(Document).where(Document.id == document_id))
        doc = result.scalar_one_or_none()
        if doc is None:
            raise ValueError("Document not found")

        with open(doc.storage_path, "rb") as f:
            content = f.read()

        text = self._parse_content(content, doc.content_type)

        chunks = self._chunk_text(text)

        chunk_count = 0
        for i, chunk_text in enumerate(chunks):
            chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=i,
                content=chunk_text,
            )
            self.db.add(chunk)
            chunk_count += 1

        await self.db.flush()

        chunk_models = await self._get_chunks(doc.id)
        texts = [c.content for c in chunk_models]
        embeddings = self.embedder.embed_batch(texts)

        from app.services.rag_service import RAGService
        rag = RAGService(self.db)
        for chunk_model, emb in zip(chunk_models, embeddings):
            point_id = await rag.index_chunk(chunk_model, emb)
            chunk_model.embedding_id = point_id

        await self.db.flush()

        doc.status = "processed"
        await self.db.flush()

        logger.info(f"Document processed: id={doc.id}, chunks={chunk_count}")
        return chunk_count

    def _parse_content(self, content: bytes, content_type: str) -> str:
        if content_type == "application/pdf":
            return self._parse_pdf(content)
        return content.decode("utf-8", errors="replace")

    def _parse_pdf(self, content: bytes) -> str:
        try:
            import PyPDF2
            import io
            reader = PyPDF2.PdfReader(io.BytesIO(content))
            return "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
        except ImportError:
            logger.warning("PyPDF2 not installed, using raw text fallback")
            return content.decode("utf-8", errors="replace")

    def _chunk_text(self, text: str) -> list[str]:
        words = text.split()
        chunks = []
        i = 0
        while i < len(words):
            chunk_words = words[i:i + CHUNK_SIZE]
            chunks.append(" ".join(chunk_words))
            i += CHUNK_SIZE - CHUNK_OVERLAP
            if i >= len(words):
                break
        return chunks if chunks else [text]

    async def _get_chunks(self, document_id: int) -> list[DocumentChunk]:
        result = await self.db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        return list(result.scalars().all())

    async def get_documents(self, user_id: int | None = None) -> list[Document]:
        query = select(Document).order_by(Document.created_at.desc())
        if user_id:
            query = query.where(Document.user_id == user_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_document(self, document_id: int) -> Document | None:
        result = await self.db.execute(select(Document).where(Document.id == document_id))
        return result.scalar_one_or_none()

    async def delete_document(self, document_id: int, user_id: int) -> bool:
        result = await self.db.execute(
            select(Document).where(Document.id == document_id, Document.user_id == user_id)
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            return False
        if os.path.exists(doc.storage_path):
            os.remove(doc.storage_path)
        await self.db.delete(doc)
        await self.db.flush()
        return True
