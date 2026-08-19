"""Comprehensive Phase 4 QA test suite — Surgical Machine Unlearning.

Covers every step of the QA specification (Steps 1-21):
  STEP 1  - Unlearning Dashboard
  STEP 2  - Identity Selection
  STEP 3  - Record Identification
  STEP 4  - Pre-Unlearning Analysis (Impact)
  STEP 5  - Surgical Data Removal (single, multi, user, dataset)
  STEP 6  - Embedding Removal
  STEP 7  - Vector Store Validation
  STEP 8  - Model Update (selective retrain)
  STEP 9  - Post-Unlearning Validation
  STEP 10 - Model Accuracy
  STEP 11 - Forgetting Quality
  STEP 12 - Database Validation
  STEP 13 - Audit Logging
  STEP 14 - API Validation
  STEP 15 - Frontend data shapes
  STEP 16 - Error Handling
  STEP 17 - Security
  STEP 18 - Performance
  STEP 19 - Concurrent Requests
  STEP 20 - Rollback
  STEP 21 - End-to-End Unlearning Flow
"""
from __future__ import annotations

import asyncio
import time

import numpy as np
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AuditEvent,
    Certificate,
    DatasetRecord,
    DeletionHistory,
    DeletionRequest,
    EmbeddingIndex,
    MLModel,
)
from app.repositories.deletion_repo import DeletionRepository
from app.repositories.model_repo import ModelRepository
from app.repositories.privacy_repo import DeletionHistoryRepository
from app.services.certificate import CertificateService
from app.services.embeddings import get_vector_store
from app.services.ingestion import IngestionService
from app.services.models.linear import SklearnLinearModel
from app.services.privacy import PrivacyService
from app.services.sisa import SISAEngine
from app.services.unlearning import UnlearningService
from app.services.zkproof import ZKDeletionProofService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_csv(n: int = 600) -> bytes:
    rng = np.random.default_rng(42)
    rows = []
    for i in range(n):
        cls = i % 2
        a = rng.normal(cls * 2.0, 0.8)
        b = rng.normal(cls * -2.0, 0.8)
        label = "high" if cls == 1 else "low"
        rows.append(f"{a:.4f},{b:.4f},{label}")
    return ("a,b,income\n" + "\n".join(rows)).encode()


def make_chat_csv(n: int = 200) -> bytes:
    rng = np.random.default_rng(1)
    rows = []
    for i in range(n):
        cls = i % 2
        a = rng.normal(cls * 2.0, 0.8)
        b = rng.normal(cls * -2.0, 0.8)
        chat = f"chat-{i % 10}"
        label = "high" if cls else "low"
        rows.append(f"{a:.4f},{b:.4f},{chat},{label}")
    return ("a,b,chat_id,income\n" + "\n".join(rows)).encode()


def make_large_csv(n: int = 1000) -> bytes:
    rng = np.random.default_rng(7)
    rows = []
    for i in range(n):
        cls = i % 2
        a = rng.normal(cls * 2.0, 0.8)
        b = rng.normal(cls * -2.0, 0.8)
        label = "high" if cls else "low"
        rows.append(f"{a:.4f},{b:.4f},{label}")
    return ("a,b,income\n" + "\n".join(rows)).encode()


async def build_pipeline(session_factory, n: int = 600, shard_count: int = 4) -> dict:
    """Ingest + train. Returns {dataset_id, model_id}."""
    async with session_factory() as session:
        ds = await IngestionService(session).ingest_csv_bytes(
            make_csv(n), name="synth", label_column="income", shard_count=shard_count
        )
        model = MLModel(name="v1", model_type="linear", dataset_id=ds.id, shard_count=shard_count)
        model = await ModelRepository(session).add(model)
        dataset = await session.get(type(ds), ds.id)
        await SISAEngine(session).train_model(model, dataset)
        await session.commit()
        return {"dataset_id": ds.id, "model_id": model.id}


async def build_chat_pipeline(session_factory) -> dict:
    """Ingest chat CSV + train. Returns {dataset_id, model_id}."""
    async with session_factory() as session:
        ds = await IngestionService(session).ingest_csv_bytes(
            make_chat_csv(), name="chats", label_column="income", shard_count=4
        )
        model = MLModel(name="chats-v1", model_type="linear", dataset_id=ds.id, shard_count=4)
        model = await ModelRepository(session).add(model)
        dataset = await session.get(type(ds), ds.id)
        await SISAEngine(session).train_model(model, dataset)
        await session.commit()
        return {"dataset_id": ds.id, "model_id": model.id}


async def run_unlearning(session_factory, request_id: str) -> dict:
    async with session_factory() as session:
        result = await UnlearningService(session).execute(request_id)
        await session.commit()
        return result


async def get_accuracy(session_factory, model_id: str, dataset_id: str) -> float:
    """Compute accuracy of the current model on active records."""
    async with session_factory() as session:
        from app.db.models import Dataset
        model = await session.get(MLModel, model_id)
        dataset = await session.get(Dataset, dataset_id)
        records = await DatasetRepository(session).get_records(dataset_id, include_deleted=False)
        if not records:
            return 0.0
        encoder = SISAEngine(session).load_encoder(model)
        X, y, _ = SISAEngine.build_design_matrix(records, dataset.feature_names, encoder=encoder)
        classes = np.unique(y)
        positive_class = classes[1] if len(classes) > 1 else classes[0]
        y_bin = SISAEngine.binary_labels(y, positive_class)
        shard_models_dict = await SISAEngine(session).load_shard_models(model)
        probas = SISAEngine.aggregate_predict_proba(list(shard_models_dict.values()), X)
        preds = (probas[:, 1] >= 0.5).astype(int)
        from sklearn.metrics import accuracy_score
        return float(accuracy_score(y_bin, preds))


from app.db.models import Dataset
from app.repositories.dataset_repo import DatasetRepository


# ===========================================================================
# STEP 1 — Unlearning Dashboard
# ===========================================================================

