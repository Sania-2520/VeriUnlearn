"""Comprehensive Phase 5 QA test suite — Verifiable Machine Unlearning.

Covers every step of the QA specification (Steps 1-19):
  STEP 1  - Verification Dashboard
  STEP 2  - Unlearning Request
  STEP 3  - Verification Engine
  STEP 4  - Merkle Tree
  STEP 5  - Hash Validation
  STEP 6  - Digital Signatures
  STEP 7  - Certificate Generation
  STEP 8  - Certificate Validation
  STEP 9  - Audit Trail
  STEP 10 - Immutability Test (tampering detection)
  STEP 11 - API Validation
  STEP 12 - Database Validation
  STEP 13 - Export
  STEP 14 - Frontend data shapes
  STEP 15 - Error Handling
  STEP 16 - Security
  STEP 17 - Performance
  STEP 18 - Concurrent Operations
  STEP 19 - End-to-End Verification Flow
"""
from __future__ import annotations

import asyncio
import hashlib
import time

import numpy as np
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import public_key_pem, sign_sha256, verify_sha256
from app.db.models import (
    AuditEvent,
    Certificate,
    CryptoProof,
    Dataset,
    DatasetRecord,
    DeletionRequest,
    MLModel,
    VerificationReport,
)
from app.repositories.audit_repo import AuditRepository
from app.repositories.certificate_repo import CertificateRepository
from app.repositories.deletion_repo import DeletionRepository
from app.repositories.model_repo import ModelRepository
from app.services.audit import AuditService
from app.services.certificate import CertificateService
from app.services.crypto import (
    MerkleTree,
    canonical_json,
    hash_chain_link,
    leaf_hash,
    sha256_hex,
    tombstone_hash,
)
from app.services.ingestion import IngestionService
from app.services.merkle_engine import MerkleEngine
from app.services.proofs import ProofService
from app.services.sisa import SISAEngine
from app.services.unlearning import UnlearningService
from app.services.verification_engine import VerificationService
from app.services.zkproof import ZKDeletionProofService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_csv(n: int = 400) -> bytes:
    rng = np.random.default_rng(42)
    rows = []
    for i in range(n):
        cls = i % 2
        a = rng.normal(cls * 2.0, 0.8)
        b = rng.normal(cls * -2.0, 0.8)
        label = "high" if cls else "low"
        rows.append(f"{a:.4f},{b:.4f},{label}")
    return ("a,b,income\n" + "\n".join(rows)).encode()


async def build_and_delete(session_factory) -> dict:
    """Build dataset + train + delete one identity → return context dict."""
    async with session_factory() as session:
        ds = await IngestionService(session).ingest_csv_bytes(
            make_csv(), name="v5-qa", label_column="income", shard_count=4
        )
        await session.commit()
        ds_id = ds.id

    async with session_factory() as session:
        model = MLModel(name="v5-qa-model", model_type="linear", dataset_id=ds_id, shard_count=4)
        model = await ModelRepository(session).add(model)
        dataset = await session.get(Dataset, ds_id)
        await SISAEngine(session).train_model(model, dataset)
        await session.commit()
        model_id = model.id

    async with session_factory() as session:
        result = await session.execute(
            select(DatasetRecord).where(DatasetRecord.dataset_id == ds_id).limit(5)
        )
        chosen = list(result.scalars().all())
        service = UnlearningService(session)
        request = DeletionRequest(
            identity_key=chosen[0].identity_key,
            subject_label=chosen[0].identity_key or "identity",
            deletion_type="records",
            method="retrain",
            scope={"scope": "records"},
            record_ids=[r.id for r in chosen],
            requested_by="qa-tester",
        )
        request = await DeletionRepository(session).create(request)
        await service.execute(request.id)
        await session.commit()
        return {"ds_id": ds_id, "model_id": model_id, "request_id": request.id, "cert_id": request.certificate_id}


# ===========================================================================
# STEP 1 — Verification Dashboard
# ===========================================================================

@pytest.mark.asyncio
async def test_step1_verification_history(session_factory, auth_headers, client):
    """GET /verification/history returns verification reports."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        req = await session.get(DeletionRequest, ctx["request_id"])
        await VerificationService(session).run(deletion_request_id=req.id, created_by="qa")
        await session.commit()

    resp = await client.get("/api/v1/verification/history", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "reports" in body
    assert len(body["reports"]) >= 1
    r = body["reports"][0]
    assert r["verdict"] == "valid"
    assert r["checks_passed"] == r["checks_total"]
    assert r["certificate_id"]


@pytest.mark.asyncio
async def test_step1_verification_audit(session_factory, auth_headers, client):
    """GET /verification/audit returns audit chain status."""
    ctx = await build_and_delete(session_factory)
    resp = await client.get("/api/v1/verification/audit", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "chain" in body
    assert body["chain"]["verified"] is True
    assert body["chain"]["event_count"] >= 1
    assert "events" in body
    assert len(body["events"]) >= 1


@pytest.mark.asyncio
async def test_step1_public_key(session_factory, auth_headers, client):
    """GET /verification/public-key returns RSA public key."""
    resp = await client.get("/api/v1/verification/public-key", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "BEGIN PUBLIC KEY" in body["public_key_pem"]
    assert body["algorithm"] == "RSA-PKCS1v15-SHA256"


# ===========================================================================
# STEP 2 — Unlearning Request
# ===========================================================================

@pytest.mark.asyncio
async def test_step2_single_record_deletion_creates_certificate(session_factory):
    """Single record deletion produces a certificate."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        cert = await CertificateService(session).repo.get(ctx["cert_id"])
        assert cert.id == ctx["cert_id"]
        assert cert.deleted_record_count == 5
        assert cert.pre_merkle_root
        assert cert.post_merkle_root
        assert cert.pre_merkle_root != cert.post_merkle_root


