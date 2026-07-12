from __future__ import annotations

from typing import Any

from loguru import logger
from qdrant_client import AsyncQdrantClient, models
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.ml.embeddings import EmbeddingEngine


COLLECTION_NAME = "document_chunks"


class RAGService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.embedder = EmbeddingEngine()
        self._client: AsyncQdrantClient | None = None
        self._collection_ready = False

    async def _get_client(self) -> AsyncQdrantClient:
        if self._client is None:
            self._client = AsyncQdrantClient(url=settings.qdrant_url)
        return self._client

    async def ensure_collection(self) -> None:
        if self._collection_ready:
            return
        client = await self._get_client()
        try:
            collections = await client.get_collections()
            existing = {c.name for c in collections.collections}
            if COLLECTION_NAME not in existing:
                await client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=models.VectorParams(
                        size=self.embedder.dimension,
                        distance=models.Distance.COSINE,
                    ),
                )
                logger.info(f"Qdrant collection created: {COLLECTION_NAME}")
            self._collection_ready = True
        except Exception as e:
            logger.warning(f"Qdrant not available: {e}")

    async def index_chunk(self, chunk: Any, embedding: list[float]) -> str:
        await self.ensure_collection()
        point_id = f"chunk_{chunk.id}"
        client = await self._get_client()
        try:
            await client.upsert(
                collection_name=COLLECTION_NAME,
                points=[
                    models.PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload={
                            "chunk_id": chunk.id,
                            "document_id": chunk.document_id,
                            "chunk_index": chunk.chunk_index,
                            "content": chunk.content[:500],
                        },
                    )
                ],
            )
        except Exception as e:
            logger.warning(f"Qdrant index failed: {e}")
        return point_id

    async def retrieve(
        self, query: str, top_k: int = 3, user_id: int | None = None
    ) -> list[dict[str, Any]]:
        query_embedding = self.embedder.embed(query)
        await self.ensure_collection()
        client = await self._get_client()
        try:
            search_result = await client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_embedding,
                limit=top_k,
                score_threshold=0.5,
            )
            results = []
            for point in search_result.points:
                payload = point.payload or {}
                results.append({
                    "chunk_id": payload.get("chunk_id"),
                    "document_id": payload.get("document_id"),
                    "content": payload.get("content", ""),
                    "score": point.score,
                })
            return results
        except Exception as e:
            logger.warning(f"Qdrant search failed: {e}")
            return []

    async def delete_document_chunks(self, document_id: int) -> None:
        client = await self._get_client()
        try:
            await client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="document_id",
                                match=models.MatchValue(value=document_id),
                            )
                        ]
                    )
                ),
            )
        except Exception as e:
            logger.warning(f"Qdrant deletion failed: {e}")

    async def delete_point(self, point_id: str) -> None:
        client = await self._get_client()
        try:
            await client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=models.PointIdsList(points=[point_id]),
            )
        except Exception as e:
            logger.warning(f"Qdrant point deletion failed: {e}")

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None