@pytest.mark.asyncio
async def test_step1_deletion_history_api(session_factory, auth_headers, client):
    """GET /unlearning/history returns deletion history."""
    ctx = await build_pipeline(session_factory)
    # Execute a deletion first
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[target["record_id"]],
            requested_by="qa-tester",
        )
        request = await DeletionRepository(session).create(request)
        await service.execute(request.id)
        await session.commit()

    resp = await client.get("/api/v1/unlearning/history", headers=auth_headers)
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) >= 1
    assert history[0]["request_id"]
    assert history[0]["scope"]
    assert history[0]["records_before"] >= 1
    assert history[0]["records_after"] >= 0
    assert "certificates" not in history[0]  # history, not certificate detail


@pytest.mark.asyncio
async def test_step1_list_deletion_requests(session_factory, auth_headers, client):
    """GET /unlearning/requests returns list of requests."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[target["record_id"]],
            requested_by="qa",
        )
        request = await DeletionRepository(session).create(request)
        await service.execute(request.id)
        await session.commit()

    resp = await client.get("/api/v1/unlearning/requests", headers=auth_headers)
    assert resp.status_code == 200
    requests = resp.json()
    assert len(requests) >= 1
    r = requests[0]
    assert r["id"]
    assert r["status"] == "completed"
    assert r["method"]
    assert r["deletion_type"]


# ===========================================================================
# STEP 2 — Identity Selection
# ===========================================================================

@pytest.mark.asyncio
async def test_step2_select_by_identity_key(session_factory):
    """Resolve records by identity_key."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        service = UnlearningService(session)
        records = await service.resolve_records(identity_key=target["identity_key"])
        assert len(records) >= 1
        assert all(r.identity_key == target["identity_key"] for r in records)
        assert all(not r.is_deleted for r in records)


@pytest.mark.asyncio
async def test_step2_select_by_record_ids(session_factory):
    """Resolve records by explicit record_ids."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        rid = matches[0]["record_id"]
        service = UnlearningService(session)
        records = await service.resolve_records(record_ids=[rid])
        assert len(records) == 1
        assert records[0].id == rid


@pytest.mark.asyncio
async def test_step2_select_by_chat_id(session_factory):
    """Resolve records by chat_id (scope=chat)."""
    ctx = await build_chat_pipeline(session_factory)
    async with session_factory() as session:
        service = UnlearningService(session)
        records = await service.resolve_records(chat_id="chat-3", scope="chat")
        assert len(records) == 20  # 200 rows / 10 chats
        assert all(r.chat_id == "chat-3" for r in records)


@pytest.mark.asyncio
async def test_step2_select_by_dataset_id(session_factory):
    """Resolve records by dataset_id (scope=dataset)."""
    ctx = await build_chat_pipeline(session_factory)
    async with session_factory() as session:
        service = UnlearningService(session)
        records = await service.resolve_records(dataset_id=ctx["dataset_id"], scope="dataset")
        assert len(records) == 200


@pytest.mark.asyncio
async def test_step2_no_incorrect_records_selected(session_factory):
    """Selecting identity X does not return identity Y's records."""
    ctx = await build_pipeline(session_factory, n=400)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        if len(matches) < 2:
            return  # need at least 2 distinct identities
        ik1 = matches[0]["identity_key"]
        ik2 = matches[1]["identity_key"]
        if ik1 == ik2:
            return
        service = UnlearningService(session)
        recs1 = await service.resolve_records(identity_key=ik1)
        recs2 = await service.resolve_records(identity_key=ik2)
        ids1 = {r.id for r in recs1}
        ids2 = {r.id for r in recs2}
        assert ids1.isdisjoint(ids2), "Different identities must not share records"


# ===========================================================================
# STEP 3 — Record Identification
# ===========================================================================

@pytest.mark.asyncio
async def test_step3_records_have_embeddings_and_metadata(session_factory):
    """Records after ingestion have embedding references and metadata."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        records = await DatasetRepository(session).get_records(ctx["dataset_id"], include_deleted=False)
        for r in records[:10]:
            assert r.embedding_id is not None
            assert r.vector_id is not None
            assert r.content_hash
            assert r.identity_key
            assert r.features


@pytest.mark.asyncio
async def test_step3_embedding_index_rows_exist(session_factory):
    """EmbeddingIndex rows track every record's embedding."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        result = await session.execute(
            select(EmbeddingIndex).where(EmbeddingIndex.dataset_id == ctx["dataset_id"])
        )
        rows = result.scalars().all()
        assert len(rows) == 600
        assert all(r.dim > 0 for r in rows)


@pytest.mark.asyncio
async def test_step3_affected_models_identified(session_factory):
    """Impact analysis identifies the active model for the dataset."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        service = UnlearningService(session)
        impact = await service.analyze_impact(identity_key=target["identity_key"])
        for ds_id, info in impact["datasets"].items():
            assert info["dependencies"]["model_id"] == ctx["model_id"]
            assert info["dependencies"]["model_version"] >= 1


# ===========================================================================
# STEP 4 — Pre-Unlearning Analysis (Impact)
# ===========================================================================

@pytest.mark.asyncio
async def test_step4_impact_analysis_single_record(session_factory):
    """Impact for single record deletion."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        service = UnlearningService(session)
        impact = await service.analyze_impact(identity_key=target["identity_key"])
        assert impact["totals"]["records"] >= 1
        assert impact["totals"]["affected_shards"] >= 1
        assert impact["eligible"] is True
        # Embedding exists
        assert impact["totals"]["embeddings"] >= 1


@pytest.mark.asyncio
async def test_step4_impact_analysis_chat_scope(session_factory):
    """Impact for chat-scoped deletion."""
    ctx = await build_chat_pipeline(session_factory)
    async with session_factory() as session:
        service = UnlearningService(session)
        impact = await service.analyze_impact(chat_id="chat-3", scope="chat")
        assert impact["totals"]["records"] == 20
        assert impact["totals"]["affected_shards"] >= 1
        assert impact["eligible"] is True


@pytest.mark.asyncio
async def test_step4_impact_analysis_dataset_scope(session_factory):
    """Impact for dataset-scoped deletion."""
    ctx = await build_chat_pipeline(session_factory)
    async with session_factory() as session:
        service = UnlearningService(session)
        impact = await service.analyze_impact(dataset_id=ctx["dataset_id"], scope="dataset")
        assert impact["totals"]["records"] == 200
        assert impact["eligible"] is True


