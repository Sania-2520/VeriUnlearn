"""Unlearning orchestration.

Executes a :class:`DeletionRequest` through the full VeriUnlearn pipeline:

1. resolve affected records (identity or explicit ids) → group by dataset
2. capture the *pre* dataset Merkle root per dataset
3. tombstone records (never hard-delete — auditability) + drop embeddings
4. scrub model per selected method:
   - ``retrain``   : SISA selective retraining of affected shards (gold standard)
   - ``certified`` : Newton-step certified removal with a provable bound
   - ``influence`` : reverse-gradient scrub weighted by influence scores
5. capture the *post* Merkle root (tombstone leaves change the root)
6. issue signed certificate + ZK proof + blockchain registration per dataset
7. write hash-chained audit events at every step

Runs inside a background worker (``workers/tasks.py``) so the API stays async.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationFailedError
from app.db.models import (
    DatasetRecord,
    DeletionHistory,
    DeletionRequest,
    EmbeddingIndex,
    MLModel,
)
from app.repositories.dataset_repo import DatasetRepository
from app.repositories.deletion_repo import DeletionRepository
from app.repositories.model_repo import ModelRepository
from app.services.audit import AuditService
from app.services.blockchain import BlockchainService
from app.services.certificate import CertificateService
from app.services.certified_removal import CertifiedRemovalService
from app.services.crypto import (
    MerkleTree,
    canonical_json,
    leaf_hash,
    sha256_hex,
    tombstone_hash,
)
from app.services.embeddings import get_vector_store
from app.services.influence import InfluenceEngine
from app.services.sisa import SISAEngine
from app.services.zkproof import ZKDeletionProofService

logger = logging.getLogger("veriunlearn.unlearning")


class UnlearningService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.datasets = DatasetRepository(session)
        self.models_repo = ModelRepository(session)
        self.deletions = DeletionRepository(session)
        self.sisa = SISAEngine(session)
        self.influence = InfluenceEngine(session)
        self.certified = CertifiedRemovalService(session)
        self.certificates = CertificateService(session)
        self.audit = AuditService(session)
        self.blockchain = BlockchainService(session)
        self.vectors = get_vector_store()

    # ------------------------------------------------------------------ resolution

    async def resolve_records(
        self,
        *,
        identity_key: str | None = None,
        record_ids: list[str] | None = None,
        chat_id: str | None = None,
        dataset_id: str | None = None,
        scope: str = "records",
    ) -> list[DatasetRecord]:
        """Resolve the records targeted by a deletion selection.

        Scopes (Phase 4 STEP 1): ``records`` (single/multiple/identity),
        ``chat`` (entire conversation), ``dataset`` (entire dataset).
        """
        if scope == "dataset" and dataset_id:
            records = await self.datasets.get_records(dataset_id, include_deleted=False)
            if not records:
                raise NotFoundError(f"No active records in dataset {dataset_id}")
            return records
        if scope == "chat" and chat_id:
            result = await self.session.execute(
                select(DatasetRecord).where(
                    DatasetRecord.chat_id == chat_id, DatasetRecord.is_deleted.is_(False)
                )
            )
            records = list(result.scalars().all())
            if not records:
                raise NotFoundError(f"No active records for chat '{chat_id}'")
            return records
        if record_ids:
            records = await self.datasets.get_records_by_ids(record_ids)
            active = [r for r in records if not r.is_deleted]
            if not active:
                raise ValidationFailedError("No active records match the given ids")
            return active
        if identity_key:
            result = await self.session.execute(
                select(DatasetRecord).where(
                    DatasetRecord.identity_key == identity_key,
                    DatasetRecord.is_deleted.is_(False),
                )
            )
            records = list(result.scalars().all())
            if not records:
                raise NotFoundError(f"No active records for identity '{identity_key}'")
            return records
        raise ValidationFailedError("Provide a selection (identity_key, record_ids, chat_id or dataset_id)")

    # ------------------------------------------------------------------ impact analysis

    async def analyze_impact(
        self,
        *,
        identity_key: str | None = None,
        record_ids: list[str] | None = None,
        chat_id: str | None = None,
        dataset_id: str | None = None,
        scope: str = "records",
    ) -> dict[str, Any]:
        """Phase 4 STEP 2 — impact report computed *before* any deletion.

        Lists affected embeddings, vectors, knowledge chunks, model shards,
        influence estimates, dependencies and deletion eligibility.
        """
        records = await self.resolve_records(
            identity_key=identity_key,
            record_ids=record_ids,
            chat_id=chat_id,
            dataset_id=dataset_id,
            scope=scope,
        )
        groups: dict[str, list[DatasetRecord]] = {}
        for record in records:
            groups.setdefault(record.dataset_id, []).append(record)

        datasets_out: dict[str, Any] = {}
        totals = {"records": 0, "embeddings": 0, "chunks": 0, "shards": 0, "influence_abs": 0.0}
        for ds_id, group in groups.items():
            dataset = await self.datasets.get(ds_id)
            model = await self.models_repo.get_active_for_dataset(ds_id)
            shards = sorted({r.shard_id for r in group})
            embeddings = [r.embedding_id for r in group if r.embedding_id]
            vectors = [r.vector_id for r in group if r.vector_id]
            influences = [r.influence_score for r in group if r.influence_score is not None]
            est_retrain = 0.0
            if model:
                per_shard = float(model.metrics.get("training_seconds", 0)) / max(model.shard_count, 1)
                est_retrain = round(per_shard * len(shards), 3)
            entry = {
                "dataset_id": ds_id,
                "dataset_name": dataset.name,
                "dataset_version": dataset.version,
                "record_count": len(group),
                "record_ids": [r.id for r in group],
                "embedding_ids": embeddings,
                "vector_ids": vectors,
                "knowledge_chunks": [f"chunk-{ds_id}-{r.record_index}" for r in group],
                "chat_ids": sorted({r.chat_id for r in group if r.chat_id}),
                "affected_shards": shards,
                "influence": {
                    "mean": round(float(np.mean(influences)), 6) if influences else None,
                    "abs_sum": round(float(np.sum(np.abs(influences))), 6) if influences else 0.0,
                },
                "dependencies": {
                    "model_id": model.id if model else None,
                    "model_version": model.version if model else None,
                    "adapters": model.adapters if model else [],
                },
                "estimated_retraining_seconds": est_retrain,
                "deletion_eligible": model is not None and model.status == "ready",
            }
            totals["records"] += len(group)
            totals["embeddings"] += len(embeddings)
            totals["chunks"] += len(entry["knowledge_chunks"])
            totals["shards"] += len(shards)
            totals["influence_abs"] += entry["influence"]["abs_sum"]
            datasets_out[ds_id] = entry

        return {
            "scope": scope,
            "selection": {
                "identity_key": identity_key,
                "record_ids": record_ids,
                "chat_id": chat_id,
                "dataset_id": dataset_id,
            },
            "totals": {
                "records": totals["records"],
                "embeddings": totals["embeddings"],
                "vectors": totals["embeddings"],
                "knowledge_chunks": totals["chunks"],
                "affected_shards": totals["shards"],
                "influence_abs_sum": round(totals["influence_abs"], 6),
            },
            "datasets": datasets_out,
            "eligible": all(d["deletion_eligible"] for d in datasets_out.values()) if datasets_out else False,
        }

    # ------------------------------------------------------------------ execution

    async def execute(self, request_id: str) -> dict[str, Any]:
        request = await self.deletions.get(request_id)
        request.status = "in_progress"
        await self.session.flush()
        start = time.monotonic()

        try:
            scope = request.scope.get("scope", "records") if request.scope else "records"
            records = await self.resolve_records(
                identity_key=request.identity_key,
                record_ids=request.record_ids,
                chat_id=request.scope.get("chat_id") if request.scope else None,
                dataset_id=request.scope.get("dataset_id") if request.scope else None,
                scope=scope,
            )
            if not records:
                raise ValidationFailedError("Nothing to delete")

            request.record_ids = [r.id for r in records]
            groups: dict[str, list[DatasetRecord]] = {}
            for record in records:
                groups.setdefault(record.dataset_id, []).append(record)

            outcome: dict[str, Any] = {"datasets": {}, "certificates": []}
            for dataset_id, group in groups.items():
                dataset_outcome = await self._execute_for_dataset(request, dataset_id, group)
                outcome["datasets"][dataset_id] = dataset_outcome
                outcome["certificates"].append(dataset_outcome["certificate_id"])

            request.status = "completed"
            request.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            request.duration_seconds = round(time.monotonic() - start, 3)
            request.certificate_id = outcome["certificates"][0] if outcome["certificates"] else None
            request.result = {
                "deleted_records": len(records),
                "datasets": list(groups),
                "certificates": outcome["certificates"],
                **outcome["datasets"],
            }
            await self.audit.log(
                event_type="unlearning.completed",
                actor=request.requested_by,
                subject=request.identity_key or request.subject_label,
                certificate_id=request.certificate_id,
                payload={
                    "request_id": request.id,
                    "method": request.method,
                    "records": len(records),
                    "datasets": list(groups),
                    "duration": request.duration_seconds,
                },
            )
            await self.session.flush()
            logger.info("Unlearning %s completed in %ss", request.id, request.duration_seconds)
            return request.result
        except Exception as exc:
            request.status = "failed"
            request.error = str(exc)
            await self.audit.log(
                event_type="unlearning.failed",
                actor=request.requested_by,
                subject=request.identity_key or request.subject_label,
                payload={"request_id": request.id, "error": str(exc)},
            )
            await self.session.flush()
            logger.exception("Unlearning %s failed", request.id)
            raise

    async def _execute_for_dataset(
        self, request: DeletionRequest, dataset_id: str, records: list[DatasetRecord]
    ) -> dict[str, Any]:
        dataset_start = time.monotonic()
        model = await self.models_repo.get_active_for_dataset(dataset_id)
        if model is None:
            raise NotFoundError(f"No trained model for dataset {dataset_id}")
        dataset = await self.datasets.get(dataset_id)

        affected_shards = sorted({r.shard_id for r in records})
        pre_root = await self._dataset_root(dataset_id)

        # Phase 4 STEP 6 — before snapshot.
        all_active = await self.datasets.get_records(dataset_id, include_deleted=False)
        shard_metrics_before = {}
        for shard in await self.models_repo.get_shards(model.id):
            if shard.shard_index in affected_shards:
                shard_metrics_before[shard.shard_index] = {
                    "accuracy": shard.accuracy,
                    "record_version": shard.record_version,
                    "trained_on": shard.trained_on,
                }
        before = {
            "records": len(all_active),
            "embeddings": sum(1 for r in all_active if r.embedding_id),
            "vectors": sum(1 for r in all_active if r.vector_id),
            "shards": shard_metrics_before,
            "dataset_version": dataset.version,
            "model_version": model.version,
        }

        # 1. Tombstone records + drop embeddings/vectors (STEP 3).
        collection = f"dataset_{dataset_id}"
        for record in records:
            record.is_deleted = True
            record.tombstone_hash = tombstone_hash(record.id, record.content_hash)
            record.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
            if record.embedding_id:
                self.vectors.delete(collection, [record.embedding_id])
                record.embedding_id = None
                record.vector_id = None
        await self.session.execute(
            EmbeddingIndex.__table__.update()
            .where(EmbeddingIndex.record_id.in_([r.id for r in records]))
            .values(is_deleted=True)
        )
        await self.session.flush()

        # 2. Scrub the model (STEP 4 SISA retrain / STEP 5 weight scrub).
        scrub = await self._scrub_model(model, dataset, affected_shards, records, request.method)

        # 3. Post root + certificate.
        post_root = await self._dataset_root(dataset_id)
        model.version += 1
        model.parent_version = model.version - 1
        dataset.version += 1
        await self.session.flush()

        certificate = await self.certificates.issue(
            subject_user_id=request.identity_key or request.subject_label,
            deletion_type=request.deletion_type,
            deleted_record_count=len(records),
            dataset_id=dataset_id,
            model_id=model.id,
            model_version=model.version,
            shard_ids=affected_shards,
            pre_merkle_root=pre_root,
            post_merkle_root=post_root,
            deleted_record_hashes=[r.content_hash for r in records],
            method=request.method,
            deletion_request_id=request.id,
            certified_bound=scrub.get("certified_bound"),
            actor=request.requested_by,
        )

        # 4. ZK proof bound to this certificate.
        zk_proof = ZKDeletionProofService.issue(
            weights_hash=model.weights_hash,
            post_merkle_root=post_root,
            certificate_id=certificate.id,
            deleted_record_hashes=[r.content_hash for r in records],
            method=request.method,
        )
        certificate.zk_proof = zk_proof
        await self.session.flush()

        # 5. PDF + blockchain registration.
        try:
            await self.certificates.persist_pdf(certificate)
        except Exception as exc:  # noqa: BLE001 - PDF is a nicety, never fails the deletion
            logger.warning("PDF generation failed: %s", exc)
        ledger = await self.blockchain.register_certificate(certificate.id, certificate.content_hash)
        certificate.blockchain_tx = ledger.get("tx_hash")

        # Phase 4 STEP 6 — after snapshot + STEP 7 deletion report row.
        remaining = await self.datasets.get_records(dataset_id, include_deleted=False)
        after = {
            "records": len(remaining),
            "embeddings": sum(1 for r in remaining if r.embedding_id),
            "vectors": sum(1 for r in remaining if r.vector_id),
            "dataset_version": dataset.version,
            "model_version": model.version,
        }
        self.session.add(
            DeletionHistory(
                request_id=request.id,
                scope=request.scope.get("scope", "records") if request.scope else "records",
                subject=request.identity_key or request.subject_label,
                method=request.method,
                status="completed",
                record_count=len(records),
                shard_ids=affected_shards,
                duration_seconds=round(time.monotonic() - dataset_start, 3),
                model_id=model.id,
                model_version=model.version,
                dataset_id=dataset_id,
                dataset_version=dataset.version,
                records_before=before["records"],
                records_after=after["records"],
                embeddings_before=before["embeddings"],
                embeddings_after=after["embeddings"],
                vectors_removed=sum(1 for r in records if r.vector_id is None and r.is_deleted),
                certified_bound=scrub.get("certified_bound"),
                certificate_id=certificate.id,
                before=before,
                after=after,
            )
        )
        await self.session.flush()

        return {
            "deleted_records": len(records),
            "shards": affected_shards,
            "pre_root": pre_root,
            "post_root": post_root,
            "certificate_id": certificate.id,
            "before": before,
            "after": after,
            "vectors_removed": sum(1 for r in records if r.vector_id is None and r.is_deleted),
            "remaining_records": after["records"],
            "model_version": model.version,
            "dataset_version": dataset.version,
            **scrub,
        }

    # ------------------------------------------------------------------ helpers

    async def _dataset_root(self, dataset_id: str) -> str:
        records = await self.datasets.get_records(dataset_id, include_deleted=True)
        leaves = [leaf_hash(r.id, r.content_hash, deleted=r.is_deleted) for r in records]
        return MerkleTree(leaves).root

    async def _scrub_model(
        self,
        model: MLModel,
        dataset: Any,
        shard_indices: list[int],
        records: list[DatasetRecord],
        method: str,
    ) -> dict[str, Any]:
        record_ids = {r.id for r in records}
        if method == "retrain":
            return await self.sisa.retrain_shards(model, dataset, shard_indices)
        if method in {"certified", "influence"}:
            return await self._weight_scrub(model, dataset, shard_indices, record_ids, method)
        raise ValidationFailedError(f"Unknown method: {method}")

    async def _weight_scrub(
        self,
        model: MLModel,
        dataset: Any,
        shard_indices: list[int],
        record_ids: set[str],
        method: str,
    ) -> dict[str, Any]:
        """In-place parameter scrub (certified Newton step or influence gradient)."""
        results: dict[str, Any] = {"updated_shards": [], "certified_bound": None}
        for shard_index in shard_indices:
            shard = await self.models_repo.get_shard(model.id, shard_index)
            if method == "certified":
                outcome = await self.certified.remove_records_from_shard(
                    model, dataset, shard_index, list(record_ids)
                )
                shard.weights_hash = self.sisa.serialize_weights(outcome.new_weights)
                np.savez(shard.weights_path, weights=outcome.new_weights)
                results["certified_bound"] = outcome.certified_bound
                results["weight_delta_norm"] = outcome.weight_delta_norm
            else:  # influence-guided reverse gradient scrub
                active = await self.datasets.get_records(
                    dataset.id, shard_id=shard_index, include_deleted=False
                )
                if active:
                    X, y, _ = self.sisa.build_design_matrix(
                        active, dataset.feature_names, encoder=self.sisa.load_encoder(model)
                    )
                    classes = np.unique(y)
                    positive_class = classes[1] if len(classes) > 1 else classes[0]
                    y_bin = self.sisa.binary_labels(y, positive_class)
                    clf = (await self.sisa.load_shard_models(model, [shard_index]))[shard_index]
                    proba = clf.predict_proba(X)[:, 1]
                    grad = np.zeros(X.shape[1])
                    removed_count = 0
                    for record, x, p, yv in zip(active, X, proba, y_bin):
                        if record.id in record_ids:
                            grad += self.influence.point_gradient(x, float(yv), float(p))
                            removed_count += 1
                    weights = clf.weights().copy()
                    # First-order scrub: step scaled by the fraction of the
                    # shard being removed, so a few records cause a small,
                    # utility-preserving correction.
                    fraction = removed_count / max(len(active), 1)
                    eta = fraction * np.linalg.norm(weights[1:]) / (np.linalg.norm(grad) + 1e-12)
                    weights[1:] -= eta * grad
                    shard.weights_hash = self.sisa.serialize_weights(weights)
                    np.savez(shard.weights_path, weights=weights)
                    results["gradient_norm"] = float(np.linalg.norm(grad))
            shard.record_version += 1
            shard.retrained_at = datetime.now(timezone.utc).replace(tzinfo=None)
            results["updated_shards"].append(shard_index)

        all_shards = await self.models_repo.get_shards(model.id)
        model.weights_hash = sha256_hex(
            canonical_json(
                {f"shard_{sh.shard_index}": sh.weights_hash for sh in all_shards}
            )
        )
        await self.session.flush()
        return results

    # ------------------------------------------------------------------ full reset

    async def full_identity_reset(
        self, *, identity_key: str, requested_by: str, deletion_type: str = "identity_reset"
    ) -> DeletionRequest:
        """Complete identity reset: every record of the identity across all
        datasets/shards, plus all embeddings. Adaptor removal is handled by the
        LLM backend when such a model is deployed."""
        from app.services.privacy import decrypt_profile  # local import avoids cycle

        result = await self.session.execute(
            select(DatasetRecord).where(DatasetRecord.identity_key == identity_key)
        )
        records = list(result.scalars().all())
        if not records:
            raise NotFoundError(f"No records for identity '{identity_key}'")

        datasets_affected = sorted({r.dataset_id for r in records})
        request = DeletionRequest(
            identity_key=identity_key,
            subject_label=decrypt_profile(records[0])["full_name"] or identity_key,
            deletion_type=deletion_type,
            method="retrain",
            scope={"datasets_affected": datasets_affected, "all_datasets": True},
            record_ids=[r.id for r in records],
            requested_by=requested_by,
        )
        request = await self.deletions.create(request)
        await self.audit.log(
            event_type="unlearning.requested",
            actor=requested_by,
            subject=identity_key,
            payload={"request_id": request.id, "type": deletion_type, "records": len(records)},
        )
        return request
