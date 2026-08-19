"""End-to-end vertical slice: ingest → train → audit → unlearn → verify.

Uses a synthetic 600-row dataset with two classes so the whole SISA pipeline
(4 shards, 150 rows each) runs in a couple of seconds.
"""
from __future__ import annotations

import numpy as np
import pytest
from sqlalchemy import select

from app.db.models import DatasetRecord, DeletionRequest, MLModel
from app.repositories.deletion_repo import DeletionRepository
from app.repositories.model_repo import ModelRepository
from app.services.certificate import CertificateService
from app.services.ingestion import IngestionService
from app.services.privacy import PrivacyService
from app.services.sisa import SISAEngine
from app.services.unlearning import UnlearningService
from app.services.zkproof import ZKDeletionProofService


def make_csv(n: int = 600) -> bytes:
    rng = np.random.default_rng(0)
    rows = []
    for i in range(n):
        # Two well-separated classes make LR learning clean and fast.
        cls = i % 2
        a = rng.normal(cls * 2.0, 0.8)
        b = rng.normal(cls * -2.0, 0.8)
        label = "high" if cls == 1 else "low"
        rows.append(f"{a:.4f},{b:.4f},{label}")
    return ("a,b,income\n" + "\n".join(rows)).encode()


async def build_pipeline(session_factory, n: int = 600) -> dict:
    async with session_factory() as session:
        dataset = await IngestionService(session).ingest_csv_bytes(
            make_csv(n),
            name="synthetic",
            label_column="income",
            shard_count=4,
        )
        model = MLModel(name="synth-v1", model_type="linear", dataset_id=dataset.id, shard_count=4)
        model = await ModelRepository(session).add(model)
        model = await SISAEngine(session).train_model(model, dataset)
        await session.commit()
        return {"dataset_id": dataset.id, "model_id": model.id}


@pytest.mark.asyncio
async def test_full_flow(session_factory):
    await build_pipeline(session_factory)
    async with session_factory() as session:
        # --- identity search ---
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        assert matches, "identity search should find records"
        target = matches[0]
        identity_key = target["identity_key"]

        # --- footprint ---
        footprint = await privacy.identity_footprint(identity_key)
        assert footprint["active_records"] >= 1
        assert footprint["identity_key"] == identity_key
        assert "knowledge_clusters" in footprint

        # --- selective unlearning (SISA retrain) ---
        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=identity_key,
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[target["record_id"]],
            requested_by="test-user",
        )
        request = await DeletionRepository(session).create(request)
        result = await service.execute(request.id)
        assert result["certificates"], "expected at least one certificate"

        # --- record tombstoned ---
        result = await session.execute(
            select(DatasetRecord).where(DatasetRecord.id == target["record_id"])
        )
        record = result.scalar_one()
        assert record.is_deleted is True
        assert record.tombstone_hash

        # --- certificate verify ---
        request = await DeletionRepository(session).get(request.id)
        cert = await CertificateService(session).repo.get(request.certificate_id)
        verdict = await CertificateService(session).verify(cert)
        assert verdict["verified"] is True, verdict

        # --- ZK proof verifies ---
        assert ZKDeletionProofService.verify(cert.zk_proof)

        # --- search no longer surfaces the deleted identity records ---
        matches_after = await privacy.search_identities(target["full_name"].split()[0])
        assert all(m["record_id"] != target["record_id"] for m in matches_after)


@pytest.mark.asyncio
async def test_certified_method(session_factory):
    ctx = await build_pipeline(session_factory, n=400)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        target = (await privacy.search_identities("a"))[0]
        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="certified",
            record_ids=[target["record_id"]],
            requested_by="test-user",
        )
        request = await DeletionRepository(session).create(request)
        result = await service.execute(request.id)
        dataset_result = result[ctx["dataset_id"]]
        assert dataset_result.get("certified_bound") is not None
        assert dataset_result["certified_bound"] >= 0

        request = await DeletionRepository(session).get(request.id)
        cert = await CertificateService(session).repo.get(request.certificate_id)
        assert cert.certified_bound == dataset_result["certified_bound"]


@pytest.mark.asyncio
async def test_influence_method(session_factory):
    await build_pipeline(session_factory, n=400)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        target = (await privacy.search_identities("a"))[0]
        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="influence",
            record_ids=[target["record_id"]],
            requested_by="test-user",
        )
        request = await DeletionRepository(session).create(request)
        result = await service.execute(request.id)
        assert result["certificates"]
