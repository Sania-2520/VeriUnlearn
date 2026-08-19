from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, Response

from app.api.deps import CurrentUser, DbSession
from app.core.exceptions import ValidationFailedError
from app.core.security import public_key_pem
from app.db.models import CryptoProof
from app.repositories.audit_repo import AuditRepository
from app.repositories.certificate_repo import CertificateRepository
from app.repositories.verification_repo import CryptoProofRepository
from app.schemas.certificate import VerificationOut
from app.schemas.verification import (
    ProofIssueRequest,
    ProofOut,
    ProofVerifyOut,
    ProofVerifyRequest,
    VerificationReportOut,
    VerificationRunRequest,
)
from app.services.certificate import CertificateService
from app.services.crypto import MerkleTree
from app.services.proofs import ProofService
from app.services.verification_engine import VerificationService

router = APIRouter(prefix="/verification", tags=["verification"])


# ------------------------------------------------------------------ run / get


@router.post("/run")
async def run_verification(
    payload: VerificationRunRequest, db: DbSession, user: CurrentUser
) -> dict:
    """Run a full deletion-verification job (records, embeddings, vectors,
    versions, Merkle roots, signature, audit chain, consistency)."""
    report = await VerificationService(db).run(
        certificate_id=payload.certificate_id,
        deletion_request_id=payload.deletion_request_id,
        dataset_id=payload.dataset_id,
        created_by=user["sub"],
    )
    return {
        "report_id": report.id,
        "verdict": report.verdict,
        "checks_passed": report.checks_passed,
        "checks_total": report.checks_total,
        "duration_seconds": report.duration_seconds,
        "certificate_id": report.certificate_id,
    }


@router.get("/history")
async def verification_history(db: DbSession, user: CurrentUser, limit: int = Query(default=50, ge=1, le=200)) -> dict:
    reports = await VerificationService(db).list_reports(limit=limit)
    return {
        "reports": [
            {
                "id": r.id,
                "certificate_id": r.certificate_id,
                "deletion_request_id": r.deletion_request_id,
                "dataset_id": r.dataset_id,
                "verdict": r.verdict,
                "checks_passed": r.checks_passed,
                "checks_total": r.checks_total,
                "duration_seconds": r.duration_seconds,
                "created_by": r.created_by,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reports
        ]
    }


@router.get("/audit")
async def verification_audit(db: DbSession, user: CurrentUser, limit: int = Query(default=100, ge=1, le=500)) -> dict:
    """Audit-chain status + recent events (Phase 5 external audit view)."""
    audit = AuditRepository(db)
    chain = await audit_chain_check(audit)
    events = await audit.ordered_events()
    return {
        "chain": chain,
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "actor": e.actor,
                "subject": e.subject,
                "certificate_id": e.certificate_id,
                "prev_hash": e.prev_hash,
                "event_hash": e.event_hash,
                "payload": e.payload,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events[-limit:]
        ],
    }


async def audit_chain_check(audit: AuditRepository) -> dict:
    events = await audit.ordered_events()
    from app.services.crypto import hash_chain_link

    prev: str | None = None
    broken_at: str | None = None
    for event in events:
        recomputed = hash_chain_link(
            event.prev_hash, event.event_type, event.payload, event.created_at.isoformat()
        )
        if event.prev_hash != prev or recomputed != event.event_hash:
            broken_at = event.id
            break
        prev = event.event_hash
    return {
        "verified": broken_at is None,
        "event_count": len(events),
        "broken_event_id": broken_at,
        "head_hash": prev,
    }


@router.get("/public-key")
async def get_public_key(db: DbSession, user: CurrentUser) -> dict:
    """Server RSA public key for external verification of signatures/proofs."""
    return {"algorithm": "RSA-PKCS1v15-SHA256", "key_bits": 2048, "public_key_pem": public_key_pem()}


@router.get("/certificate/{certificate_id}", response_model=VerificationOut)
async def verify_certificate(certificate_id: str, db: DbSession, user: CurrentUser) -> VerificationOut:
    """Independently verify a deletion certificate (hash + signature + roots)."""
    cert = await CertificateRepository(db).get(certificate_id)
    result = await CertificateService(db).verify(cert)
    return VerificationOut(**result)


# Legacy compatibility: POST /verify/{certificate_id}
@router.post("/verify/{certificate_id}", response_model=VerificationOut)
async def verify_certificate_post(certificate_id: str, db: DbSession, user: CurrentUser) -> VerificationOut:
    cert = await CertificateRepository(db).get(certificate_id)
    result = await CertificateService(db).verify(cert)
    return VerificationOut(**result)


# -------------------------------------------------------------------- proofs


@router.post("/verify-proof", response_model=ProofVerifyOut)
async def verify_merkle_proof(payload: ProofVerifyRequest, db: DbSession, user: CurrentUser) -> ProofVerifyOut:
    """Verify a Merkle membership proof against a published root.

    Also accepts ``leaf``/``proof`` omitted to simply validate the root
    structure — pass an empty proof to check ``leaf`` is the root itself.
    """
    if not payload.proof:
        verified = payload.leaf == payload.root
    else:
        verified = MerkleTree.verify(payload.root, payload.leaf, payload.proof)
    return ProofVerifyOut(
        verified=verified,
        reason="ok" if verified else "proof does not chain to root",
        hash_integrity=True,
        signature_valid=False,
        nonce_present=False,
        timestamp_valid=False,
    )