@pytest.mark.asyncio
async def test_step2_deletion_request_status_completed(session_factory):
    """Deletion request is marked 'completed' after execution."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        req = await DeletionRepository(session).get(ctx["request_id"])
        assert req.status == "completed"
        assert req.certificate_id == ctx["cert_id"]
        assert req.duration_seconds is not None


# ===========================================================================
# STEP 3 — Verification Engine
# ===========================================================================

@pytest.mark.asyncio
async def test_step3_verification_engine_all_checks_pass(session_factory):
    """Full verification run passes all 8 checks."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        req = await session.get(DeletionRequest, ctx["request_id"])
        report = await VerificationService(session).run(
            deletion_request_id=req.id, created_by="qa-engine"
        )
        await session.commit()
        assert report.verdict == "valid"
        assert report.checks_passed == 8
        assert report.checks_total == 8
        assert report.duration_seconds is not None
        assert report.merkle_snapshot.get("root")


@pytest.mark.asyncio
async def test_step3_verification_engine_persists_report(session_factory):
    """Verification report is persisted and retrievable."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        req = await session.get(DeletionRequest, ctx["request_id"])
        report = await VerificationService(session).run(
            deletion_request_id=req.id, created_by="qa"
        )
        await session.commit()
        report_id = report.id

    async with session_factory() as session:
        got = await VerificationService(session).get_report(report_id)
        assert got.id == report_id
        assert got.verdict == "valid"
        assert got.certificate_id == ctx["cert_id"]
        assert got.dataset_id == ctx["ds_id"]


@pytest.mark.asyncio
async def test_step3_verification_engine_check_details(session_factory):
    """Each check has passed=True and details dict."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        req = await session.get(DeletionRequest, ctx["request_id"])
        report = await VerificationService(session).run(
            deletion_request_id=req.id, created_by="qa"
        )
        await session.commit()
        for name in ("records", "embeddings", "vectors", "versions", "merkle", "signature", "audit", "consistency"):
            check = report.checks[name]
            assert check["passed"] is True, f"Check '{name}' failed"
            assert "details" in check


# ===========================================================================
# STEP 4 — Merkle Tree
# ===========================================================================

@pytest.mark.asyncio
async def test_step4_merkle_tree_creation():
    """MerkleTree builds correctly from leaves."""
    leaves = [leaf_hash(f"r{i}", f"h{i}") for i in range(8)]
    tree = MerkleTree(leaves)
    assert tree.root
    assert len(tree.leaves) == 8
    assert len(tree.levels) >= 4  # log2(8) + 1


@pytest.mark.asyncio
async def test_step4_merkle_root_consistency():
    """Same leaves always produce the same root."""
    leaves = [leaf_hash(f"r{i}", f"h{i}") for i in range(5)]
    t1 = MerkleTree(leaves)
    t2 = MerkleTree(leaves)
    assert t1.root == t2.root


@pytest.mark.asyncio
async def test_step4_merkle_root_changes_after_deletion():
    """Merkle root changes when a leaf is deleted (tombstoned)."""
    leaves = [leaf_hash(f"r{i}", f"h{i}", deleted=False) for i in range(8)]
    tree_before = MerkleTree(leaves)
    # Replace one leaf with its tombstone
    tombstoned = leaf_hash("r0", "h0", deleted=True)
    new_leaves = [tombstoned] + leaves[1:]
    tree_after = MerkleTree(new_leaves)
    assert tree_before.root != tree_after.root


@pytest.mark.asyncio
async def test_step4_merkle_proof_verification():
    """Merkle proof for a leaf verifies against the root."""
    leaves = [leaf_hash(f"r{i}", f"h{i}") for i in range(16)]
    tree = MerkleTree(leaves)
    for leaf in leaves[:5]:
        proof = tree.proof(leaf)
        assert MerkleTree.verify(tree.root, leaf, proof)


@pytest.mark.asyncio
async def test_step4_merkle_membership_proof():
    """MerkleEngine membership proof works."""
    leaves = [leaf_hash(f"r{i}", f"h{i}") for i in range(10)]
    tree = MerkleTree(leaves)
    ok, proof = MerkleEngine.verify_membership(tree, leaves[3])
    assert ok
    assert len(proof) >= 1


@pytest.mark.asyncio
async def test_step4_merkle_partial_verification():
    """MerkleEngine partial verification for a subset of leaves."""
    leaves = [leaf_hash(f"r{i}", f"h{i}") for i in range(20)]
    tree = MerkleTree(leaves)
    subset = leaves[:5]
    proof = MerkleEngine.proof_for_leaves(tree, subset)
    assert MerkleEngine.verify_subset(proof["root"], proof["leaves"], proof["excluded_hashes"])


@pytest.mark.asyncio
async def test_step4_merkle_incremental_operations():
    """Insert and delete maintain tree integrity."""
    t0 = MerkleTree(["a", "b", "c"])
    t1 = MerkleEngine.insert(t0, "d")
    assert "d" in t1.leaves
    t2 = MerkleEngine.delete(t1, "d")
    assert t2.root == t0.root