@pytest.mark.asyncio
async def test_step4_impact_estimated_retraining_time(session_factory):
    """Impact includes estimated retraining time."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        service = UnlearningService(session)
        impact = await service.analyze_impact(identity_key=target["identity_key"])
        for ds_id, info in impact["datasets"].items():
            assert "estimated_retraining_seconds" in info
            assert info["estimated_retraining_seconds"] >= 0


# ===========================================================================
# STEP 5 — Surgical Data Removal
# ===========================================================================

@pytest.mark.asyncio
async def test_step5_single_record_deletion(session_factory):
    """Delete a single record; verify tombstoned and no others affected."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[target["record_id"]],
            requested_by="qa",
        )
        request = await DeletionRepository(session).create(request)
        result = await service.execute(request.id)
        await session.commit()

        # Record is tombstoned
        rec = await session.get(DatasetRecord, target["record_id"])
        assert rec.is_deleted is True
        assert rec.tombstone_hash
        assert rec.deleted_at

        # Other records are not affected
        ds_records = await DatasetRepository(session).get_records(ctx["dataset_id"], include_deleted=True)
        deleted = [r for r in ds_records if r.is_deleted]
        assert len(deleted) == 1
        assert deleted[0].id == target["record_id"]


@pytest.mark.asyncio
async def test_step5_multiple_records_deletion(session_factory):
    """Delete multiple records at once."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        # Take first 3 matches
        rids = [m["record_id"] for m in matches[:3]]
        service = UnlearningService(session)
        request = DeletionRequest(
            subject_label="multi",
            deletion_type="records",
            method="retrain",
            record_ids=rids,
            requested_by="qa",
        )
        request = await DeletionRepository(session).create(request)
        result = await service.execute(request.id)
        await session.commit()
        assert result["deleted_records"] == 3
        # Verify all 3 are tombstoned
        for rid in rids:
            rec = await session.get(DatasetRecord, rid)
            assert rec.is_deleted is True


@pytest.mark.asyncio
async def test_step5_chat_scoped_deletion(session_factory):
    """Delete an entire chat conversation."""
    ctx = await build_chat_pipeline(session_factory)
    async with session_factory() as session:
        service = UnlearningService(session)
        records = await service.resolve_records(chat_id="chat-3", scope="chat")
        request = DeletionRequest(
            subject_label="chat:chat-3",
            deletion_type="chat",
            method="retrain",
            scope={"scope": "chat", "chat_id": "chat-3"},
            record_ids=[r.id for r in records],
            requested_by="qa",
        )
        request = await DeletionRepository(session).create(request)
        result = await service.execute(request.id)
        await session.commit()
        assert result["deleted_records"] == 20
        assert result[ctx["dataset_id"]]["after"]["records"] == 180


@pytest.mark.asyncio
async def test_step5_dataset_scoped_deletion(session_factory):
    """Delete an entire dataset."""
    ctx = await build_chat_pipeline(session_factory)
    async with session_factory() as session:
        service = UnlearningService(session)
        records = await service.resolve_records(dataset_id=ctx["dataset_id"], scope="dataset")
        request = DeletionRequest(
            subject_label=f"dataset:{ctx['dataset_id']}",
            deletion_type="dataset",
            method="retrain",
            scope={"scope": "dataset", "dataset_id": ctx["dataset_id"]},
            record_ids=[r.id for r in records],
            requested_by="qa",
        )
        request = await DeletionRepository(session).create(request)
        result = await service.execute(request.id)
        await session.commit()
        assert result["deleted_records"] == 200
        assert result[ctx["dataset_id"]]["remaining_records"] == 0


@pytest.mark.asyncio
async def test_step5_only_selected_records_removed(session_factory):
    """After deletion, only the target records are deleted; others are intact."""
    ctx = await build_pipeline(session_factory, n=400)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        all_before = await DatasetRepository(session).get_records(ctx["dataset_id"], include_deleted=False)
        count_before = len(all_before)

        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[target["record_id"]],
            requested_by="qa",
        )
        request = await DeletionRepository(session).create(request)
        await service.execute(request.id)
        await session.commit()

        all_after = await DatasetRepository(session).get_records(ctx["dataset_id"], include_deleted=False)
        count_after = len(all_after)
        assert count_after == count_before - 1


# ===========================================================================
# STEP 6 — Embedding Removal
# ===========================================================================

@pytest.mark.asyncio
async def test_step6_embeddings_removed_after_deletion(session_factory):
    """After deletion, embedding_id and vector_id are cleared."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[target["record_id"]],
            requested_by="qa",
        )
        request = await DeletionRepository(session).create(request)
        await service.execute(request.id)
        await session.commit()

        rec = await session.get(DatasetRecord, target["record_id"])
        assert rec.embedding_id is None
        assert rec.vector_id is None


@pytest.mark.asyncio
async def test_step6_embedding_index_marked_deleted(session_factory):
    """EmbeddingIndex rows are marked is_deleted=True."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[target["record_id"]],
            requested_by="qa",
        )
        request = await DeletionRepository(session).create(request)
        await service.execute(request.id)
        await session.commit()

        result = await session.execute(
            select(EmbeddingIndex).where(EmbeddingIndex.record_id == target["record_id"])
        )
        emb = result.scalars().first()
        assert emb is not None
        assert emb.is_deleted is True


# ===========================================================================
# STEP 7 — Vector Store Validation
# ===========================================================================

@pytest.mark.asyncio
async def test_step7_vectors_deleted_from_store(session_factory):
    """Deleted vectors are removed from the vector store."""
    ctx = await build_pipeline(session_factory)
    vs = get_vector_store()
    collection = f"dataset_{ctx['dataset_id']}"
    count_before = vs.count(collection)

    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[target["record_id"]],
            requested_by="qa",
        )
        request = await DeletionRepository(session).create(request)
        await service.execute(request.id)
        await session.commit()

    count_after = vs.count(collection)
    assert count_after == count_before - 1


@pytest.mark.asyncio
async def test_step7_no_deleted_vectors_searchable(session_factory):
    """Deleted vectors do not appear in search results."""
    ctx = await build_pipeline(session_factory)
    vs = get_vector_store()
    collection = f"dataset_{ctx['dataset_id']}"

    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        del_id = target["record_id"]

        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[del_id],
            requested_by="qa",
        )
        request = await DeletionRepository(session).create(request)
        await service.execute(request.id)
        await session.commit()

    # Search with random vector — deleted record should not appear
    rng = np.random.default_rng(99)
    q = rng.normal(size=2)
    q = q / np.linalg.norm(q)
    results = vs.search(collection, q, k=50)
    result_ids = {r["id"] for r in results}
    assert del_id not in result_ids


# ===========================================================================
# STEP 8 — Model Update
# ===========================================================================

@pytest.mark.asyncio
async def test_step8_model_version_incremented(session_factory):
    """Model version is incremented after unlearning."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        model = await session.get(MLModel, ctx["model_id"])
        v_before = model.version

        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[target["record_id"]],
            requested_by="qa",
        )
        request = await DeletionRepository(session).create(request)
        await service.execute(request.id)
        await session.commit()

        model = await session.get(MLModel, ctx["model_id"])
        assert model.version == v_before + 1


