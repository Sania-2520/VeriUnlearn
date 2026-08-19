"""Phase 5 — Verifiable Machine Unlearning tests.

Covers the Merkle engine (incremental/batch/partial), the cryptographic proof
generator, the full deletion-verification engine, and the verification API.
"""
from __future__ import annotations

import numpy as np
import pytest

from app.db.models import DeletionRequest, MLModel, VerificationReport
from app.repositories.deletion_repo import DeletionRepository
from app.repositories.model_repo import ModelRepository
from app.services.crypto import MerkleTree, leaf_hash
from app.services.ingestion import IngestionService
from app.services.merkle_engine import MerkleEngine
from app.services.proofs import ProofService
from app.services.sisa import SISAEngine
from app.services.unlearning import UnlearningService
from app.services.verification_engine import VerificationService


def make_csv(n: int = 200) -> bytes:
    rng = np.random.default_rng(7)
    rows = []
    for i in range(n):
        cls = i % 2
        rows.append(f"{rng.normal(cls * 2.0, 0.8):.4f},{rng.normal(cls * -2.0, 0.8):.4f},{'high' if cls else 'low'}")
    return ("a,b,income\n" + "\n".join(rows)).encode()


# ------------------------------------------------------------- Merkle engine


def test_merkle_incremental_insert_delete():
    t0 = MerkleTree(["a", "b", "c"])
    root_before = t0.root

    t1 = MerkleEngine.insert(t0, "d")
    assert t1.root != root_before
    assert "d" in t1.leaves

    t2 = MerkleEngine.delete(t1, "d")
    assert t2.root == root_before
    assert "d" not in t2.leaves


def test_merkle_batch_delete_and_comparison():
    leaves = [leaf_hash(f"r{i}", f"h{i}", deleted=False) for i in range(8)]
    tree = MerkleTree(leaves)
    removed = leaves[:3]
    post = MerkleEngine.delete_many(tree, removed)
    comparison = MerkleEngine.compare(tree, post)
    assert comparison["transition"] == "reduced"
    assert comparison["root_changed"] is True
    assert set(comparison["removed_leaves"]) == set(removed)


def test_merkle_partial_verification():
    leaves = [leaf_hash(f"r{i}", f"h{i}", deleted=False) for i in range(10)]
    tree = MerkleTree(leaves)
    subset = leaves[:4]
    proof = MerkleEngine.proof_for_leaves(tree, subset)
    assert proof["root"] == tree.root
    # Rebuild root from subset + excluded hashes must match.
    assert MerkleEngine.verify_subset(
        proof["root"], proof["leaves"], proof["excluded_hashes"]
    )
    # Tampered subset must fail.
    assert not MerkleEngine.verify_subset(
        proof["root"], leaves[:2], proof["excluded_hashes"]
    )


def test_merkle_membership_and_snapshot():
    leaves = [leaf_hash(f"r{i}", f"h{i}", deleted=False) for i in range(6)]
    tree = MerkleTree(leaves)
    ok, proof = MerkleEngine.verify_membership(tree, leaves[2])
    assert ok and len(proof) >= 1
    snap = MerkleEngine.snapshot(tree)
    assert snap["root"] == tree.root
    assert snap["leaf_count"] == 6
    assert snap["levels_depth"] >= 3


# --------------------------------------------------------------- Proofs


def test_proof_issue_and_verify():
    proof = ProofService.issue(
        subject_id="cert-1",
        subject_type="certificate",
        pre_merkle_root="a" * 64,
        post_merkle_root="b" * 64,
        leaf_hashes=["l1", "l2"],
        claim="deletion_occurred",
    )
    assert proof["proof_id"] and proof["nonce"] and proof["signature"]
    verdict = ProofService.verify(proof)
    assert verdict["verified"] is True
    assert verdict["hash_integrity"] and verdict["signature_valid"]
    assert verdict["nonce_present"] and verdict["timestamp_valid"]


def test_proof_tamper_detection():
    proof = ProofService.issue(
        subject_id="cert-2",
        subject_type="certificate",
        pre_merkle_root="a" * 64,
        post_merkle_root="b" * 64,
        leaf_hashes=["l1"],
        claim="deletion_occurred",
    )
    tampered = dict(proof)
    tampered["post_merkle_root"] = "c" * 64
    assert ProofService.verify(tampered)["verified"] is False

    forged = dict(proof)
    forged["signature"] = "Zm9yZ2Vk"  # base64("forged")
    assert ProofService.verify(forged)["signature_valid"] is False


# ------------------------------------------------------- Verification engine


async def _build_deleted_request(session_factory) -> tuple[str, str, str]:
    """Dataset + model + a completed identity deletion → (dataset_id, model_id, request_id)."""
    async with session_factory() as session:
        dataset = await IngestionService(session).ingest_csv_bytes(
            make_csv(), name="v5-data", label_column="income", shard_count=4
        )
        await session.commit()
        ds_id = dataset.id

    async with session_factory() as session:
        model = MLModel(name="v5-model", model_type="linear", dataset_id=ds_id, shard_count=4)
        model = await ModelRepository(session).add(model)
        from app.db.models import Dataset

        await SISAEngine(session).train_model(model, await session.get(Dataset, ds_id))
        await session.commit()
        model_id = model.id

    async with session_factory() as session:
        service = UnlearningService(session)
        from sqlalchemy import select

        from app.db.models import DatasetRecord

        # Delete one identity across its records.
        result = await session.execute(
            select(DatasetRecord)
            .where(DatasetRecord.dataset_id == ds_id)
            .limit(10)
        )
        chosen = list(result.scalars().all())
        request = DeletionRequest(
            identity_key=chosen[0].identity_key,
            subject_label=chosen[0].identity_key or "identity",
            deletion_type="records",
            method="retrain",
            scope={"scope": "records"},
            record_ids=[r.id for r in chosen],
            requested_by="tester",
        )
        request = await DeletionRepository(session).create(request)
        await service.execute(request.id)
        await session.commit()
        return ds_id, model_id, request.id