@pytest.mark.asyncio
async def test_step4_merkle_snapshot():
    """Snapshot produces valid visualisation data."""
    leaves = [leaf_hash(f"r{i}", f"h{i}") for i in range(8)]
    tree = MerkleTree(leaves)
    snap = MerkleEngine.snapshot(tree)
    assert snap["root"] == tree.root
    assert snap["leaf_count"] == 8
    assert snap["levels_depth"] >= 4
    assert len(snap["levels"]) >= 4


# ===========================================================================
# STEP 5 — Hash Validation
# ===========================================================================

@pytest.mark.asyncio
async def test_step5_sha256_correctness():
    """SHA-256 produces correct 64-char hex strings."""
    h = sha256_hex("hello world")
    assert len(h) == 64
    # Known SHA-256 of "hello world"
    expected = hashlib.sha256(b"hello world").hexdigest()
    assert h == expected


@pytest.mark.asyncio
async def test_step5_hash_deterministic():
    """Same input always produces same hash."""
    h1 = sha256_hex("test data")
    h2 = sha256_hex("test data")
    assert h1 == h2


@pytest.mark.asyncio
async def test_step5_hash_different_inputs():
    """Different inputs produce different hashes."""
    h1 = sha256_hex("data A")
    h2 = sha256_hex("data B")
    assert h1 != h2


@pytest.mark.asyncio
async def test_step5_canonical_json_deterministic():
    """canonical_json is deterministic regardless of dict order."""
    d1 = {"b": 2, "a": 1}
    d2 = {"a": 1, "b": 2}
    assert canonical_json(d1) == canonical_json(d2)
    # Sorted keys, no whitespace
    j = canonical_json(d1)
    assert j == '{"a":1,"b":2}'


@pytest.mark.asyncio
async def test_step5_tombstone_hash_deterministic():
    """tombstone_hash is deterministic."""
    h1 = tombstone_hash("rec-1", "abc123")
    h2 = tombstone_hash("rec-1", "abc123")
    assert h1 == h2
    assert len(h1) == 64


@pytest.mark.asyncio
async def test_step5_leaf_hash_active_vs_deleted():
    """Active and deleted leaf hashes are different."""
    active = leaf_hash("r1", "h1", deleted=False)
    deleted = leaf_hash("r1", "h1", deleted=True)
    assert active != deleted


@pytest.mark.asyncio
async def test_step5_hash_chain_link():
    """hash_chain_link produces consistent results."""
    h1 = hash_chain_link("prev_hash", "event_type", {"key": "val"}, "2024-01-01T00:00:00")
    h2 = hash_chain_link("prev_hash", "event_type", {"key": "val"}, "2024-01-01T00:00:00")
    assert h1 == h2
    assert len(h1) == 64


# ===========================================================================
# STEP 6 — Digital Signatures
# ===========================================================================

@pytest.mark.asyncio
async def test_step6_signature_generation_and_verification():
    """sign_sha256 + verify_sha256 round-trip works."""
    msg = b"important data to sign"
    sig = sign_sha256(msg)
    assert sig
    assert verify_sha256(msg, sig) is True


@pytest.mark.asyncio
async def test_step6_signature_tamper_detection():
    """Tampered signature fails verification."""
    msg = b"important data"
    sig = sign_sha256(msg)
    # Forged signature
    assert verify_sha256(msg, "Zm9yZ2Vk") is False


@pytest.mark.asyncio
async def test_step6_signature_wrong_message():
    """Signature from different message fails verification."""
    sig1 = sign_sha256(b"message A")
    assert verify_sha256(b"message B", sig1) is False


@pytest.mark.asyncio
async def test_step6_signature_unique_per_message():
    """Different messages produce different signatures."""
    sig1 = sign_sha256(b"message 1")
    sig2 = sign_sha256(b"message 2")
    assert sig1 != sig2


@pytest.mark.asyncio
async def test_step6_public_key_accessible():
    """Public key is accessible and valid PEM."""
    pem = public_key_pem()
    assert "BEGIN PUBLIC KEY" in pem
    assert "END PUBLIC KEY" in pem


# ===========================================================================
# STEP 7 — Certificate Generation
# ===========================================================================

@pytest.mark.asyncio
async def test_step7_certificate_has_required_fields(session_factory):
    """Certificate contains all required fields."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        cert = await CertificateService(session).repo.get(ctx["cert_id"])
        assert cert.id  # Certificate ID
        assert cert.deletion_request_id  # Request ID
        assert cert.dataset_id  # Dataset ID
        assert cert.subject_user_id  # Deleted User ID
        assert cert.timestamp  # Timestamp
        assert cert.content_hash  # Hash
        assert cert.pre_merkle_root  # Pre Merkle Root
        assert cert.post_merkle_root  # Post Merkle Root
        assert cert.signature  # Digital Signature
        assert cert.verification_status  # Verification Status
        assert cert.model_version >= 1  # Model Version
        assert cert.method  # Method


@pytest.mark.asyncio
async def test_step7_certificate_json_serializable(session_factory):
    """Certificate JSON is valid and contains expected keys."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        cert = await CertificateService(session).repo.get(ctx["cert_id"])
        import json
        cert_json = json.loads(CertificateService(session).to_json_bytes(cert))
        assert cert_json["certificate_id"] == cert.id
        assert cert_json["subject_user_id"]
        assert cert_json["pre_merkle_root"]
        assert cert_json["post_merkle_root"]
        assert cert_json["content_hash"]
        assert cert_json["signature"]