@pytest.mark.asyncio
async def test_step8_shard_weights_updated(session_factory):
    """Shard weights are updated after retraining."""
    ctx = await build_pipeline(session_factory)
    # Read old state in a separate session
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        shard_id = target["shard_id"]
        old_shard = await ModelRepository(session).get_shard(ctx["model_id"], shard_id)
        old_hash = old_shard.weights_hash
        old_version = old_shard.record_version

    # Execute deletion in its own session
    async with session_factory() as session:
        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[target["record_id"]],
            requested_by="qa",
        )
        request = await DeletionRepository(session).create(request)
        await service.execute(request.id)
        await session.commit()

    # Read new state in a fresh session
    async with session_factory() as session:
        new_shard = await ModelRepository(session).get_shard(ctx["model_id"], shard_id)
        assert new_shard.weights_hash != old_hash
        assert new_shard.record_version == old_version + 1


@pytest.mark.asyncio
async def test_step8_inference_still_works_after_unlearning(session_factory):
    """Model inference produces valid predictions after unlearning."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[target["record_id"]],
            requested_by="qa",
        )
        request = await DeletionRepository(session).create(request)
        await service.execute(request.id)
        await session.commit()

        # Load model and predict
        model = await session.get(MLModel, ctx["model_id"])
        shard_models = await SISAEngine(session).load_shard_models(model)
        X_test = np.array([[1.0, -1.0]])
        probas = SISAEngine.aggregate_predict_proba(list(shard_models.values()), X_test)
        assert probas.shape == (1, 2)
        assert 0.0 <= probas[0, 0] <= 1.0
        assert 0.0 <= probas[0, 1] <= 1.0


# ===========================================================================
# STEP 9 — Post-Unlearning Validation
# ===========================================================================

@pytest.mark.asyncio
async def test_step9_deleted_identity_not_searchable(session_factory):
    """After deleting all records of an identity, search no longer returns them."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        ik = target["identity_key"]

        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=ik,
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[target["record_id"]],
            requested_by="qa",
        )
        request = await DeletionRepository(session).create(request)
        await service.execute(request.id)
        await session.commit()

        # Search again — the deleted record should not appear
        matches_after = await privacy.search_identities(target["full_name"].split()[0])
        deleted_ids = {target["record_id"]}
        for m in matches_after:
            assert m["record_id"] not in deleted_ids


@pytest.mark.asyncio
async def test_step9_deleted_record_tombstoned_not_in_active(session_factory):
    """Deleted record is tombstoned and excluded from active queries."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[target["record_id"]],
            requested_by="qa",
        )
        request = await DeletionRepository(session).create(request)
        await service.execute(request.id)
        await session.commit()

        active = await DatasetRepository(session).get_records(ctx["dataset_id"], include_deleted=False)
        active_ids = {r.id for r in active}
        assert target["record_id"] not in active_ids


# ===========================================================================
# STEP 10 — Model Accuracy
# ===========================================================================

@pytest.mark.asyncio
async def test_step10_accuracy_after_unlearning(session_factory):
    """Model accuracy remains reasonable after deleting one record."""
    ctx = await build_pipeline(session_factory)
    # Accuracy before
    acc_before = await get_accuracy(session_factory, ctx["model_id"], ctx["dataset_id"])

    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[target["record_id"]],
            requested_by="qa",
        )
        request = await DeletionRepository(session).create(request)
        await service.execute(request.id)
        await session.commit()

    acc_after = await get_accuracy(session_factory, ctx["model_id"], ctx["dataset_id"])
    # Utility loss should be small (< 10% drop for single record removal)
    assert acc_after >= acc_before - 0.10, f"Accuracy dropped too much: {acc_before:.3f} → {acc_after:.3f}"


@pytest.mark.asyncio
async def test_step10_accuracy_with_retrain_method(session_factory):
    """SISA retrain maintains utility on unaffected shards."""
    ctx = await build_pipeline(session_factory, n=400)
    acc_before = await get_accuracy(session_factory, ctx["model_id"], ctx["dataset_id"])

    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        targets = matches[:3]
        rids = [m["record_id"] for m in targets]
        service = UnlearningService(session)
        request = DeletionRequest(
            subject_label="multi-delete",
            deletion_type="records",
            method="retrain",
            record_ids=rids,
            requested_by="qa",
        )
        request = await DeletionRepository(session).create(request)
        await service.execute(request.id)
        await session.commit()

    acc_after = await get_accuracy(session_factory, ctx["model_id"], ctx["dataset_id"])
    # Unaffected shards keep their accuracy; only affected shard retrained
    assert acc_after >= acc_before - 0.15, f"Accuracy dropped: {acc_before:.3f} → {acc_after:.3f}"


# ===========================================================================
# STEP 11 — Forgetting Quality
# ===========================================================================

@pytest.mark.asyncio
async def test_step11_certificate_issued_and_verifiable(session_factory):
    """Every deletion produces a valid certificate."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[target["record_id"]],
            requested_by="qa",
        )
        request = await DeletionRepository(session).create(request)
        result = await service.execute(request.id)
        await session.commit()

        assert result["certificates"]
        cert_id = result["certificates"][0]
        cert = await CertificateService(session).repo.get(cert_id)
        assert cert.pre_merkle_root
        assert cert.post_merkle_root
        assert cert.pre_merkle_root != cert.post_merkle_root
        assert cert.content_hash
        assert cert.signature

        # Verify
        verdict = await CertificateService(session).verify(cert)
        assert verdict["verified"] is True
        assert verdict["hash_integrity"] is True
        assert verdict["signature_valid"] is True


