"""Privacy Auditor engine (Phase 3).

- ``search_identities`` : scan every dataset/shard for an identity across many
  field types (name, email, phone, Aadhaar, PAN, passport, customer/employee
  id, record id, chat id, metadata) with computed confidence.
- ``scan_all``          : full-dataset privacy scan (PII categories + severity)
  producing persisted :class:`PrivacyReport` rows.
- ``identity_footprint``: full memory footprint of one identity.
- ``get_record_detail`` : record viewer payload.
- ``recompute_dataset_roots`` : re-derive current Merkle roots from DB state
  (used by certificate verification).
"""
from __future__ import annotations

import difflib
import json
import re
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.security import aes_decrypt
from app.db.models import (
    Dataset,
    DatasetRecord,
    IdentityIndex,
    MLModel,
    PrivacyReport,
    SearchHistory,
)
from app.repositories.dataset_repo import DatasetRepository
from app.repositories.model_repo import ModelRepository
from app.services.crypto import MerkleTree, leaf_hash
from app.services.embeddings import get_vector_store
from app.services.pii import identity_key
from app.services.pii_detection import PIIDetectionEngine

_ENGINE = PIIDetectionEngine()


def decrypt_profile(record: DatasetRecord) -> dict[str, str]:
    """Decrypt PII fields stored at rest (AES-256-GCM)."""
    return {
        "full_name": aes_decrypt(record.full_name_enc) if record.full_name_enc else "",
        "email": aes_decrypt(record.email_enc) if record.email_enc else "",
        "phone": aes_decrypt(record.phone_enc) if record.phone_enc else "",
        "aadhaar": aes_decrypt(record.aadhaar_enc) if record.aadhaar_enc else "",
        "pan": aes_decrypt(record.pan_enc) if record.pan_enc else "",
        "passport": aes_decrypt(record.passport_enc) if record.passport_enc else "",
        "dob": aes_decrypt(record.dob_enc) if record.dob_enc else "",
        "address": aes_decrypt(record.address_enc) if record.address_enc else "",
    }


def _normalize(value: str) -> str:
    """Strip formatting noise for stable matching (phones, ids)."""
    return re.sub(r"[\s\-+.]", "", value).lower()


class PrivacyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.datasets = DatasetRepository(session)
        self.models = ModelRepository(session)
        self.vectors = get_vector_store()

    # ------------------------------------------------------------------ search

    async def search_identities(
        self,
        query: str = "",
        *,
        limit: int = 50,
        identity_key_filter: str | None = None,
        filters: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search across every dataset/shard for an identity.

        ``query`` is matched against name, email, phone, Aadhaar, PAN,
        passport, customer/employee id, record id, chat id and metadata.
        Structured ``filters`` (e.g. ``{"aadhaar": "..."}``) narrow the scan.
        """
        query = (query or "").strip().lower()
        filters = filters or {}
        exact_key = identity_key_filter or (identity_key(query.replace(" ", "")) if query else None)

        result = await self.session.execute(
            select(DatasetRecord).where(DatasetRecord.is_deleted.is_(False))
        )
        records = list(result.scalars().all())
        datasets = {d.id: d for d in await self._all_datasets()}
        models = await self._active_models_by_dataset()

        q_norm = _normalize(query) if query else ""
        matches: list[dict[str, Any]] = []
        seen: set[str] = set()

        for record in records:
            profile = decrypt_profile(record)
            confidence, matched_field = self._match_record(
                record, profile, query, q_norm, exact_key, filters
            )
            if confidence <= 0:
                continue
            if record.id in seen:
                continue
            seen.add(record.id)

            dataset = datasets.get(record.dataset_id)
            model = models.get(record.dataset_id)
            matches.append(
                {
                    "record_id": record.id,
                    "identity_key": record.identity_key,
                    "full_name": profile["full_name"],
                    "email": profile["email"],
                    "phone": profile["phone"],
                    "aadhaar": profile["aadhaar"],
                    "pan": profile["pan"],
                    "passport": profile["passport"],
                    "dob": profile["dob"],
                    "address": profile["address"],
                    "customer_id": str(record.features.get("customer_id") or ""),
                    "employee_id": str(record.features.get("employee_id") or ""),
                    "chat_id": record.chat_id,
                    "matched_field": matched_field,
                    "confidence": round(min(confidence, 1.0), 4),
                    "source": dataset.name if dataset else "unknown",
                    "dataset_id": record.dataset_id,
                    "model_id": model.id if model else None,
                    "model_version": model.version if model else None,
                    "shard_id": record.shard_id,
                    "sensitivity": record.sensitivity,
                    "influence_score": record.influence_score,
                    "has_embedding": record.embedding_id is not None,
                    "embedding_id": record.embedding_id,
                    "vector_id": record.vector_id,
                    "adapter": model.adapters[0] if model and model.adapters else None,
                    "is_deleted": record.is_deleted,
                }
            )
            if len(matches) >= limit:
                break

        matches.sort(key=lambda m: m["confidence"], reverse=True)

        # Persist search history (frontend Search History page).
        if user_id:
            self.session.add(
                SearchHistory(
                    user_id=user_id,
                    query=query[:255],
                    filters=filters,
                    result_count=len(matches),
                )
            )
            await self.session.flush()
        return matches

    @staticmethod
    def _match_record(
        record: DatasetRecord,
        profile: dict[str, str],
        query: str,
        q_norm: str,
        exact_key: str | None,
        filters: dict[str, Any],
    ) -> tuple[float, str]:
        """Return ``(confidence, matched_field)`` or ``(0, "")`` if unmatched."""
        if exact_key and record.identity_key == exact_key:
            return 1.0, "identity_key"
        if filters:
            best = 0.0
            field = ""
            for key, expected in filters.items():
                if expected is None:
                    continue
                expected_s = str(expected)
                if key == "record_id":
                    if record.id == expected_s:
                        return 1.0, "record_id"
                elif key == "chat_id":
                    if record.chat_id == expected_s:
                        return 0.95, "chat_id"
                elif key in {"name", "full_name"}:
                    ratio = difflib.SequenceMatcher(None, expected_s.lower(), profile["full_name"].lower()).ratio()
                    if ratio > best:
                        best, field = ratio, "full_name"
                elif key == "email":
                    if expected_s.lower() in profile["email"].lower():
                        return 0.95, "email"
                else:
                    value = profile.get(key, "")
                    if value and _normalize(expected_s) == _normalize(value):
                        return 0.98, key
            if best > 0:
                return best, field
            return 0.0, ""
        if not query:
            return 0.0, ""

        # Generic query: check every field.
        if record.id == query or record.id.startswith(query):
            return 1.0, "record_id"
        if record.chat_id and (record.chat_id == query or query in record.chat_id.lower()):
            return 0.9, "chat_id"
        if query in profile["full_name"].lower():
            ratio = difflib.SequenceMatcher(None, query, profile["full_name"].lower()).ratio()
            return max(ratio, 0.7), "full_name"
        if query in profile["email"].lower():
            return 0.95, "email"
        for field in ("phone", "aadhaar", "pan", "passport"):
            value = profile.get(field, "")
            if value and _normalize(value) == q_norm:
                return 0.98, field
            if value and q_norm and q_norm in _normalize(value):
                return 0.8, field
        if query in profile["dob"].lower() or query in profile["address"].lower():
            return 0.7, "address" if query in profile["address"].lower() else "dob"
        # Metadata (feature values).
        for key, value in record.features.items():
            if value is not None and query in str(value).lower():
                return 0.6, key
        return 0.0, ""

    # ------------------------------------------------------------------ scan

    async def scan_all(
        self, *, dataset_id: str | None = None, identity_key_filter: str | None = None, created_by: str
    ) -> PrivacyReport:
        """Full privacy scan over active records → persisted PrivacyReport."""
        stmt = select(DatasetRecord).where(DatasetRecord.is_deleted.is_(False))
        if dataset_id:
            stmt = stmt.where(DatasetRecord.dataset_id == dataset_id)
        if identity_key_filter:
            stmt = stmt.where(DatasetRecord.identity_key == identity_key_filter)
        result = await self.session.execute(stmt)
        records = list(result.scalars().all())

        findings_out: list[dict[str, Any]] = []
        counts: dict[str, int] = {}
        critical = high = medium = low = 0
        for record in records:
            profile = decrypt_profile(record)
            text = record.original_text or json.dumps(record.features, default=str)
            analysis = _ENGINE.analyze(text, record.features)
            # Update per-record sensitivity from the strongest finding.
            record.sensitivity = max(record.sensitivity, analysis.max_severity)
            for f in analysis.findings:
                counts[f.category] = counts.get(f.category, 0) + 1
                if f.severity == "critical":
                    critical += 1
                elif f.severity == "high":
                    high += 1
                elif f.severity == "medium":
                    medium += 1
                else:
                    low += 1
                findings_out.append(
                    {
                        "record_id": record.id,
                        "identity_key": record.identity_key,
                        "full_name": profile["full_name"],
                        "dataset_id": record.dataset_id,
                        "shard_id": record.shard_id,
                        **f.to_dict(),
                    }
                )

        # Cap stored findings to keep reports light; aggregate counts remain exact.
        stored_findings = findings_out[:5000]
        risk_score = round(
            min(100.0, (critical * 20 + high * 10 + medium * 4 + low * 1) / max(len(records), 1)), 1
        )
        report = PrivacyReport(
            dataset_id=dataset_id,
            scope="dataset" if dataset_id else ("identity" if identity_key_filter else "all"),
            subject=identity_key_filter,
            scanned_records=len(records),
            findings_count=len(findings_out),
            critical_count=critical,
            high_count=high,
            medium_count=medium,
            low_count=low,
            categories=counts,
            risk_score=risk_score,
            findings=stored_findings,
            created_by=created_by,
        )
        self.session.add(report)
        await self.session.flush()
        return report

    async def get_report(self, report_id: str) -> PrivacyReport:
        report = await self.session.get(PrivacyReport, report_id)
        if report is None:
            raise NotFoundError(f"Privacy report {report_id} not found")
        return report

    async def get_record_detail(self, record_id: str) -> dict[str, Any]:
        """Record viewer payload: text, metadata, file, dataset, hashes."""
        record = await self.datasets.get_record(record_id)
        dataset = await self.datasets.get(record.dataset_id)
        profile = decrypt_profile(record)
        findings = _ENGINE.analyze(
            record.original_text or json.dumps(record.features, default=str), record.features
        ).to_dict()
        return {
            "record_id": record.id,
            "identity_key": record.identity_key,
            "full_name": profile["full_name"],
            "email": profile["email"],
            "phone": profile["phone"],
            "aadhaar": profile["aadhaar"],
            "pan": profile["pan"],
            "passport": profile["passport"],
            "dob": profile["dob"],
            "address": profile["address"],
            "customer_id": str(record.features.get("customer_id") or ""),
            "employee_id": str(record.features.get("employee_id") or ""),
            "original_text": record.original_text,
            "metadata": record.features,
            "label": record.label,
            "file_name": record.source_filename,
            "dataset_id": dataset.id,
            "dataset_name": dataset.name,
            "timestamp": record.source_timestamp.isoformat() if record.source_timestamp else None,
            "chat_id": record.chat_id,
            "chunk_index": record.chunk_index,
            "chunk_id": f"chunk-{dataset.id}-{record.record_index}",
            "embedding_id": record.embedding_id,
            "vector_id": record.vector_id,
            "content_hash": record.content_hash,
            "shard_id": record.shard_id,
            "is_deleted": record.is_deleted,
            "influence_score": record.influence_score,
            "sensitivity": record.sensitivity,
            "pii_findings": findings,
        }

    # ------------------------------------------------------------------ footprint

    async def identity_footprint(self, identity: str) -> dict[str, Any]:
        key = identity_key(identity)
        result = await self.session.execute(
            select(DatasetRecord).where(DatasetRecord.identity_key == key)
        )
        records = list(result.scalars().all())
        if not records:
            raise LookupError(f"No records found for identity '{identity}'")

        first = decrypt_profile(records[0])
        active = [r for r in records if not r.is_deleted]
        deleted = [r for r in records if r.is_deleted]

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

        # Privacy risk of this identity's records (from stored scan findings if
        # available, otherwise computed inline).
        sensitivity_score, severity_counts = await self._identity_risk(active)

        return {
            "identity_key": key,
            "full_name": first["full_name"],
            "email": first["email"],
            "phone": first["phone"],
            "aadhaar": first["aadhaar"],
            "pan": first["pan"],
            "passport": first["passport"],
            "dob": first["dob"],
            "address": first["address"],
            "customer_id": str(active[0].features.get("customer_id") or "") if active else "",
            "employee_id": str(active[0].features.get("employee_id") or "") if active else "",
            "total_records": len(records),
            "active_records": len(active),
            "deleted_records": len(deleted),
            "datasets_affected": sorted({r.dataset_id for r in records}),
            "record_ids": [r.id for r in records],
            "chat_ids": sorted({r.chat_id for r in active if r.chat_id}),
            "associated_files": sorted({r.source_filename for r in records if r.source_filename}),
            "embedding_ids": [r.embedding_id for r in active if r.embedding_id],
            "vector_ids": [r.vector_id for r in active if r.vector_id],
            "knowledge_chunks": [f"chunk-{r.dataset_id}-{r.record_index}" for r in active],
            "knowledge_clusters": clusters,
            "affected_neurons": neurons,
            "adapters": [],
            "data_importance": {
                "mean_influence": round(float(np.mean(influence_scores)), 6) if influence_scores else None,
                "max_influence": round(float(np.max(influence_scores)), 6) if influence_scores else None,
                "influence_scores": {r.id: r.influence_score for r in active if r.influence_score is not None},
            },
            "sensitivity": sorted({r.sensitivity for r in records}),
            "sensitivity_score": sensitivity_score,
            "privacy_severity_counts": severity_counts,
            "deletion_eligible": await self._deletion_eligible(active),
            "model_memory_footprint_bytes": sum(len(r.features) * 64 for r in records),
        }

    async def _deletion_eligible(self, records: list[DatasetRecord]) -> bool:
        if not records:
            return False
        for record in records:
            if await self.models.get_active_for_dataset(record.dataset_id):
                return True
        return False

    async def _identity_risk(self, records: list[DatasetRecord]) -> tuple[float, dict[str, int]]:
        """Aggregate PII severity over the identity's active records."""
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for record in records:
            analysis = _ENGINE.analyze(
                record.original_text or json.dumps(record.features, default=str), record.features
            )
            severity_counts[analysis.max_severity] += 1
        score = min(
            100.0,
            severity_counts["critical"] * 25 + severity_counts["high"] * 10
            + severity_counts["medium"] * 4 + severity_counts["low"],
        )
        return round(score, 1), severity_counts

    # ------------------------------------------------------------------ overview / index

    async def privacy_overview(self) -> dict[str, Any]:
        datasets = await self._all_datasets()
        identities = (
            await self.session.execute(select(IdentityIndex))
        ).scalars().all()
        reports = (
            await self.session.execute(select(PrivacyReport).order_by(PrivacyReport.created_at.desc()))
        ).scalars().all()
        report_counts = {
            "total": len(reports),
            "critical": sum(r.critical_count for r in reports),
            "high": sum(r.high_count for r in reports),
            "medium": sum(r.medium_count for r in reports),
            "low": sum(r.low_count for r in reports),
        }
        return {
            "datasets": len(datasets),
            "records": sum(d.record_count for d in datasets),
            "identities_indexed": len(identities),
            "reports": report_counts,
            "recent_reports": [
                {
                    "id": r.id,
                    "scope": r.scope,
                    "subject": r.subject,
                    "scanned_records": r.scanned_records,
                    "findings_count": r.findings_count,
                    "risk_score": r.risk_score,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in reports[:10]
            ],
        }

    async def list_reports(self, limit: int = 50) -> list[PrivacyReport]:
        result = await self.session.execute(
            select(PrivacyReport).order_by(PrivacyReport.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def list_history(self, user_id: str, limit: int = 50) -> list[SearchHistory]:
        result = await self.session.execute(
            select(SearchHistory)
            .where(SearchHistory.user_id == user_id)
            .order_by(SearchHistory.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

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
    """Re-derive current Merkle roots from live DB state."""
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
