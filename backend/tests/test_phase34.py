"""Phase 3 & Phase 4 integration tests.

Covers: full-dataset privacy scan → reports, multi-field identity search,
record viewer, impact analysis, chat/dataset scoped unlearning, before/after
snapshots and persisted deletion history, plus PDF ingestion.
"""
from __future__ import annotations

import numpy as np
import pytest
from fpdf import FPDF

from app.db.models import DeletionRequest, MLModel
from app.repositories.deletion_repo import DeletionRepository
from app.repositories.model_repo import ModelRepository
from app.repositories.privacy_repo import DeletionHistoryRepository
from app.services.ingestion import IngestionService
from app.services.privacy import PrivacyService
from app.services.sisa import SISAEngine
from app.services.unlearning import UnlearningService


def make_chat_csv(n: int = 200) -> bytes:
    """Two-class rows with a chat_id column (for conversation-scoped unlearning)."""
    rng = np.random.default_rng(1)
    rows = []
    for i in range(n):
        cls = i % 2
        a = rng.normal(cls * 2.0, 0.8)
        b = rng.normal(cls * -2.0, 0.8)
        chat = f"chat-{i % 10}"
        label = "high" if cls == 1 else "low"
        rows.append(f"{a:.4f},{b:.4f},{chat},{label}")
    return ("a,b,chat_id,income\n" + "\n".join(rows)).encode()


def make_pii_csv(n: int = 100) -> bytes:
    """Rows with real identity columns incl. Aadhaar/PAN/phone for detection."""
    rng = np.random.default_rng(2)
    rows = []
    for i in range(n):
        rows.append(
            f"user{i}@mail.com,+91987654{i:04d},234567890{i:03d},ABCDE{i % 10}0{i % 9}F,{rng.normal(0,1):.3f},{i % 2}"
        )
    return ("email,phone,aadhaar,pan,score,label\n" + "\n".join(rows)).encode()


def make_pdf() -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 8, "Patient record: diagnosis diabetes, email patient@clinic.com, aadhaar 2345 6789 0123")
    pdf.add_page()
    pdf.cell(0, 8, "Second page: blood group O+, phone +91 9876543210")
    return bytes(pdf.output())


async def build_dataset(session_factory, content: bytes, name: str, label_column: str | None = None) -> str:
    async with session_factory() as session:
        dataset = await IngestionService(session).ingest_csv_bytes(
            content, name=name, label_column=label_column, shard_count=4
        )
        await session.commit()
        return dataset.id


@pytest.mark.asyncio
async def test_pdf_ingestion(session_factory):
    async with session_factory() as session:
        dataset = await IngestionService(session).ingest_file("notes.pdf", make_pdf(), shard_count=2)
        assert dataset.source_type == "pdf"
        assert dataset.record_count >= 2
        assert dataset.meta.get("kind") == "documents"
        records = await session.execute(__import__("sqlalchemy").select(__import__("app.db.models", fromlist=["DatasetRecord"]).DatasetRecord))
        first = records.scalars().first()
        assert first.original_text and "patient" in first.original_text.lower()


@pytest.mark.asyncio
async def test_full_scan_and_structured_search(session_factory):
    ds_id = await build_dataset(session_factory, make_pii_csv(), "pii")
    async with session_factory() as session:
        service = PrivacyService(session)
        report = await service.scan_all(dataset_id=ds_id, created_by="tester")
        await session.commit()

        assert report.scanned_records == 100
        assert report.critical_count > 0  # Aadhaar/PAN fields
        assert "government_id" in report.categories
        assert report.findings_count >= 100

        # Structured search by aadhaar.
        matches = await service.search_identities(filters={"aadhaar": "234567890000"})
        assert any(m["aadhaar"] == "234567890000" for m in matches)
        assert matches[0]["confidence"] >= 0.98

        # Search by phone substring (+91987654XXXX in the fixture).
        phone_matches = await service.search_identities("987654")
        assert phone_matches, "phone substring should match"

        # Record viewer round-trip.
        detail = await service.get_record_detail(matches[0]["record_id"])
        assert detail["file_name"] is None or isinstance(detail["file_name"], str)
        assert detail["content_hash"]
        assert detail["pii_findings"]["counts_by_severity"]["critical"] >= 1
        await session.commit()

        # Report retrieval via repository.
        got = await service.get_report(report.id)
        assert got.id == report.id
        assert len(got.findings) >= 1