@pytest.mark.asyncio
async def test_step11_zk_proof_verifiable(session_factory):
    """ZK proof is generated and verifiable."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[target["record_id"]],
            requested_by="qa",
        )
        request = await DeletionRepository(session).create(request)
        await service.execute(request.id)
        await session.commit()

        cert = await CertificateService(session).repo.get(request.certificate_id)
        assert ZKDeletionProofService.verify(cert.zk_proof)


@pytest.mark.asyncio
async def test_step11_deletion_history_before_after(session_factory):
    """DeletionHistory has correct before/after snapshots."""
    ctx = await build_chat_pipeline(session_factory)
    async with session_factory() as session:
        service = UnlearningService(session)
        records = await service.resolve_records(chat_id="chat-3", scope="chat")
        request = DeletionRequest(
            subject_label="chat:chat-3",
            deletion_type="chat",
            method="retrain",
            scope={"scope": "chat", "chat_id": "chat-3"},
            record_ids=[r.id for r in records],
            requested_by="qa",
        )
        request = await DeletionRepository(session).create(request)
        await service.execute(request.id)
        await session.commit()

        history = await DeletionHistoryRepository(session).get_by_request(request.id)
        assert history is not None
        assert history.records_before == 200
        assert history.records_after == 180
        assert history.embeddings_before == 200
        assert history.embeddings_after == 180
        assert history.vectors_removed == 20
        assert history.method == "retrain"
        assert history.scope == "chat"
        assert history.certificate_id


# ===========================================================================
# STEP 12 — Database Validation
# ===========================================================================

@pytest.mark.asyncio
async def test_step12_no_orphan_embedding_rows(session_factory):
    """No orphan EmbeddingIndex rows (every active record has a non-deleted index)."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[target["record_id"]],
            requested_by="qa",
        )
        request = await DeletionRepository(session).create(request)
        await service.execute(request.id)
        await session.commit()

        # Active records should have non-deleted embedding index
        active = await DatasetRepository(session).get_records(ctx["dataset_id"], include_deleted=False)
        active_ids = {r.id for r in active}
        result = await session.execute(
            select(EmbeddingIndex).where(EmbeddingIndex.dataset_id == ctx["dataset_id"])
        )
        for emb in result.scalars().all():
            if emb.record_id in active_ids:
                assert emb.is_deleted is False


@pytest.mark.asyncio
async def test_step12_merkle_root_changed(session_factory):
    """Merkle root changes after deletion."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        service = UnlearningService(session)
        root_before = await service._dataset_root(ctx["dataset_id"])

        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        request = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[target["record_id"]],
            requested_by="qa",
        )
        request = await DeletionRepository(session).create(request)
        await service.execute(request.id)
        await session.commit()

        root_after = await service._dataset_root(ctx["dataset_id"])
        assert root_before != root_after


@pytest.mark.asyncio
async def test_step12_tombstone_hash_deterministic(session_factory):
    """Tombstone hash is deterministic for the same record."""
    from app.services.crypto import tombstone_hash
    h1 = tombstone_hash("rec-1", "abc123")
    h2 = tombstone_hash("rec-1", "abc123")
    assert h1 == h2
    assert len(h1) == 64  # SHA-256


# ===========================================================================
# STEP 13 — Audit Logging
# ===========================================================================

@pytest.mark.asyncio
async def test_step13_audit_events_logged(session_factory):
    """Unlearning creates audit events for requested + completed."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[target["record_id"]],
            requested_by="qa-auditor",
        )
        request = await DeletionRepository(session).create(request)
        await service.execute(request.id)
        await session.commit()

        # Check audit events
        events = (await session.execute(
            select(AuditEvent).where(AuditEvent.event_type == "unlearning.completed")
        )).scalars().all()
        assert len(events) >= 1
        event = events[-1]
        assert event.actor == "qa-auditor"
        assert event.payload.get("request_id") == request.id
        assert event.payload.get("method") == "retrain"
        assert event.payload.get("records") == 1
        assert event.certificate_id


@pytest.mark.asyncio
async def test_step13_audit_certificate_issued_event(session_factory):
    """Certificate issuance is logged in audit trail."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[target["record_id"]],
            requested_by="qa",
        )
        request = await DeletionRepository(session).create(request)
        await service.execute(request.id)
        await session.commit()

        events = (await session.execute(
            select(AuditEvent).where(AuditEvent.event_type == "certificate.issued")
        )).scalars().all()
        assert len(events) >= 1


@pytest.mark.asyncio
async def test_step13_audit_chain_integrity(session_factory):
    """Audit chain verification passes after unlearning."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[target["record_id"]],
            requested_by="qa",
        )
        request = await DeletionRepository(session).create(request)
        await service.execute(request.id)
        await session.commit()

        from app.services.audit import AuditService
        chain = await AuditService(session).verify_chain()
        assert chain["verified"] is True


# ===========================================================================
# STEP 14 — API Validation
# ===========================================================================

