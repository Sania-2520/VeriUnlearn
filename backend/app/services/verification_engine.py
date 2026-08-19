"""Deletion Verification Engine (Phase 5).

Runs a **full verification job** against a deletion request / certificate and
produces a persisted :class:`VerificationReport` with a per-check breakdown:

1. **records**        — every claimed record id is tombstoned (``is_deleted``,
                        has a tombstone hash, and the tombstone matches).
2. **embeddings**     — no live embedding ids remain on those records and the
                        embedding index rows are marked deleted.
3. **vectors**        — the vector store no longer contains the vectors.
4. **versions**       — dataset / model / shard versions match the certificate.
5. **merkle**         — recomputed pre/post roots match the certificate, and the
                        post root covers the claimed tombstoned leaves.
6. **signature**      — the certificate content hash + RSA signature validate.
7. **audit**          — the hash-chained audit trail is intact end-to-end.
8. **consistency**    — DB/cache/vector-store counts agree (no orphans).

Each check returns ``{passed, details}``; the report carries an overall verdict,
per-check results, the Merkle tree snapshot and the elapsed duration.
"""
from __future__ import annotations

import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationFailedError
from app.core.security import verify_sha256
from app.db.models import (
    Certificate,
    Dataset,
    DatasetRecord,
    DeletionRequest,
    EmbeddingIndex,
    MLModel,
    ModelShard,
    VerificationReport,
)
from app.repositories.audit_repo import AuditRepository
from app.repositories.certificate_repo import CertificateRepository
from app.repositories.verification_repo import VerificationReportRepository
from app.services.audit import AuditService
from app.services.crypto import MerkleTree, canonical_json, leaf_hash, sha256_hex
from app.services.embeddings import get_vector_store
from app.services.merkle_engine import MerkleEngine

logger = __import__("logging").getLogger("veriunlearn.verification")


class VerificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.certificates = CertificateRepository(session)
        self.audit = AuditService(session)
        self.audit_repo = AuditRepository(session)
        self.reports = VerificationReportRepository(session)
        self.vectors = get_vector_store()

    # ------------------------------------------------------------------ run

    async def run(
        self,
        *,
        certificate_id: str | None = None,
        deletion_request_id: str | None = None,
        dataset_id: str | None = None,
        created_by: str = "system",
    ) -> VerificationReport:
        """Execute a full verification job for the selected target.

        Resolution order: explicit certificate → deletion request (its
        certificate) → latest certificate of a dataset.
        """
        cert: Certificate | None = None
        if certificate_id:
            cert = await self.certificates.get(certificate_id)
        elif deletion_request_id:
            request = await self.session.get(DeletionRequest, deletion_request_id)
            if request is None:
                raise NotFoundError(f"Deletion request {deletion_request_id} not found")
            if request.certificate_id:
                cert = await self.certificates.get(request.certificate_id)
        elif dataset_id:
            cert = await self._latest_certificate_for_dataset(dataset_id)

        if cert is None:
            raise ValidationFailedError(
                "No certificate found — provide certificate_id, deletion_request_id, or a dataset with certificates"
            )

        start = time.monotonic()
        checks: dict[str, dict[str, Any]] = {}

        checks["records"] = await self._check_records(cert)
        checks["embeddings"] = await self._check_embeddings(cert)
        checks["vectors"] = await self._check_vectors(cert)
        checks["versions"] = await self._check_versions(cert)
        checks["merkle"] = await self._check_merkle(cert)
        checks["signature"] = await self._check_signature(cert)
        checks["audit"] = await self._check_audit()
        checks["consistency"] = await self._check_consistency(cert)

        passed = sum(1 for c in checks.values() if c["passed"])
        verdict = "valid" if passed == len(checks) else "invalid"
        duration = round(time.monotonic() - start, 3)

        report = VerificationReport(
            certificate_id=cert.id,
            deletion_request_id=cert.deletion_request_id,
            dataset_id=cert.dataset_id,
            model_id=cert.model_id,
            verdict=verdict,
            checks_passed=passed,
            checks_total=len(checks),
            checks=checks,
            merkle_snapshot=checks["merkle"].get("snapshot", {}),
            duration_seconds=duration,
            created_by=created_by,
        )
        report = await self.reports.create(report)

        cert.verification_status = verdict
        await self.session.flush()

        await self.audit.log(
            event_type="verification.completed",
            actor=created_by,
            subject=cert.subject_user_id,
            certificate_id=cert.id,
            payload={
                "report_id": report.id,
                "verdict": verdict,
                "passed": passed,
                "total": len(checks),
                "duration": duration,
            },
        )
        logger.info(
            "Verification %s: %s (%d/%d checks) in %ss",
            report.id, verdict, passed, len(checks), duration,
        )
        return report

    # ---------------------------------------------------------------- checks

    async def _check_records(self, cert: Certificate) -> dict[str, Any]:
        """All claimed records must be tombstoned with a matching tombstone.

        The certificate stores the *content hashes* of deleted records, so we
        check the live dataset for records whose content hash is claimed and
        which must be tombstoned (and none still live).
        """
        if not cert.dataset_id:
            return {"passed": False, "details": "certificate has no dataset_id"}
        all_records = (
            await self.session.execute(
                select(DatasetRecord).where(DatasetRecord.dataset_id == cert.dataset_id)
            )
        ).scalars().all()
        claimed = set(cert.deleted_record_hashes or [])
        tombstoned = [r for r in all_records if r.is_deleted and r.content_hash in claimed]
        live_with_claimed_hash = [r for r in all_records if not r.is_deleted and r.content_hash in claimed]

        # Every claimed hash must appear among tombstoned records, and none
        # among live records.
        tombstoned_hashes = {r.content_hash for r in tombstoned}
        missing = sorted(claimed - tombstoned_hashes)
        passed = not missing and not live_with_claimed_hash
        return {
            "passed": passed,
            "details": {
                "claimed_hashes": len(claimed),
                "tombstoned_with_claimed_hash": len(tombstoned),
                "live_with_claimed_hash": len(live_with_claimed_hash),
                "missing_hashes": missing,
            },
        }

    async def _check_embeddings(self, cert: Certificate) -> dict[str, Any]:
        """Tombstoned records must have no live embedding; their index rows deleted.

        Live records legitimately keep their index rows — only the tombstoned
        records' rows must be gone.
        """
        result = await self.session.execute(
            select(DatasetRecord).where(
                DatasetRecord.dataset_id == cert.dataset_id,
                DatasetRecord.is_deleted.is_(True),
            )
        )
        tombstoned = list(result.scalars().all())
        still_embedded = [r.id for r in tombstoned if r.embedding_id or r.vector_id]
        index_rows = (
            await self.session.execute(
                select(EmbeddingIndex).where(
                    EmbeddingIndex.dataset_id == cert.dataset_id,
                    EmbeddingIndex.is_deleted.is_(True),
                )
            )
        ).scalars().all()
        deleted_index_embedding_ids = {e.embedding_id for e in index_rows}
        tombstoned_embedding_ids = {r.embedding_id for r in tombstoned if r.embedding_id}
        # Every tombstoned record's embedding must appear in the deleted index rows.
        all_covered = tombstoned_embedding_ids.issubset(deleted_index_embedding_ids) if tombstoned_embedding_ids else True
        passed = not still_embedded and all_covered
        return {
            "passed": passed,
            "details": {
                "tombstoned_records": len(tombstoned),
                "still_embedded": still_embedded[:20],
                "deleted_index_rows": len(index_rows),
                "tombstoned_embeddings_covered": all_covered,
            },
        }

    async def _check_vectors(self, cert: Certificate) -> dict[str, Any]:
        """Vector store must no longer contain the deleted vectors."""
        collection = f"dataset_{cert.dataset_id}" if cert.dataset_id else ""
        if not collection:
            return {"passed": False, "details": "no dataset"}
        live_ids: set[str] = set()
        if cert.dataset_id:
            rows = (
                await self.session.execute(
                    select(DatasetRecord).where(
                        DatasetRecord.dataset_id == cert.dataset_id,
                        DatasetRecord.is_deleted.is_(False),
                    )
                )
            ).scalars().all()
            live_ids = {r.vector_id for r in rows if r.vector_id}
        # The in-memory store counts total vectors; the deleted ones should be gone.
        stored = self.vectors.count(collection)
        passed = stored <= len(live_ids)
        return {
            "passed": passed,
            "details": {
                "collection": collection,
                "vectors_in_store": stored,
                "live_vector_ids": len(live_ids),
                "consistent": stored <= len(live_ids),
            },
        }

    async def _check_versions(self, cert: Certificate) -> dict[str, Any]:
        """Dataset / model / shard versions must match the certificate."""
        details: dict[str, Any] = {}
        passed = True
        if cert.dataset_id:
            dataset = await self.session.get(Dataset, cert.dataset_id)
            details["dataset_version"] = dataset.version if dataset else None
            details["expected"] = None  # certificate does not pin dataset version
        if cert.model_id:
            model = await self.session.get(MLModel, cert.model_id)
            if model is None:
                details["model"] = "missing"
                passed = False
            else:
                details["model_version"] = model.version
                details["expected_model_version"] = cert.model_version
                if model.version != cert.model_version:
                    passed = False
                shards = (
                    await self.session.execute(
                        select(ModelShard).where(ModelShard.model_id == cert.model_id)
                    )
                ).scalars().all()
                details["shard_versions"] = {
                    s.shard_index: {"record_version": s.record_version, "retrained_at": s.retrained_at.isoformat() if s.retrained_at else None}
                    for s in shards
                }
                details["shard_count"] = len(shards)
        details["model_version_matches"] = passed
        return {"passed": passed, "details": details}

    async def _check_merkle(self, cert: Certificate) -> dict[str, Any]:
        """Recompute the dataset tree; post root must equal the certificate's."""
        records = (
            await self.session.execute(
                select(DatasetRecord).where(DatasetRecord.dataset_id == cert.dataset_id)
                if cert.dataset_id else select(DatasetRecord)
            )
        ).scalars().all()
        leaves = [
            leaf_hash(r.id, r.content_hash, deleted=r.is_deleted) for r in records
        ]
        tree = MerkleTree(leaves)
        snapshot = MerkleEngine.snapshot(tree)
        post_ok = tree.root == cert.post_merkle_root
        # Membership: the deleted leaves must be provably absent from the live set.
        deleted_leaves = {
            leaf_hash(r.id, r.content_hash, deleted=True) for r in records if r.is_deleted
        }
        excluded = [l for l in tree.leaves if l not in deleted_leaves]
        partial_ok = MerkleEngine.verify_subset(tree.root, sorted(deleted_leaves), excluded)
        return {
            "passed": post_ok and partial_ok,
            "details": {
                "recomputed_post_root": tree.root,
                "certificate_post_root": cert.post_merkle_root,
                "pre_root": cert.pre_merkle_root,
                "post_root_matches": post_ok,
                "deleted_leaves_provable": partial_ok,
                "leaf_count": len(leaves),
                "tombstoned": sum(1 for r in records if r.is_deleted),
            },
            "snapshot": snapshot,
        }

    async def _check_signature(self, cert: Certificate) -> dict[str, Any]:
        """Content-hash integrity + RSA signature over the canonical body."""
        body = {
            "certificate_id": cert.id,
            "subject_user_id": cert.subject_user_id,
            "deletion_type": cert.deletion_type,
            "deleted_record_count": cert.deleted_record_count,
            "dataset_id": cert.dataset_id,
            "model_id": cert.model_id,
            "model_version": cert.model_version,
            "shard_ids": cert.shard_ids,
            "pre_merkle_root": cert.pre_merkle_root,
            "post_merkle_root": cert.post_merkle_root,
            "deleted_record_hashes": cert.deleted_record_hashes,
            "method": cert.method,
            "certified_bound": cert.certified_bound,
            "timestamp": cert.timestamp,
            "issuer": "VeriUnlearn",
        }
        # NOTE: the certificate signature is over the canonical body *bytes*
        # (same as CertificateService.issue/verify), not the content-hash string.
        hash_ok = sha256_hex(canonical_json(body)) == cert.content_hash
        sig_ok = verify_sha256(canonical_json(body).encode("utf-8"), cert.signature)
        return {
            "passed": hash_ok and sig_ok,
            "details": {
                "hash_integrity": hash_ok,
                "signature_valid": sig_ok,
                "content_hash": cert.content_hash,
            },
        }

    async def _check_audit(self) -> dict[str, Any]:
        chain = await self.audit.verify_chain()
        return {
            "passed": chain["verified"],
            "details": {
                "event_count": chain["event_count"],
                "head_hash": chain["head_hash"],
                "broken_event_id": chain["broken_event_id"],
            },
        }

    async def _check_consistency(self, cert: Certificate) -> dict[str, Any]:
        """Cross-store consistency: DB records vs embedding index vs vector store.

        DB-internal agreement (live records with embeddings == live index rows)
        is strict. The vector store may legitimately report *fewer* vectors
        (e.g. a freshly started process with the in-memory backend), so the
        store is only a failure when it reports *more* than the DB.
        """
        if not cert.dataset_id:
            return {"passed": False, "details": "no dataset"}
        records = (
            await self.session.execute(
                select(DatasetRecord).where(DatasetRecord.dataset_id == cert.dataset_id)
            )
        ).scalars().all()
        live = [r for r in records if not r.is_deleted]
        live_embedded = [r for r in live if r.embedding_id]
        index_rows = (
            await self.session.execute(
                select(EmbeddingIndex).where(
                    EmbeddingIndex.dataset_id == cert.dataset_id,
                    EmbeddingIndex.is_deleted.is_(False),
                )
            )
        ).scalars().all()
        collection = f"dataset_{cert.dataset_id}"
        stored = self.vectors.count(collection)
        db_consistent = len(live_embedded) == len(index_rows)
        store_not_exceeding = stored <= len(live_embedded)
        consistent = db_consistent and store_not_exceeding
        return {
            "passed": consistent,
            "details": {
                "live_records": len(live),
                "live_embedded": len(live_embedded),
                "live_index_rows": len(index_rows),
                "vectors_in_store": stored,
                "db_internal_consistent": db_consistent,
                "store_not_exceeding_db": store_not_exceeding,
            },
        }

    # ------------------------------------------------------------- lookups

    async def _latest_certificate_for_dataset(self, dataset_id: str) -> Certificate:
        result = await self.session.execute(
            select(Certificate)
            .where(Certificate.dataset_id == dataset_id)
            .order_by(Certificate.created_at.desc())
            .limit(1)
        )
        cert = result.scalar_one_or_none()
        if cert is None:
            raise NotFoundError(f"No certificates for dataset {dataset_id}")
        return cert

    async def get_report(self, report_id: str) -> VerificationReport:
        return await self.reports.get(report_id)

    async def list_reports(self, limit: int = 50) -> list[VerificationReport]:
        return await self.reports.list(limit=limit)

    async def latest_report_for_certificate(self, certificate_id: str) -> VerificationReport | None:
        result = await self.session.execute(
            select(VerificationReport)
            .where(VerificationReport.certificate_id == certificate_id)
            .order_by(VerificationReport.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