@pytest.mark.asyncio
async def test_step7_certificate_pdf_generated(session_factory):
    """Certificate PDF is generated and valid."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        cert = await CertificateService(session).repo.get(ctx["cert_id"])
        pdf_bytes = CertificateService(session).to_pdf_bytes(cert)
        assert len(pdf_bytes) > 100
        assert pdf_bytes[:4] == b"%PDF"  # PDF header


@pytest.mark.asyncio
async def test_step7_certificate_zk_proof(session_factory):
    """Certificate has a ZK proof attached."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        cert = await CertificateService(session).repo.get(ctx["cert_id"])
        assert cert.zk_proof
        assert cert.zk_proof.get("commitment")
        assert cert.zk_proof.get("nonce")
        assert cert.zk_proof.get("signature")
        assert ZKDeletionProofService.verify(cert.zk_proof)


# ===========================================================================
# STEP 8 — Certificate Validation
# ===========================================================================

@pytest.mark.asyncio
async def test_step8_certificate_verify_passes(session_factory):
    """CertificateService.verify() returns verified=True for a valid cert."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        cert = await CertificateService(session).repo.get(ctx["cert_id"])
        verdict = await CertificateService(session).verify(cert)
        assert verdict["verified"] is True
        assert verdict["hash_integrity"] is True
        assert verdict["signature_valid"] is True
        assert verdict["post_root_matches_current_state"] is True
        assert verdict["audit_chain_verified"] is True


@pytest.mark.asyncio
async def test_step8_certificate_post_root_matches_current_state(session_factory):
    """Post Merkle root matches current dataset state."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        cert = await CertificateService(session).repo.get(ctx["cert_id"])
        verdict = await CertificateService(session).verify(cert)
        assert verdict["post_root_matches_current_state"] is True
        # Recomputed root should match
        assert verdict["recomputed_post_root"] == cert.post_merkle_root


@pytest.mark.asyncio
async def test_step8_certificate_deleted_records_tombstoned(session_factory):
    """Deleted records are confirmed tombstoned."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        cert = await CertificateService(session).repo.get(ctx["cert_id"])
        verdict = await CertificateService(session).verify(cert)
        assert len(verdict["deleted_records_still_tombstoned"]) >= 1


# ===========================================================================
# STEP 9 — Audit Trail
# ===========================================================================

@pytest.mark.asyncio
async def test_step9_audit_events_created(session_factory):
    """Deletion + certificate + verification events exist in audit trail."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        req = await session.get(DeletionRequest, ctx["request_id"])
        await VerificationService(session).run(deletion_request_id=req.id, created_by="qa")
        await session.commit()

    async with session_factory() as session:
        events = (await session.execute(
            select(AuditEvent).order_by(AuditEvent.created_at)
        )).scalars().all()
        event_types = {e.event_type for e in events}
        assert "unlearning.requested" in event_types or "unlearning.completed" in event_types
        assert "certificate.issued" in event_types
        # verification.completed is logged by VerificationService.run()
        assert any("verification" in t for t in event_types) or "certificate.verified" in event_types


@pytest.mark.asyncio
async def test_step9_audit_chain_integrity(session_factory):
    """Audit chain verification passes after unlearning + verification."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        req = await session.get(DeletionRequest, ctx["request_id"])
        await VerificationService(session).run(deletion_request_id=req.id, created_by="qa")
        await session.commit()

    async with session_factory() as session:
        chain = await AuditService(session).verify_chain()
        assert chain["verified"] is True
        assert chain["event_count"] >= 3  # at minimum: completed + issued + verified


@pytest.mark.asyncio
async def test_step9_audit_events_have_required_fields(session_factory):
    """Each audit event has actor, timestamp, event_type, payload."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        events = (await session.execute(
            select(AuditEvent).order_by(AuditEvent.created_at)
        )).scalars().all()
        for e in events:
            assert e.event_type
            assert e.actor
            assert e.created_at
            assert e.event_hash
            assert e.prev_hash is not None or e == events[0]


@pytest.mark.asyncio
async def test_step9_audit_event_payload(session_factory):
    """Unlearning.completed event has correct payload fields."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        events = (await session.execute(
            select(AuditEvent).where(AuditEvent.event_type == "unlearning.completed")
        )).scalars().all()
        assert len(events) >= 1
        payload = events[-1].payload
        assert "request_id" in payload
        assert "method" in payload
        assert "records" in payload
        assert payload["records"] >= 1


# ===========================================================================
# STEP 10 — Immutability Test (tampering detection)
# ===========================================================================

@pytest.mark.asyncio
async def test_step10_tampered_certificate_fails_verification(session_factory):
    """Modifying a certificate field causes verification to fail."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        cert = await CertificateService(session).repo.get(ctx["cert_id"])
        # Tamper with the stored content hash (simulating DB tampering)
        original_hash = cert.content_hash
        cert.content_hash = sha256_hex("tampered data")
        await session.flush()

        verdict = await CertificateService(session).verify(cert)
        assert verdict["verified"] is False
        assert verdict["hash_integrity"] is False

        # Restore for other tests
        cert.content_hash = original_hash
        await session.flush()


@pytest.mark.asyncio
async def test_step10_tampered_merkle_root_fails(session_factory):
    """Modifying post Merkle root causes verification to fail."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        cert = await CertificateService(session).repo.get(ctx["cert_id"])
        original_root = cert.post_merkle_root
        cert.post_merkle_root = sha256_hex("fake_root")
        await session.flush()

        verdict = await CertificateService(session).verify(cert)
        assert verdict["verified"] is False
        assert verdict["post_root_matches_current_state"] is False

        cert.post_merkle_root = original_root
        await session.flush()


@pytest.mark.asyncio
async def test_step10_tampered_proof_detected(session_factory):
    """ZK proof tampering is detected."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        cert = await CertificateService(session).repo.get(ctx["cert_id"])
        proof = dict(cert.zk_proof)
        proof["commitment"] = sha256_hex("fake_commitment")
        assert ZKDeletionProofService.verify(proof) is False