@pytest.mark.asyncio
async def test_impact_analysis_and_scoped_deletion(session_factory):
    ds_id = await build_dataset(session_factory, make_chat_csv(), "chats")
    async with session_factory() as session:
        model = MLModel(name="chats-v1", model_type="linear", dataset_id=ds_id, shard_count=4)
        model = await ModelRepository(session).add(model)
        await SISAEngine(session).train_model(model, await session.get(__import__("app.db.models", fromlist=["Dataset"]).Dataset, ds_id))
        await session.commit()

    async with session_factory() as session:
        service = UnlearningService(session)

        # Impact for one chat (200 rows / 10 chats = 20 records spread across shards).
        impact = await service.analyze_impact(chat_id="chat-3", scope="chat")
        assert impact["totals"]["records"] == 20
        assert impact["totals"]["affected_shards"] >= 1
        assert impact["eligible"] is True
        assert impact["datasets"][ds_id]["dependencies"]["model_id"] == model.id
        assert impact["totals"]["embeddings"] == 20  # numeric features are embedded

        # Execute chat-scoped deletion (SISA retrain).
        request = DeletionRequest(
            identity_key=None,
            subject_label="chat:chat-3",
            deletion_type="chat",
            method="retrain",
            scope={"scope": "chat", "chat_id": "chat-3"},
            record_ids=[],
            requested_by="tester",
        )
        # resolve records directly so the request carries correct ids
        records = await service.resolve_records(chat_id="chat-3", scope="chat")
        request.record_ids = [r.id for r in records]
        request = await DeletionRepository(session).create(request)
        result = await service.execute(request.id)
        await session.commit()

        assert result["deleted_records"] == 20
        dataset_result = result[ds_id]
        assert dataset_result["after"]["records"] == 180
        assert dataset_result["after"]["embeddings"] == 180
        assert dataset_result["vectors_removed"] == 20
        assert dataset_result["dataset_version"] == 2
        assert dataset_result["before"]["records"] == 200

        # Deletion history row persisted (Phase 4 STEP 7).
        history = await DeletionHistoryRepository(session).get_by_request(request.id)
        assert history is not None
        assert history.records_before == 200 and history.records_after == 180
        assert history.scope == "chat"
        assert history.certificate_id


@pytest.mark.asyncio
async def test_dataset_scope_deletion(session_factory):
    ds_id = await build_dataset(session_factory, make_chat_csv(), "chats2")
    async with session_factory() as session:
        model = MLModel(name="chats2-v1", model_type="linear", dataset_id=ds_id, shard_count=4)
        model = await ModelRepository(session).add(model)
        dataset = await session.get(__import__("app.db.models", fromlist=["Dataset"]).Dataset, ds_id)
        await SISAEngine(session).train_model(model, dataset)
        await session.commit()

    async with session_factory() as session:
        service = UnlearningService(session)
        request = DeletionRequest(
            subject_label=f"dataset:{ds_id}",
            deletion_type="dataset",
            method="retrain",
            scope={"scope": "dataset", "dataset_id": ds_id},
            record_ids=[],
            requested_by="tester",
        )
        records = await service.resolve_records(dataset_id=ds_id, scope="dataset")
        request.record_ids = [r.id for r in records]
        request = await DeletionRepository(session).create(request)
        result = await service.execute(request.id)
        await session.commit()

        assert result["deleted_records"] == 200
        dataset_result = result[ds_id]
        assert dataset_result["remaining_records"] == 0
        assert dataset_result["dataset_version"] == 2


@pytest.mark.asyncio
async def test_search_history_recorded(session_factory):
    await build_dataset(session_factory, make_pii_csv(), "pii2")
    async with session_factory() as session:
        service = PrivacyService(session)
        await service.search_identities("user1@", user_id="u-123")
        await session.commit()
        entries = await service.list_history("u-123")
        assert entries and entries[0].query == "user1@"