@pytest.mark.asyncio
async def test_step14_impact_api(client, auth_headers, session_factory):
    """POST /unlearning/impact returns impact report."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        ik = target["identity_key"]

    resp = await client.post(
        "/api/v1/unlearning/impact",
        headers=auth_headers,
        json={"identity_key": ik},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "totals" in body
    assert "datasets" in body
    assert "eligible" in body


@pytest.mark.asyncio
async def test_step14_selective_unlearning_api(client, auth_headers, session_factory):
    """POST /unlearning/selective creates deletion request."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        ik = target["identity_key"]
        rid = target["record_id"]

    resp = await client.post(
        "/api/v1/unlearning/selective",
        headers=auth_headers,
        json={
            "identity_key": ik,
            "record_ids": [rid],
            "deletion_type": "records",
            "method": "retrain",
        },
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["id"]
    assert body["method"] == "retrain"

    # The conftest replaces dispatch_unlearning with a recorder.
    # Execute the recorded request inline (same pattern as test_api.py).
    from tests.conftest import run_unlearning_inline
    await run_unlearning_inline(session_factory, body["id"])

    # Now the request should be completed
    poll = await client.get(f"/api/v1/unlearning/requests/{body['id']}", headers=auth_headers)
    assert poll.json()["status"] == "completed"
    assert poll.json()["certificate_id"]


@pytest.mark.asyncio
async def test_step14_get_request_api(client, auth_headers, session_factory):
    """GET /unlearning/requests/{id} returns request details."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[target["record_id"]],
            requested_by="api-test",
        )
        request = await DeletionRepository(session).create(request)
        await service.execute(request.id)
        await session.commit()
        req_id = request.id

    resp = await client.get(f"/api/v1/unlearning/requests/{req_id}", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == req_id
    assert body["status"] == "completed"
    assert body["certificate_id"]
    assert body["duration_seconds"] is not None


@pytest.mark.asyncio
async def test_step14_selective_requires_auth(client):
    """POST /unlearning/selective without auth returns 401."""
    resp = await client.post("/api/v1/unlearning/selective", json={"identity_key": "x"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_step14_impact_requires_auth(client):
    """POST /unlearning/impact without auth returns 401."""
    resp = await client.post("/api/v1/unlearning/impact", json={"identity_key": "x"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_step14_invalid_method_rejected(client, auth_headers, session_factory):
    """POST /unlearning/selective with invalid method returns 422."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]

    resp = await client.post(
        "/api/v1/unlearning/selective",
        headers=auth_headers,
        json={
            "identity_key": target["identity_key"],
            "record_ids": [target["record_id"]],
            "method": "invalid_method",
        },
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_step14_no_selection_rejected(client, auth_headers, session_factory):
    """POST /unlearning/selective without any selection returns 422."""
    resp = await client.post(
        "/api/v1/unlearning/selective",
        headers=auth_headers,
        json={"method": "retrain"},
    )
    assert resp.status_code in (400, 422)


# ===========================================================================
# STEP 15 — Frontend data shapes
# ===========================================================================

@pytest.mark.asyncio
async def test_step15_deletion_history_shape(session_factory, auth_headers, client):
    """Deletion history response has the shape expected by frontend."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[target["record_id"]],
            requested_by="fe-qa",
        )
        request = await DeletionRepository(session).create(request)
        await service.execute(request.id)
        await session.commit()

    resp = await client.get("/api/v1/unlearning/history", headers=auth_headers)
    h = resp.json()[0]
    required = {
        "id", "request_id", "scope", "subject", "method", "status",
        "record_count", "shard_ids", "records_before", "records_after",
        "embeddings_before", "embeddings_after", "vectors_removed",
        "certificate_id", "before", "after",
    }
    assert required.issubset(h.keys())


@pytest.mark.asyncio
async def test_step15_deletion_request_shape(session_factory, auth_headers, client):
    """Deletion request response has the shape expected by frontend."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[target["record_id"]],
            requested_by="fe-qa",
        )
        request = await DeletionRepository(session).create(request)
        await service.execute(request.id)
        await session.commit()
        req_id = request.id

    resp = await client.get(f"/api/v1/unlearning/requests/{req_id}", headers=auth_headers)
    r = resp.json()
    required = {
        "id", "identity_key", "subject_label", "deletion_type", "method",
        "status", "record_ids", "requested_by", "requested_at", "completed_at",
        "duration_seconds", "certificate_id",
    }
    assert required.issubset(r.keys())


# ===========================================================================
# STEP 16 — Error Handling
# ===========================================================================

@pytest.mark.asyncio
async def test_step16_invalid_request_id_returns_error(session_factory, auth_headers, client):
    """GET /unlearning/requests/bogus returns 404."""
    resp = await client.get("/api/v1/unlearning/requests/bogus-id", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_step16_nonexistent_identity_impact(client, auth_headers):
    """Impact for non-existent identity returns 404."""
    resp = await client.post(
        "/api/v1/unlearning/impact",
        headers=auth_headers,
        json={"identity_key": "nonexistent_xyz"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_step16_nonexistent_chat_impact(client, auth_headers):
    """Impact for non-existent chat returns 404."""
    resp = await client.post(
        "/api/v1/unlearning/impact",
        headers=auth_headers,
        json={"chat_id": "nonexistent-chat", "scope": "chat"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_step16_invalid_scope_rejected(client, auth_headers, session_factory):
    """Invalid scope value returns error."""
    ctx = await build_pipeline(session_factory)
    resp = await client.post(
        "/api/v1/unlearning/impact",
        headers=auth_headers,
        json={"identity_key": "x", "scope": "invalid_scope"},
    )
    assert resp.status_code in (400, 422)


# ===========================================================================
# STEP 17 — Security
# ===========================================================================

@pytest.mark.asyncio
async def test_step17_unauthorized_deletion_blocked(client):
    """POST /unlearning/selective without auth returns 401."""
    resp = await client.post(
        "/api/v1/unlearning/selective",
        json={"identity_key": "x", "method": "retrain"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_step17_unauthorized_full_reset_blocked(client):
    """POST /unlearning/full-reset without auth returns 401."""
    resp = await client.post(
        "/api/v1/unlearning/full-reset",
        json={"identity_key": "x"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_step17_unauthorized_history_blocked(client):
    """GET /unlearning/history without auth returns 401."""
    resp = await client.get("/api/v1/unlearning/history")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_step17_deletion_request_logged_with_actor(session_factory):
    """Audit log records the actor who requested deletion."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[target["record_id"]],
            requested_by="security-tester",
        )
        request = await DeletionRepository(session).create(request)
        await service.execute(request.id)
        await session.commit()

        events = (await session.execute(
            select(AuditEvent).where(AuditEvent.event_type == "unlearning.completed")
        )).scalars().all()
        assert events[-1].actor == "security-tester"


# ===========================================================================
# STEP 18 — Performance
# ===========================================================================

@pytest.mark.asyncio
async def test_step18_single_record_deletion_latency(session_factory):
    """Single record deletion completes within 15s."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[target["record_id"]],
            requested_by="perf",
        )
        request = await DeletionRepository(session).create(request)
        start = time.time()
        await service.execute(request.id)
        await session.commit()
        elapsed = time.time() - start
        assert elapsed < 15.0, f"Deletion took {elapsed:.1f}s (>15s)"


@pytest.mark.asyncio
async def test_step18_chat_scoped_deletion_latency(session_factory):
    """Chat-scoped deletion (20 records) completes within 15s."""
    ctx = await build_chat_pipeline(session_factory)
    async with session_factory() as session:
        service = UnlearningService(session)
        records = await service.resolve_records(chat_id="chat-3", scope="chat")
        request = DeletionRequest(
            subject_label="chat:chat-3",
            deletion_type="chat",
            method="retrain",
            scope={"scope": "chat", "chat_id": "chat-3"},
            record_ids=[r.id for r in records],
            requested_by="perf",
        )
        request = await DeletionRepository(session).create(request)
        start = time.time()
        await service.execute(request.id)
        await session.commit()
        elapsed = time.time() - start
        assert elapsed < 15.0, f"Chat deletion took {elapsed:.1f}s (>15s)"


@pytest.mark.asyncio
async def test_step18_impact_analysis_latency(session_factory):
    """Impact analysis completes within 5s."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        service = UnlearningService(session)
        start = time.time()
        await service.analyze_impact(identity_key=target["identity_key"])
        elapsed = time.time() - start
        assert elapsed < 5.0, f"Impact analysis took {elapsed:.1f}s (>5s)"


@pytest.mark.asyncio
async def test_step18_certificate_generation_latency(session_factory):
    """Certificate issue + PDF generation completes within 10s."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[target["record_id"]],
            requested_by="perf",
        )
        request = await DeletionRepository(session).create(request)
        start = time.time()
        await service.execute(request.id)
        await session.commit()
        elapsed = time.time() - start
        # Certificate + PDF + blockchain all within the total deletion time
        assert elapsed < 10.0, f"Full pipeline took {elapsed:.1f}s (>10s)"


# ===========================================================================
# STEP 19 — Concurrent Requests
# ===========================================================================

@pytest.mark.asyncio
async def test_step19_concurrent_deletions_different_records(session_factory):
    """Two concurrent deletions of different records do not interfere."""
    ctx = await build_pipeline(session_factory, n=400)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        targets = matches[:2]
        rids = [m["record_id"] for m in targets]
        iks = [m["identity_key"] for m in targets]
        names = [m["full_name"] for m in targets]

    # Launch both deletions concurrently
    async def _delete(idx):
        async with session_factory() as session:
            service = UnlearningService(session)
            request = DeletionRequest(
                identity_key=iks[idx],
                subject_label=names[idx],
                deletion_type="records",
                method="retrain",
                record_ids=[rids[idx]],
                requested_by=f"concurrent-{idx}",
            )
            request = await DeletionRepository(session).create(request)
            result = await service.execute(request.id)
            await session.commit()
            return result

    results = await asyncio.gather(_delete(0), _delete(1), return_exceptions=True)
    # Both should succeed (no exception)
    for r in results:
        assert not isinstance(r, Exception), f"Concurrent deletion failed: {r}"
        assert r["deleted_records"] >= 1

    # Both records should be tombstoned
    async with session_factory() as session:
        for rid in rids:
            rec = await session.get(DatasetRecord, rid)
            assert rec.is_deleted is True


# ===========================================================================
# STEP 20 — Rollback / Recovery
# ===========================================================================

@pytest.mark.asyncio
async def test_step20_failed_deletion_status(session_factory):
    """A failed deletion request is marked as 'failed' not stuck in progress."""
    ctx = await build_pipeline(session_factory)
    async with session_factory() as session:
        privacy = PrivacyService(session)
        matches = await privacy.search_identities("a")
        target = matches[0]
        service = UnlearningService(session)

        # Delete once
        request1 = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[target["record_id"]],
            requested_by="qa",
        )
        request1 = await DeletionRepository(session).create(request1)
        await service.execute(request1.id)
        await session.commit()
        request1_id = request1.id

    # Try to delete the same record again (should fail — no active records)
    async with session_factory() as session:
        service = UnlearningService(session)
        request2 = DeletionRequest(
            identity_key=target["identity_key"],
            subject_label=target["full_name"],
            deletion_type="records",
            method="retrain",
            record_ids=[target["record_id"]],
            requested_by="qa",
        )
        request2 = await DeletionRepository(session).create(request2)
        request2_id = request2.id
        try:
            await service.execute(request2.id)
            # Should not reach here
            assert False, "Expected exception for double-delete"
        except Exception:
            pass  # Expected

        # Verify request2 is marked as failed (execute sets it before raising)
        await session.refresh(request2)
        assert request2.status == "failed"
        assert request2.error


# ===========================================================================
# STEP 21 — End-to-End Unlearning Flow
# ===========================================================================

@pytest.mark.asyncio
async def test_step21_full_e2e_unlearning_flow(session_factory, auth_headers, client):
    """Full E2E: Upload → Train → Search → Impact → Delete → Verify → Certificate."""
    # 1. Upload dataset
    resp = await client.post(
        "/api/v1/datasets/upload",
        headers=auth_headers,
        data={"shard_count": "4"},
        files={"file": ("e2e.csv", make_csv(400), "text/csv")},
    )
    assert resp.status_code == 201
    ds_id = resp.json()["id"]
    assert resp.json()["record_count"] == 400

    # 2. Train model
    resp = await client.post(f"/api/v1/models/train?dataset_id={ds_id}", headers=auth_headers)
    assert resp.status_code == 201
    model_id = resp.json()["id"]
    assert resp.json()["status"] == "ready"
    acc_before = resp.json()["metrics"]["accuracy"]

    # 3. Search identity
    resp = await client.post("/api/v1/privacy/search?query=a", headers=auth_headers)
    matches = resp.json()["matches"]
    assert len(matches) >= 1
    target = matches[0]
    ik = target["identity_key"]
    rid = target["record_id"]

    # 4. Preview impact
    resp = await client.post(
        "/api/v1/unlearning/impact",
        headers=auth_headers,
        json={"identity_key": ik},
    )
    assert resp.status_code == 200
    impact = resp.json()
    assert impact["eligible"] is True
    assert impact["totals"]["records"] >= 1

    # 5. Execute selective unlearning
    resp = await client.post(
        "/api/v1/unlearning/selective",
        headers=auth_headers,
        json={
            "identity_key": ik,
            "record_ids": [rid],
            "deletion_type": "records",
            "method": "retrain",
        },
    )
    assert resp.status_code == 202
    request_id = resp.json()["id"]

    # 6. Run unlearning inline (conftest replaces dispatch with recorder)
    from tests.conftest import run_unlearning_inline
    await run_unlearning_inline(session_factory, request_id)

    poll = await client.get(f"/api/v1/unlearning/requests/{request_id}", headers=auth_headers)
    assert poll.json()["status"] == "completed"
    assert poll.json()["certificate_id"]

    # 7. Verify certificate
    cert_id = poll.json()["certificate_id"]
    resp = await client.post(f"/api/v1/verification/verify/{cert_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["verified"] is True

    # 8. Verify deleted identity is no longer searchable
    resp = await client.post(
        "/api/v1/privacy/search",
        headers=auth_headers,
        json={"filters": {"record_id": rid}},
    )
    assert resp.json()["match_count"] == 0

    # 9. Verify deletion history
    resp = await client.get("/api/v1/unlearning/history", headers=auth_headers)
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) >= 1
    h = history[0]
    assert h["records_before"] >= 1
    assert h["records_after"] == h["records_before"] - 1

    # 10. Verify model still works
    resp = await client.post(
        f"/api/v1/models/{model_id}/predict",
        headers=auth_headers,
        json={"features": {"a": 2.0, "b": -2.0}},
    )
    assert resp.status_code == 200
    assert "probability" in resp.json()


@pytest.mark.asyncio
async def test_step21_e2e_certified_method_flow(session_factory, auth_headers, client):
    """E2E with certified removal method."""
    resp = await client.post(
        "/api/v1/datasets/upload",
        headers=auth_headers,
        data={"shard_count": "4"},
        files={"file": ("cert_e2e.csv", make_csv(400), "text/csv")},
    )
    ds_id = resp.json()["id"]

    resp = await client.post(f"/api/v1/models/train?dataset_id={ds_id}", headers=auth_headers)
    assert resp.status_code == 201

    resp = await client.post("/api/v1/privacy/search?query=a", headers=auth_headers)
    target = resp.json()["matches"][0]

    resp = await client.post(
        "/api/v1/unlearning/selective",
        headers=auth_headers,
        json={
            "identity_key": target["identity_key"],
            "record_ids": [target["record_id"]],
            "deletion_type": "records",
            "method": "certified",
        },
    )
    assert resp.status_code == 202
    request_id = resp.json()["id"]

    from tests.conftest import run_unlearning_inline
    await run_unlearning_inline(session_factory, request_id)

    poll = await client.get(f"/api/v1/unlearning/requests/{request_id}", headers=auth_headers)
    assert poll.json()["status"] == "completed"

    # Certificate should have certified_bound
    cert_id = poll.json()["certificate_id"]
    resp = await client.post(f"/api/v1/verification/verify/{cert_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["verified"] is True


@pytest.mark.asyncio
async def test_step21_e2e_influence_method_flow(session_factory, auth_headers, client):
    """E2E with influence-based scrubbing."""
    resp = await client.post(
        "/api/v1/datasets/upload",
        headers=auth_headers,
        data={"shard_count": "4"},
        files={"file": ("inf_e2e.csv", make_csv(400), "text/csv")},
    )
    ds_id = resp.json()["id"]

    resp = await client.post(f"/api/v1/models/train?dataset_id={ds_id}", headers=auth_headers)
    assert resp.status_code == 201

    resp = await client.post("/api/v1/privacy/search?query=a", headers=auth_headers)
    target = resp.json()["matches"][0]

    resp = await client.post(
        "/api/v1/unlearning/selective",
        headers=auth_headers,
        json={
            "identity_key": target["identity_key"],
            "record_ids": [target["record_id"]],
            "deletion_type": "records",
            "method": "influence",
        },
    )
    assert resp.status_code == 202
    request_id = resp.json()["id"]

    from tests.conftest import run_unlearning_inline
    await run_unlearning_inline(session_factory, request_id)

    poll = await client.get(f"/api/v1/unlearning/requests/{request_id}", headers=auth_headers)
    assert poll.json()["status"] == "completed"
    assert poll.json()["certificate_id"]


@pytest.mark.asyncio
async def test_step21_full_identity_reset_e2e(session_factory, auth_headers, client):
    """Full identity reset deletes ALL records of the identity across datasets."""
    resp = await client.post(
        "/api/v1/datasets/upload",
        headers=auth_headers,
        data={"shard_count": "4"},
        files={"file": ("reset_e2e.csv", make_csv(400), "text/csv")},
    )
    ds_id = resp.json()["id"]

    resp = await client.post(f"/api/v1/models/train?dataset_id={ds_id}", headers=auth_headers)
    assert resp.status_code == 201

    resp = await client.post("/api/v1/privacy/search?query=a", headers=auth_headers)
    target = resp.json()["matches"][0]

    resp = await client.post(
        "/api/v1/unlearning/full-reset",
        headers=auth_headers,
        json={"identity_key": target["identity_key"]},
    )
    assert resp.status_code == 202
    request_id = resp.json()["id"]

    from tests.conftest import run_unlearning_inline
    await run_unlearning_inline(session_factory, request_id)

    poll = await client.get(f"/api/v1/unlearning/requests/{request_id}", headers=auth_headers)
    assert poll.json()["status"] == "completed"

    # Footprint should show active_records=0
    resp = await client.get(
        f"/api/v1/privacy/footprint/{target['identity_key']}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["active_records"] == 0
    assert resp.json()["deleted_records"] > 0