@router.post("/proofs", response_model=ProofOut)
async def issue_proof(payload: ProofIssueRequest, db: DbSession, user: CurrentUser) -> ProofOut:
    """Generate an immutable cryptographic proof (nonce + signature)."""
    proof = ProofService.issue(
        subject_id=payload.subject_id,
        subject_type=payload.subject_type,
        pre_merkle_root=payload.pre_merkle_root,
        post_merkle_root=payload.post_merkle_root,
        leaf_hashes=payload.leaf_hashes,
        claim=payload.claim,
    )
    row = CryptoProof(
        proof_id=proof["proof_id"],
        subject_id=payload.subject_id,
        subject_type=payload.subject_type,
        claim=payload.claim,
        pre_merkle_root=payload.pre_merkle_root,
        post_merkle_root=payload.post_merkle_root,
        leaf_hashes=sorted(payload.leaf_hashes),
        nonce=proof["nonce"],
        timestamp=proof["timestamp"],
        content_hash=proof["content_hash"],
        signature=proof["signature"],
        scheme=proof["scheme"],
        verification_status="pending",
    )
    row = await CryptoProofRepository(db).create(row)
    return ProofOut(
        proof_id=row.proof_id,
        subject_id=row.subject_id,
        subject_type=row.subject_type,
        claim=row.claim,
        pre_merkle_root=row.pre_merkle_root,
        post_merkle_root=row.post_merkle_root,
        leaf_hashes=row.leaf_hashes,
        nonce=row.nonce,
        timestamp=row.timestamp,
        content_hash=row.content_hash,
        signature=row.signature,
        scheme=row.scheme,
        verification_status=row.verification_status,
    )


@router.get("/proofs/{proof_id}", response_model=ProofOut)
async def get_proof(proof_id: str, db: DbSession, user: CurrentUser) -> ProofOut:
    row = await CryptoProofRepository(db).get_by_proof_id(proof_id)
    if row is None:
        raise ValidationFailedError(f"Proof {proof_id} not found")
    return ProofOut(
        proof_id=row.proof_id,
        subject_id=row.subject_id,
        subject_type=row.subject_type,
        claim=row.claim,
        pre_merkle_root=row.pre_merkle_root,
        post_merkle_root=row.post_merkle_root,
        leaf_hashes=row.leaf_hashes,
        nonce=row.nonce,
        timestamp=row.timestamp,
        content_hash=row.content_hash,
        signature=row.signature,
        scheme=row.scheme,
        verification_status=row.verification_status,
    )


# ----------------------------------------------------------------- downloads


@router.get("/download/json/{report_id}")
async def download_report_json(report_id: str, db: DbSession, user: CurrentUser) -> JSONResponse:
    report = await VerificationService(db).get_report(report_id)
    payload = {
        "report_id": report.id,
        "verdict": report.verdict,
        "checks_passed": report.checks_passed,
        "checks_total": report.checks_total,
        "checks": report.checks,
        "merkle_snapshot": report.merkle_snapshot,
        "duration_seconds": report.duration_seconds,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }
    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": f'attachment; filename="verification-{report_id}.json"'},
    )


@router.get("/download/pdf/{report_id}")
async def download_report_pdf(report_id: str, db: DbSession, user: CurrentUser) -> Response:
    """Render the verification report as a PDF (pure Python)."""
    from fpdf import FPDF

    report = await VerificationService(db).get_report(report_id)

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "VeriUnlearn Verification Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, "Deletion verification - records, embeddings, vectors, Merkle, signature, audit", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    rows: list[tuple[str, str]] = [
        ("Report ID", report.id),
        ("Certificate ID", report.certificate_id),
        ("Dataset ID", report.dataset_id or "-"),
        ("Verdict", report.verdict.upper()),
        ("Checks", f"{report.checks_passed}/{report.checks_total}"),
        ("Duration", f"{report.duration_seconds}s" if report.duration_seconds is not None else "-"),
        ("Created By", report.created_by),
    ]
    for label, value in rows:
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(48, 7, label)
        pdf.set_font("Courier", "", 8)
        pdf.multi_cell(0, 7, value, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 8, "Checks", new_x="LMARGIN", new_y="NEXT")
    for name, check in report.checks.items():
        pdf.set_font("Helvetica", "B", 9)
        status = "PASS" if check.get("passed") else "FAIL"
        pdf.cell(60, 7, f"  {name}: {status}")
        pdf.set_font("Courier", "", 8)
        pdf.multi_cell(0, 7, "", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, "Verify via POST /api/v1/verification/run", new_x="LMARGIN", new_y="NEXT")
    return Response(
        content=bytes(pdf.output()),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="verification-{report_id}.pdf"'},
    )


# ------------------------------------------------------------------- detail


@router.get("/{report_id}", response_model=VerificationReportOut)
async def get_verification_report(report_id: str, db: DbSession, user: CurrentUser) -> VerificationReportOut:
    report = await VerificationService(db).get_report(report_id)
    return VerificationReportOut(
        id=report.id,
        certificate_id=report.certificate_id,
        deletion_request_id=report.deletion_request_id,
        dataset_id=report.dataset_id,
        model_id=report.model_id,
        verdict=report.verdict,
        checks_passed=report.checks_passed,
        checks_total=report.checks_total,
        checks=report.checks,
        merkle_snapshot=report.merkle_snapshot,
        duration_seconds=report.duration_seconds,
        created_by=report.created_by,
        created_at=report.created_at,
    )



