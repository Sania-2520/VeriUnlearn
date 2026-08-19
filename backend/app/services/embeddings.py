"""Vector store abstraction for embeddings.

Default backend is an in-memory numpy store (cosine similarity) so the whole
stack runs without infrastructure. When ``VECTOR_STORE_BACKEND=qdrant`` and
``QDRANT_URL`` are configured, :class:`QdrantVectorStore` is used instead.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Protocol

import numpy as np

logger = logging.getLogger("veriunlearn.embeddings")


class VectorStore(Protocol):
    def upsert(self, collection: str, vector_id: str, vector: np.ndarray, payload: dict[str, Any]) -> None: ...

    def upsert_batch(
        self, collection: str, vectors: list[tuple[str, np.ndarray, dict[str, Any]]]
    ) -> None: ...

    def search(self, collection: str, vector: np.ndarray, k: int = 10) -> list[dict[str, Any]]: ...

    def delete(self, collection: str, vector_ids: list[str]) -> None: ...

    def count(self, collection: str) -> int: ...

    def drop_collection(self, name: str) -> None: ...


class MemoryVectorStore:
    """Brute-force cosine-similarity store; deterministic and dependency-free."""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, tuple[np.ndarray, dict[str, Any]]]] = {}

    def _collection(self, name: str) -> dict[str, tuple[np.ndarray, dict[str, Any]]]:
        return self._data.setdefault(name, {})

    def upsert(self, collection: str, vector_id: str, vector: np.ndarray, payload: dict[str, Any]) -> None:
        self._collection(collection)[vector_id] = (np.asarray(vector, dtype=float), payload)

    def upsert_batch(
        self, collection: str, vectors: list[tuple[str, np.ndarray, dict[str, Any]]]
    ) -> None:
        bucket = self._collection(collection)
        for vector_id, vector, payload in vectors:
            bucket[vector_id] = (np.asarray(vector, dtype=float), payload)

    def search(self, collection: str, vector: np.ndarray, k: int = 10) -> list[dict[str, Any]]:
        query = np.asarray(vector, dtype=float)
        qnorm = np.linalg.norm(query)
        if qnorm == 0:
            return []
        results: list[dict[str, Any]] = []
        for vid, (vec, payload) in self._collection(collection).items():
            norm = np.linalg.norm(vec)
            if norm == 0:
                continue
            score = float(np.dot(vec, query) / (norm * qnorm))
            results.append({"id": vid, "score": score, "payload": payload})
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:k]

    def delete(self, collection: str, vector_ids: list[str]) -> None:
        bucket = self._collection(collection)
        for vid in vector_ids:
            bucket.pop(vid, None)

    def count(self, collection: str) -> int:
        return len(self._collection(collection))

    def drop_collection(self, name: str) -> None:
        self._data.pop(name, None)


class QdrantVectorStore:
    """Qdrant-backed store; requires the optional ``qdrant-client`` package."""

    def __init__(self, url: str, api_key: str | None = None) -> None:
        try:
            from qdrant_client import QdrantClient  # type: ignore[import-not-found]
            from qdrant_client.models import (  # type: ignore[import-not-found]
                Distance,
                PointStruct,
                VectorParams,
            )
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("qdrant-client not installed (pip install qdrant-client)") from exc
        self._client = QdrantClient(url=url, api_key=api_key)
        self._Distance = Distance
        self._PointStruct = PointStruct
        self._VectorParams = VectorParams
        self._dim: int | None = None

    def _ensure_collection(self, collection: str, dim: int) -> None:
        if not self._client.collection_exists(collection):
            self._client.create_collection(
                collection, vectors_config=self._VectorParams(size=dim, distance=self._Distance.COSINE)
            )

    def upsert(self, collection: str, vector_id: str, vector: np.ndarray, payload: dict[str, Any]) -> None:
        vector = np.asarray(vector, dtype=float)
        self._ensure_collection(collection, vector.shape[0])
        self._client.upsert(
            collection,
            points=[self._PointStruct(id=vector_id, vector=vector.tolist(), payload=payload)],
        )

    def upsert_batch(
        self, collection: str, vectors: list[tuple[str, np.ndarray, dict[str, Any]]]
    ) -> None:
        """Bulk upsert: one collection check + one request for all points.

        Per-point upserts cost ~25 ms each with qdrant-client (collection
        existence check per call), which makes large ingests quadratic in
        round-trips. Batching keeps a 5,000-row upload at a handful of calls.
        """
        if not vectors:
            return
        vector = np.asarray(vectors[0][1], dtype=float)
        self._ensure_collection(collection, vector.shape[0])
        self._client.upsert(
            collection,
            points=[
                self._PointStruct(id=vector_id, vector=np.asarray(v, dtype=float).tolist(), payload=payload)
                for vector_id, v, payload in vectors
            ],
        )

    def search(self, collection: str, vector: np.ndarray, k: int = 10) -> list[dict[str, Any]]:
        if not self._client.collection_exists(collection):
            return []
        hits = self._client.search(collection, query_vector=np.asarray(vector, dtype=float).tolist(), limit=k)
        return [
            {"id": str(h.id), "score": float(h.score), "payload": h.payload or {}}
            for h in hits
        ]

    def delete(self, collection: str, vector_ids: list[str]) -> None:
        if self._client.collection_exists(collection):
            self._client.delete(collection, points_selector=[uuid.UUID(v) if len(v) == 36 else v for v in vector_ids])

    def count(self, collection: str) -> int:
        if not self._client.collection_exists(collection):
            return 0
        return int(self._client.count(collection).count)

    def drop_collection(self, name: str) -> None:
        if self._client.collection_exists(name):
            self._client.delete_collection(name)


class VectorStoreFactory:
    @staticmethod
    def create() -> VectorStore:
        from app.core.config import settings

        if settings.VECTOR_STORE_BACKEND == "qdrant":
            if not settings.QDRANT_URL:
                raise RuntimeError("VECTOR_STORE_BACKEND=qdrant requires QDRANT_URL")
            try:
                store = QdrantVectorStore(settings.QDRANT_URL, settings.QDRANT_API_KEY)
                # Probe the connection so we can fall back early.
                store._client.get_collections()
                logger.info("Using Qdrant vector store at %s", settings.QDRANT_URL)
                return store
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Qdrant unavailable (%s) — falling back to in-memory vector store",
                    exc,
                )
        return MemoryVectorStore()


_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreFactory.create()
    return _vector_store
