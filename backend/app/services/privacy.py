"""Privacy Auditor engine.

- ``search_identities``   : scan every dataset/shard for a queried identity
- ``identity_footprint``  : full memory footprint of one identity
- ``recompute_dataset_roots`` : re-derive current Merkle roots from DB state
  (used by certificate verification)

Search confidence is computed (not guessed): exact identity-key matches score
1.0; otherwise the best fuzzy ratio over the decrypted name/email.
"""
from __future__ import annotations

import difflib
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import aes_decrypt
from app.db.models import Dataset, DatasetRecord, MLModel
from app.repositories.dataset_repo import DatasetRepository
from app.repositories.model_repo import ModelRepository
from app.services.crypto import MerkleTree, leaf_hash
from app.services.embeddings import get_vector_store
from app.services.pii import identity_key


def decrypt_identity(record: DatasetRecord) -> dict[str, str]:
    """Decrypt PII fields stored at rest (AES-256-GCM)."""
    full_name = aes_decrypt(record.full_name_enc) if record.full_name_enc else ""
    email = aes_decrypt(record.email_enc) if record.email_enc else ""
    return {"full_name": full_name, "email": email}


class PrivacyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.datasets = DatasetRepository(session)
        self.models = ModelRepository(session)
        self.vectors = get_vector_store()

    # ------------------------------------------------------------------ search

    async def search_identities(self, query: str, *, limit: int = 50) -> list[dict[str, Any]]:
        query = query.strip().lower()
        if not query:
            return []
        exact_key = identity_key(query.replace(" ", ""))

        result = await self.session.execute(
            select(DatasetRecord).where(DatasetRecord.is_deleted.is_(False))
        )
        records = list(result.scalars().all())
        datasets = {d.id: d for d in (await self._all_datasets())}
        models = await self._active_models_by_dataset()

        matches: list[dict[str, Any]] = []
        seen: set[str] = set()
        for record in records:
            identity = decrypt_identity(record)
            name = identity["full_name"].lower()
            email = identity["email"].lower()
            if not (query in name or query in email):
                continue
            if record.id in seen:
                continue
            seen.add(record.id)

            confidence = 1.0 if record.identity_key == exact_key else max(
                difflib.SequenceMatcher(None, query, name).ratio(),
                difflib.SequenceMatcher(None, query, email).ratio() * 0.9,
            )
            dataset = datasets.get(record.dataset_id)
            model = models.get(record.dataset_id)
            matches.append(
                {
                    "record_id": record.id,
                    "identity_key": record.identity_key,
                    "full_name": identity["full_name"],
                    "email": identity["email"],
                    "confidence": round(min(confidence, 1.0), 4),
                    "source": dataset.name if dataset else "unknown",
                    "dataset_id": record.dataset_id,
                    "model_id": model.id if model else None,
                    "model_version": model.version if model else None,
                    "shard_id": record.shard_id,
                    "sensitivity": record.sensitivity,
                    "influence_score": record.influence_score,
                    "has_embedding": record.embedding_id is not None,
                    "adapter": model.adapters[0] if model and model.adapters else None,
                    "is_deleted": record.is_deleted,
                }
            )
            if len(matches) >= limit:
                break
        matches.sort(key=lambda m: m["confidence"], reverse=True)
        return matches

    # ------------------------------------------------------------------ footprint

    async def identity_footprint(self, identity: str) -> dict[str, Any]:
        key = identity_key(identity)
        result = await self.session.execute(
            select(DatasetRecord).where(DatasetRecord.identity_key == key)
        )
        records = list(result.scalars().all())
        if not records:
            raise LookupError(f"No records found for identity '{identity}'")

        first = decrypt_identity(records[0])
        active = [r for r in records if not r.is_deleted]
        deleted = [r for r in records if r.is_deleted]

        # Knowledge clusters: group by (dataset, shard).
        clusters: list[dict[str, Any]] = []
        for dataset_id in {r.dataset_id for r in active}:
            dataset = await self.datasets.get(dataset_id)
            model = await self.models.get_active_for_dataset(dataset_id)
            for shard_id in {r.shard_id for r in active if r.dataset_id == dataset_id}:
                shard_records = [r for r in active if r.dataset_id == dataset_id and r.shard_id == shard_id]
                clusters.append(
                    {
                        "dataset": dataset.name,
                        "dataset_id": dataset_id,
                        "shard_id": shard_id,
                        "record_count": len(shard_records),
                        "record_ids": [r.id for r in shard_records],
                        "model_id": model.id if model else None,
                    }
                )

        # Affected neurons: top features by |coefficient| across shard weights.
        neurons: list[dict[str, Any]] = []
        feature_names: list[str] = []
        shard_weights: list[np.ndarray] = []
        if active:
            dataset = await self.datasets.get(active[0].dataset_id)
            feature_names = dataset.feature_names
            model = await self.models.get_active_for_dataset(dataset.id)
            if model:
                shards = await self.models.get_shards(model.id)
                for shard in shards:
                    if shard.weights_path:
                        data = np.load(shard.weights_path, allow_pickle=True)
                        shard_weights.append(data["weights"])
            if shard_weights:
                mean_weights = np.mean(np.stack([w[1:] for w in shard_weights]), axis=0)
                for idx in np.argsort(-np.abs(mean_weights))[:10]:
                    name = feature_names[idx] if idx < len(feature_names) else f"feature_{idx}"
                    neurons.append({"feature": name, "weight": round(float(mean_weights[idx]), 6)})

        influence_scores = [r.influence_score for r in active if r.influence_score is not None]
        return {
            "identity_key": key,
            "full_name": first["full_name"],
            "email": first["email"],
            "total_records": len(records),
            "active_records": len(active),
            "deleted_records": len(deleted),
            "datasets_affected": sorted({r.dataset_id for r in records}),
            "record_ids": [r.id for r in records],
            "embedding_ids": [r.embedding_id for r in active if r.embedding_id],
            "knowledge_clusters": clusters,
            "affected_neurons": neurons,
            "adapters": [],
            "data_importance": {
                "mean_influence": round(float(np.mean(influence_scores)), 6) if influence_scores else None,
                "max_influence": round(float(np.max(influence_scores)), 6) if influence_scores else None,
                "influence_scores": {r.id: r.influence_score for r in active if r.influence_score is not None},
            },
            "sensitivity": sorted({r.sensitivity for r in records}),
            "model_memory_footprint_bytes": sum(
                len(r.features) * 64 for r in records
            ),
        }

    # ------------------------------------------------------------------ merkle roots

    async def _all_datasets(self) -> list[Dataset]:
        result = await self.session.execute(select(Dataset).order_by(Dataset.created_at))
        return list(result.scalars().all())

    async def _active_models_by_dataset(self) -> dict[str, MLModel]:
        result = await self.session.execute(
            select(MLModel).where(MLModel.is_active.is_(True)).order_by(MLModel.version.desc())
        )
        models: dict[str, MLModel] = {}
        for model in result.scalars().all():
            models.setdefault(model.dataset_id, model)
        return models


async def recompute_dataset_roots(
    session: AsyncSession,
    dataset_id: str | None,
    deleted_record_hashes: list[str] | None = None,
) -> dict[str, Any]:
    """Re-derive current Merkle roots from live DB state.

    Active records contribute their content leaves; deleted records contribute
    tombstone leaves, so the post-root provably excludes deleted data while
    remaining reproducible. Returns the current root plus a check that every
    claimed deleted hash is indeed tombstoned.
    """
    stmt = select(DatasetRecord)
    if dataset_id:
        stmt = stmt.where(DatasetRecord.dataset_id == dataset_id)
    result = await session.execute(stmt)
    records = list(result.scalars().all())

    leaves = [
        leaf_hash(r.id, r.content_hash, deleted=r.is_deleted) for r in records
    ]
    root = MerkleTree(leaves).root

    tombstoned_hashes = {r.content_hash for r in records if r.is_deleted}
    claimed = set(deleted_record_hashes or [])
    return {
        "post_root": root,
        "record_count": len(records),
        "tombstoned": sorted(claimed & tombstoned_hashes),
        "all_claimed_tombstoned": bool(claimed) and claimed.issubset(tombstoned_hashes),
    }