@pytest.mark.asyncio
async def test_verification_engine_full_run(session_factory):
    ds_id, model_id, request_id = await _build_deleted_request(session_factory)
    async with session_factory() as session:
        request = await session.get(DeletionRequest, request_id)
        service = VerificationService(session)
        report = await service.run(deletion_request_id=request.id, created_by="tester")
        await session.commit()
        assert isinstance(report, VerificationReport)
        assert report.verdict == "valid"
        assert report.checks_passed == report.checks_total == 8
        assert report.certificate_id == request.certificate_id
        assert report.duration_seconds is not None
        # Merkle snapshot present for visualisation.
        assert report.merkle_snapshot.get("root")


@pytest.mark.asyncio
async def test_verification_report_persistence(session_factory):
    ds_id, model_id, request_id = await _build_deleted_request(session_factory)
    async with session_factory() as session:
        request = await session.get(DeletionRequest, request_id)
        await VerificationService(session).run(deletion_request_id=request.id, created_by="tester")
        await session.commit()

    async with session_factory() as session:
        reports = await VerificationService(session).list_reports(limit=10)
        assert len(reports) >= 1
        got = await VerificationService(session).get_report(reports[0].id)
        assert got.id == reports[0].id
        assert got.verdict == "valid"


@pytest.mark.asyncio
async def test_verification_api(session_factory, client, auth_headers):
    ds_id, model_id, request_id = await _build_deleted_request(session_factory)
    async with session_factory() as session:
        request = await session.get(DeletionRequest, request_id)
        cert_id = request.certificate_id

    # run
    r = await client.post(
        "/api/v1/verification/run",
        json={"deletion_request_id": request_id},
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    report_id = body["report_id"]
    assert body["verdict"] == "valid"

    # get report
    r = await client.get(f"/api/v1/verification/{report_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["verdict"] == "valid"
    assert len(r.json()["checks"]) == 8

    # certificate verify (GET)
    r = await client.get(f"/api/v1/verification/certificate/{cert_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["verified"] is True

    # legacy POST verify
    r = await client.post(f"/api/v1/verification/verify/{cert_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["verified"] is True

    # verify-proof: build a real membership proof and check it
    from sqlalchemy import select

    from app.db.models import DatasetRecord

    async with session_factory() as session:
        records = (
            await session.execute(
                select(DatasetRecord).where(DatasetRecord.dataset_id == ds_id).limit(20)
            )
        ).scalars().all()
        leaves = [leaf_hash(r.id, r.content_hash, deleted=r.is_deleted) for r in records]
    tree = MerkleTree(leaves)
    proof = tree.proof(leaves[0])
    # sanity: the proof must chain in-process
    assert MerkleTree.verify(tree.root, leaves[0], proof) is True, "in-process proof broken"
    r = await client.post(
        "/api/v1/verification/verify-proof",
        json={"root": tree.root, "leaf": leaves[0], "proof": proof},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["verified"] is True

    # bad proof must fail
    r = await client.post(
        "/api/v1/verification/verify-proof",
        json={"root": tree.root, "leaf": "ffff", "proof": proof},
        headers=auth_headers,
    )
    assert r.json()["verified"] is False

    # history + audit + public key
    r = await client.get("/api/v1/verification/history", headers=auth_headers)
    assert r.status_code == 200 and len(r.json()["reports"]) >= 1
    r = await client.get("/api/v1/verification/audit", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["chain"]["verified"] is True
    r = await client.get("/api/v1/verification/public-key", headers=auth_headers)
    assert "BEGIN PUBLIC KEY" in r.json()["public_key_pem"]

    # downloads
    r = await client.get(f"/api/v1/verification/download/json/{report_id}", headers=auth_headers)
    assert r.status_code == 200 and r.json()["verdict"] == "valid"
    r = await client.get(f"/api/v1/verification/download/pdf/{report_id}", headers=auth_headers)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"


@pytest.mark.asyncio
async def test_proof_api(session_factory, client, auth_headers):
    ProofService.issue(
        subject_id="cert-x",
        subject_type="certificate",
        pre_merkle_root="a" * 64,
        post_merkle_root="b" * 64,
        leaf_hashes=["l1", "l2"],
        claim="deletion_occurred",
    )
    r = await client.post(
        "/api/v1/verification/proofs",
        json={
            "subject_id": "cert-x",
            "subject_type": "certificate",
            "claim": "deletion_occurred",
            "pre_merkle_root": "a" * 64,
            "post_merkle_root": "b" * 64,
            "leaf_hashes": ["l1", "l2"],
        },
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["proof_id"] and body["nonce"] and body["signature"]
    r = await client.get(f"/api/v1/verification/proofs/{body['proof_id']}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["proof_id"] == body["proof_id"]