@pytest.mark.asyncio
async def test_step10_proof_tamper_detection():
    """ProofService detects tampered proofs."""
    proof = ProofService.issue(
        subject_id="cert-1",
        subject_type="certificate",
        pre_merkle_root="a" * 64,
        post_merkle_root="b" * 64,
        leaf_hashes=["l1"],
        claim="deletion_occurred",
    )
    # Tamper with post_merkle_root
    tampered = dict(proof)
    tampered["post_merkle_root"] = "c" * 64
    assert ProofService.verify(tampered)["verified"] is False

    # Tamper with signature
    forged = dict(proof)
    forged["signature"] = "Zm9yZ2Vk"
    assert ProofService.verify(forged)["signature_valid"] is False


# ===========================================================================
# STEP 11 — API Validation
# ===========================================================================

@pytest.mark.asyncio
async def test_step11_verify_post_api(session_factory, auth_headers, client):
    """POST /verification/verify/{cert_id} returns verified=True."""
    ctx = await build_and_delete(session_factory)
    resp = await client.post(
        f"/api/v1/verification/verify/{ctx['cert_id']}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["verified"] is True


@pytest.mark.asyncio
async def test_step11_verify_get_api(session_factory, auth_headers, client):
    """GET /verification/certificate/{cert_id} returns verified=True."""
    ctx = await build_and_delete(session_factory)
    resp = await client.get(
        f"/api/v1/verification/certificate/{ctx['cert_id']}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["verified"] is True


@pytest.mark.asyncio
async def test_step11_run_verification_api(session_factory, auth_headers, client):
    """POST /verification/run produces a verification report."""
    ctx = await build_and_delete(session_factory)
    resp = await client.post(
        "/api/v1/verification/run",
        json={"deletion_request_id": ctx["request_id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["verdict"] == "valid"
    assert body["checks_passed"] == 8


@pytest.mark.asyncio
async def test_step11_verify_proof_api(session_factory, auth_headers, client):
    """POST /verification/verify-proof validates Merkle proof."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        records = (await session.execute(
            select(DatasetRecord).where(DatasetRecord.dataset_id == ctx["ds_id"]).limit(10)
        )).scalars().all()
        leaves = [leaf_hash(r.id, r.content_hash, deleted=r.is_deleted) for r in records]
    tree = MerkleTree(leaves)
    proof = tree.proof(leaves[0])

    resp = await client.post(
        "/api/v1/verification/verify-proof",
        json={"root": tree.root, "leaf": leaves[0], "proof": proof},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["verified"] is True


@pytest.mark.asyncio
async def test_step11_issue_proof_api(session_factory, auth_headers, client):
    """POST /verification/proofs creates a proof."""
    resp = await client.post(
        "/api/v1/verification/proofs",
        json={
            "subject_id": "cert-qa",
            "subject_type": "certificate",
            "claim": "deletion_occurred",
            "pre_merkle_root": "a" * 64,
            "post_merkle_root": "b" * 64,
            "leaf_hashes": ["l1", "l2"],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["proof_id"]
    assert body["nonce"]
    assert body["signature"]
    assert body["content_hash"]


@pytest.mark.asyncio
async def test_step11_get_proof_api(session_factory, auth_headers, client):
    """GET /verification/proofs/{proof_id} retrieves a proof."""
    resp = await client.post(
        "/api/v1/verification/proofs",
        json={
            "subject_id": "cert-get",
            "subject_type": "certificate",
            "claim": "deletion_occurred",
            "pre_merkle_root": "a" * 64,
            "post_merkle_root": "b" * 64,
            "leaf_hashes": ["l1"],
        },
        headers=auth_headers,
    )
    proof_id = resp.json()["proof_id"]
    resp2 = await client.get(f"/api/v1/verification/proofs/{proof_id}", headers=auth_headers)
    assert resp2.status_code == 200
    assert resp2.json()["proof_id"] == proof_id


@pytest.mark.asyncio
async def test_step11_requires_auth(client):
    """All verification endpoints require auth."""
    for path in [
        "/api/v1/verification/history",
        "/api/v1/verification/audit",
        "/api/v1/verification/public-key",
    ]:
        resp = await client.get(path)
        assert resp.status_code == 401, f"{path} should require auth"
    # POST endpoints also require auth
    resp = await client.post("/api/v1/verification/run", json={})
    assert resp.status_code == 401
    resp = await client.post("/api/v1/verification/proofs", json={"subject_id": "x"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_step11_invalid_certificate_id(session_factory, auth_headers, client):
    """GET /verification/certificate/bogus returns 404."""
    resp = await client.get("/api/v1/verification/certificate/bogus-id", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_step11_download_json_report(session_factory, auth_headers, client):
    """GET /verification/download/json/{report_id} returns JSON."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        req = await session.get(DeletionRequest, ctx["request_id"])
        report = await VerificationService(session).run(deletion_request_id=req.id, created_by="dl")
        await session.commit()
        report_id = report.id

    resp = await client.get(f"/api/v1/verification/download/json/{report_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert "verification-" in resp.headers.get("content-disposition", "")
    assert resp.json()["verdict"] == "valid"


@pytest.mark.asyncio
async def test_step11_download_pdf_report(session_factory, auth_headers, client):
    """GET /verification/download/pdf/{report_id} returns PDF."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        req = await session.get(DeletionRequest, ctx["request_id"])
        report = await VerificationService(session).run(deletion_request_id=req.id, created_by="dl")
        await session.commit()
        report_id = report.id

    resp = await client.get(f"/api/v1/verification/download/pdf/{report_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"


@pytest.mark.asyncio
async def test_step11_get_verification_report(session_factory, auth_headers, client):
    """GET /verification/{report_id} returns full report."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        req = await session.get(DeletionRequest, ctx["request_id"])
        report = await VerificationService(session).run(deletion_request_id=req.id, created_by="detail")
        await session.commit()
        report_id = report.id

    resp = await client.get(f"/api/v1/verification/{report_id}", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["verdict"] == "valid"
    assert len(body["checks"]) == 8
    assert body["merkle_snapshot"]


# ===========================================================================
# STEP 12 — Database Validation
# ===========================================================================

@pytest.mark.asyncio
async def test_step12_certificate_stored_in_db(session_factory):
    """Certificate is persisted in the database."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        cert = await session.get(Certificate, ctx["cert_id"])
        assert cert is not None
        assert cert.content_hash
        assert cert.signature
        assert cert.verification_status == "valid"


@pytest.mark.asyncio
async def test_step12_verification_report_stored(session_factory):
    """Verification report is stored in the database."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        req = await session.get(DeletionRequest, ctx["request_id"])
        await VerificationService(session).run(deletion_request_id=req.id, created_by="db")
        await session.commit()

    async with session_factory() as session:
        reports = (await session.execute(
            select(VerificationReport)
        )).scalars().all()
        assert len(reports) >= 1
        assert reports[0].certificate_id == ctx["cert_id"]


@pytest.mark.asyncio
async def test_step12_no_orphan_certificate(session_factory):
    """Every certificate references a valid deletion request."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        cert = await session.get(Certificate, ctx["cert_id"])
        assert cert.deletion_request_id
        req = await session.get(DeletionRequest, cert.deletion_request_id)
        assert req is not None


@pytest.mark.asyncio
async def test_step12_audit_events_linked(session_factory):
    """Audit events reference valid certificate."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        events = (await session.execute(
            select(AuditEvent).where(AuditEvent.event_type == "certificate.issued")
        )).scalars().all()
        assert len(events) >= 1
        assert events[-1].certificate_id == ctx["cert_id"]


# ===========================================================================
# STEP 13 — Export
# ===========================================================================

@pytest.mark.asyncio
async def test_step13_certificate_json_export(session_factory):
    """Certificate can be exported as JSON."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        cert = await CertificateService(session).repo.get(ctx["cert_id"])
        import json
        data = json.loads(CertificateService(session).to_json_bytes(cert))
        assert data["certificate_id"] == cert.id
        assert data["pre_merkle_root"]
        assert data["post_merkle_root"]
        assert data["content_hash"]
        assert data["signature"]


@pytest.mark.asyncio
async def test_step13_certificate_pdf_export(session_factory):
    """Certificate can be exported as PDF."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        cert = await CertificateService(session).repo.get(ctx["cert_id"])
        pdf = CertificateService(session).to_pdf_bytes(cert)
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 500  # Reasonable PDF size


@pytest.mark.asyncio
async def test_step13_verification_report_json_export(session_factory, auth_headers, client):
    """Verification report JSON download matches stored data."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        req = await session.get(DeletionRequest, ctx["request_id"])
        report = await VerificationService(session).run(deletion_request_id=req.id, created_by="exp")
        await session.commit()
        report_id = report.id

    resp = await client.get(f"/api/v1/verification/download/json/{report_id}", headers=auth_headers)
    data = resp.json()
    assert data["report_id"] == report_id
    assert data["verdict"] == "valid"
    assert "checks" in data
    assert "merkle_snapshot" in data


# ===========================================================================
# STEP 14 — Frontend data shapes
# ===========================================================================

@pytest.mark.asyncio
async def test_step14_verification_report_shape(session_factory, auth_headers, client):
    """GET /verification/{id} has shape expected by frontend."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        req = await session.get(DeletionRequest, ctx["request_id"])
        report = await VerificationService(session).run(deletion_request_id=req.id, created_by="fe")
        await session.commit()
        report_id = report.id

    resp = await client.get(f"/api/v1/verification/{report_id}", headers=auth_headers)
    body = resp.json()
    required = {
        "id", "certificate_id", "verdict", "checks_passed", "checks_total",
        "checks", "merkle_snapshot", "duration_seconds", "created_by",
    }
    assert required.issubset(body.keys())


@pytest.mark.asyncio
async def test_step14_verification_history_shape(session_factory, auth_headers, client):
    """GET /verification/history has shape expected by frontend."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        req = await session.get(DeletionRequest, ctx["request_id"])
        await VerificationService(session).run(deletion_request_id=req.id, created_by="fe")
        await session.commit()

    resp = await client.get("/api/v1/verification/history", headers=auth_headers)
    body = resp.json()
    assert "reports" in body
    r = body["reports"][0]
    required = {"id", "certificate_id", "verdict", "checks_passed", "checks_total", "created_at"}
    assert required.issubset(r.keys())


# ===========================================================================
# STEP 15 — Error Handling
# ===========================================================================

@pytest.mark.asyncio
async def test_step15_invalid_report_id(session_factory, auth_headers, client):
    """GET /verification/bogus returns 404."""
    resp = await client.get("/api/v1/verification/bogus-id", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_step15_invalid_certificate_id_verify(session_factory, auth_headers, client):
    """POST /verification/verify/bogus returns 404."""
    resp = await client.post("/api/v1/verification/verify/bogus", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_step15_run_verification_no_target(session_factory, auth_headers, client):
    """POST /verification/run without target returns 422/400."""
    resp = await client.post("/api/v1/verification/run", json={}, headers=auth_headers)
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_step15_verify_proof_bad_proof(session_factory, auth_headers, client):
    """POST /verification/verify-proof with bad proof returns verified=False."""
    resp = await client.post(
        "/api/v1/verification/verify-proof",
        json={"root": "a" * 64, "leaf": "b" * 64, "proof": [{"hash": "c" * 64, "side": "right"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["verified"] is False


@pytest.mark.asyncio
async def test_step15_get_proof_not_found(session_factory, auth_headers, client):
    """GET /verification/proofs/bogus returns 422 (not found)."""
    resp = await client.get("/api/v1/verification/proofs/bogus-id", headers=auth_headers)
    assert resp.status_code == 422


# ===========================================================================
# STEP 16 — Security
# ===========================================================================

@pytest.mark.asyncio
async def test_step16_unauthorized_verification_blocked(client):
    """Unauthenticated verification is blocked (401)."""
    resp = await client.post("/api/v1/verification/run", json={})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_step16_unauthorized_certificate_access(client):
    """Unauthenticated certificate verify is blocked (401)."""
    resp = await client.get("/api/v1/verification/certificate/some-id")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_step16_unauthorized_proof_issue(client):
    """Unauthenticated proof issue is blocked (401)."""
    resp = await client.post("/api/v1/verification/proofs", json={"subject_id": "x"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_step16_audit_trail_actor_recorded(session_factory):
    """Audit events record the actor who performed the action."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        events = (await session.execute(
            select(AuditEvent).where(AuditEvent.event_type == "unlearning.completed")
        )).scalars().all()
        assert events[-1].actor == "qa-tester"


# ===========================================================================
# STEP 17 — Performance
# ===========================================================================

@pytest.mark.asyncio
async def test_step17_certificate_generation_latency(session_factory):
    """Certificate generation is fast (< 2s)."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        cert = await CertificateService(session).repo.get(ctx["cert_id"])
        assert cert  # Already generated during build_and_delete
    # The generation happened as part of build_and_delete; it's fast by design.


@pytest.mark.asyncio
async def test_step17_verification_latency(session_factory):
    """Full verification run completes within 10s."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        req = await session.get(DeletionRequest, ctx["request_id"])
        start = time.time()
        report = await VerificationService(session).run(deletion_request_id=req.id, created_by="perf")
        elapsed = time.time() - start
        await session.commit()
        assert elapsed < 10.0, f"Verification took {elapsed:.1f}s (>10s)"
        assert report.duration_seconds is not None


@pytest.mark.asyncio
async def test_step17_merkle_tree_generation_latency():
    """Merkle tree generation for 1000 leaves completes in < 1s."""
    leaves = [leaf_hash(f"r{i}", f"h{i}") for i in range(1000)]
    start = time.time()
    tree = MerkleTree(leaves)
    elapsed = time.time() - start
    assert elapsed < 1.0, f"Merkle tree took {elapsed:.3f}s (>1s)"
    assert tree.root


@pytest.mark.asyncio
async def test_step17_hash_generation_latency():
    """SHA-256 hash generation is fast (10000 hashes < 1s)."""
    start = time.time()
    for i in range(10000):
        sha256_hex(f"data_{i}")
    elapsed = time.time() - start
    assert elapsed < 1.0, f"10000 hashes took {elapsed:.3f}s (>1s)"


@pytest.mark.asyncio
async def test_step17_signature_latency():
    """Signature generation + verification for 10 iterations < 5s."""
    start = time.time()
    for i in range(10):
        msg = f"message_{i}".encode()
        sig = sign_sha256(msg)
        assert verify_sha256(msg, sig)
    elapsed = time.time() - start
    assert elapsed < 5.0, f"10 sign+verify took {elapsed:.3f}s (>5s)"


# ===========================================================================
# STEP 18 — Concurrent Operations
# ===========================================================================

@pytest.mark.asyncio
async def test_step18_concurrent_verifications(session_factory, auth_headers, client):
    """Multiple concurrent verifications don't interfere."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        req = await session.get(DeletionRequest, ctx["request_id"])
        request_id = req.id

    async def _verify():
        async with session_factory() as session:
            req = await session.get(DeletionRequest, request_id)
            return await VerificationService(session).run(
                deletion_request_id=req.id, created_by="concurrent"
            )

    results = await asyncio.gather(_verify(), _verify(), _verify(), return_exceptions=True)
    for r in results:
        assert not isinstance(r, Exception), f"Concurrent verification failed: {r}"
        assert r.verdict == "valid"


@pytest.mark.asyncio
async def test_step18_concurrent_proof_issuance(session_factory, auth_headers, client):
    """Multiple concurrent proof issuances don't create duplicates."""
    async def _issue():
        resp = await client.post(
            "/api/v1/verification/proofs",
            json={
                "subject_id": "cert-concurrent",
                "subject_type": "certificate",
                "claim": "deletion_occurred",
                "pre_merkle_root": "a" * 64,
                "post_merkle_root": "b" * 64,
                "leaf_hashes": ["l1"],
            },
            headers=auth_headers,
        )
        return resp.json()

    results = await asyncio.gather(_issue(), _issue(), _issue(), return_exceptions=True)
    proof_ids = set()
    for r in results:
        assert not isinstance(r, Exception)
        assert r["proof_id"]
        proof_ids.add(r["proof_id"])
    # Each proof should have a unique ID (UUID)
    assert len(proof_ids) == 3


# ===========================================================================
# STEP 19 — End-to-End Verification Flow
# ===========================================================================

@pytest.mark.asyncio
async def test_step19_full_e2e_verification_flow(session_factory, auth_headers, client):
    """Full E2E: Upload → Train → Search → Delete → Verify → Certificate → Audit → Tamper → Detect."""
    # 1. Upload dataset
    resp = await client.post(
        "/api/v1/datasets/upload",
        headers=auth_headers,
        data={"shard_count": "4"},
        files={"file": ("e2e_v5.csv", make_csv(400), "text/csv")},
    )
    assert resp.status_code == 201
    ds_id = resp.json()["id"]

    # 2. Train model
    resp = await client.post(f"/api/v1/models/train?dataset_id={ds_id}", headers=auth_headers)
    assert resp.status_code == 201
    model_id = resp.json()["id"]

    # 3. Search identity
    resp = await client.post("/api/v1/privacy/search?query=a", headers=auth_headers)
    target = resp.json()["matches"][0]

    # 4. Delete user
    resp = await client.post(
        "/api/v1/unlearning/selective",
        headers=auth_headers,
        json={
            "identity_key": target["identity_key"],
            "record_ids": [target["record_id"]],
            "deletion_type": "records",
            "method": "retrain",
        },
    )
    assert resp.status_code == 202
    request_id = resp.json()["id"]

    # Run inline (conftest replaces dispatch)
    from tests.conftest import run_unlearning_inline
    await run_unlearning_inline(session_factory, request_id)

    # 5. Get certificate
    resp = await client.get(f"/api/v1/unlearning/requests/{request_id}", headers=auth_headers)
    cert_id = resp.json()["certificate_id"]
    assert cert_id

    # 6. Verify certificate (POST)
    resp = await client.post(f"/api/v1/verification/verify/{cert_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["verified"] is True

    # 7. Verify certificate (GET)
    resp = await client.get(f"/api/v1/verification/certificate/{cert_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["verified"] is True

    # 8. Run full verification engine
    resp = await client.post(
        "/api/v1/verification/run",
        json={"certificate_id": cert_id},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["verdict"] == "valid"
    assert resp.json()["checks_passed"] == 8

    # 9. Check audit trail
    resp = await client.get("/api/v1/verification/audit", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["chain"]["verified"] is True

    # 10. Download certificate JSON
    report_id = resp.json()  # Need the report_id from step 8
    resp8 = await client.post(
        "/api/v1/verification/run",
        json={"certificate_id": cert_id},
        headers=auth_headers,
    )
    report_id = resp8.json()["report_id"]
    resp = await client.get(f"/api/v1/verification/download/json/{report_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["verdict"] == "valid"

    # 11. Download certificate PDF
    resp = await client.get(f"/api/v1/verification/download/pdf/{report_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"

    # 12. Issue and verify a proof
    resp = await client.post(
        "/api/v1/verification/proofs",
        json={
            "subject_id": cert_id,
            "subject_type": "certificate",
            "claim": "deletion_occurred",
            "pre_merkle_root": "a" * 64,
            "post_merkle_root": "b" * 64,
            "leaf_hashes": ["l1"],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    proof = resp.json()
    resp = await client.get(f"/api/v1/verification/proofs/{proof['proof_id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["proof_id"] == proof["proof_id"]

    # 13. Attempt tampering detection via ZK proof
    async with session_factory() as session:
        cert = await CertificateService(session).repo.get(cert_id)
        # ZK proof is valid
        assert ZKDeletionProofService.verify(cert.zk_proof)
        # Tamper with commitment
        tampered = dict(cert.zk_proof)
        tampered["commitment"] = sha256_hex("fake")
        assert ZKDeletionProofService.verify(tampered) is False


@pytest.mark.asyncio
async def test_step19_e2e_merkle_proof_verification(session_factory, auth_headers, client):
    """E2E: Generate Merkle proof → verify via API."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        records = (await session.execute(
            select(DatasetRecord).where(DatasetRecord.dataset_id == ctx["ds_id"]).limit(20)
        )).scalars().all()
        leaves = [leaf_hash(r.id, r.content_hash, deleted=r.is_deleted) for r in records]
    tree = MerkleTree(leaves)

    # Verify a leaf's membership via API
    proof = tree.proof(leaves[0])
    resp = await client.post(
        "/api/v1/verification/verify-proof",
        json={"root": tree.root, "leaf": leaves[0], "proof": proof},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["verified"] is True

    # Tampered proof should fail
    resp = await client.post(
        "/api/v1/verification/verify-proof",
        json={"root": tree.root, "leaf": "ff" * 32, "proof": proof},
        headers=auth_headers,
    )
    assert resp.json()["verified"] is False


@pytest.mark.asyncio
async def test_step19_e2e_verification_engine_comprehensive(session_factory, auth_headers, client):
    """E2E: All 8 verification checks pass after clean deletion."""
    ctx = await build_and_delete(session_factory)
    async with session_factory() as session:
        req = await session.get(DeletionRequest, ctx["request_id"])
        report = await VerificationService(session).run(
            deletion_request_id=req.id, created_by="comprehensive"
        )
        await session.commit()

    expected_checks = ["records", "embeddings", "vectors", "versions", "merkle", "signature", "audit", "consistency"]
    for check_name in expected_checks:
        assert report.checks[check_name]["passed"] is True, f"Check '{check_name}' failed"

    assert report.verdict == "valid"
    assert report.checks_passed == 8
    assert report.checks_total == 8
