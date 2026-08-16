"""Deletion certificate lifecycle.

A certificate binds the *pre/post* dataset Merkle roots, the model state hash,
the deleted record hashes, and metadata into one signed document. Verifying a
certificate re-hashes the content, checks the RSA signature, re-derives the
expected post-root from the current dataset state, and (optionally) checks the
audit chain.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fpdf import FPDF
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import sign_sha256, verify_sha256
from app.db.models import Certificate
from app.repositories.certificate_repo import CertificateRepository
from app.services.audit import AuditService
from app.services.crypto import canonical_json, sha256_hex


class CertificateService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CertificateRepository(session)
        self.audit = AuditService(session)

    async def issue(
        self,        *,
        subject_user_id: str,
        deletion_type: str,
        deleted_record_count: int,
        dataset_id: str | None = None,
        model_id: str | None,
        model_version: int,
        shard_ids: list[int],
        pre_merkle_root: str,
        post_merkle_root: str,
        deleted_record_hashes: list[str],
        method: str,
        deletion_request_id: str | None = None,
        certified_bound: float | None = None,
        zk_proof: dict[str, Any] | None = None,
        actor: str = "system",
    ) -> Certificate:
        cert_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        body = {
            "certificate_id": cert_id,
            "subject_user_id": subject_user_id,
            "deletion_type": deletion_type,
            "deleted_record_count": deleted_record_count,
            "dataset_id": dataset_id,
            "model_id": model_id,
            "model_version": model_version,
            "shard_ids": shard_ids,
            "pre_merkle_root": pre_merkle_root,
            "post_merkle_root": post_merkle_root,
            "deleted_record_hashes": deleted_record_hashes,
            "method": method,
            "certified_bound": certified_bound,
            "timestamp": timestamp,
            "issuer": settings.APP_NAME,
        }
        content_hash = sha256_hex(canonical_json(body))
        signature = sign_sha256(canonical_json(body).encode("utf-8"))

        certificate = Certificate(
            id=cert_id,
            deletion_request_id=deletion_request_id,
            subject_user_id=subject_user_id,
            deletion_type=deletion_type,
            deleted_record_count=deleted_record_count,
            dataset_id=dataset_id,
            model_id=model_id,
            model_version=model_version,
            shard_ids=shard_ids,
            pre_merkle_root=pre_merkle_root,
            post_merkle_root=post_merkle_root,
            deleted_record_hashes=deleted_record_hashes,
            method=method,
            certified_bound=certified_bound,
            timestamp=timestamp,
            content_hash=content_hash,
            signature=signature,
            verification_status="valid",  # freshly issued by the authority
            certificate_json={**body, "content_hash": content_hash, "signature": signature},
            zk_proof=zk_proof or {},
        )
        certificate = await self.repo.create(certificate)

        await self.audit.log(
            event_type="certificate.issued",
            actor=actor,
            subject=subject_user_id,
            certificate_id=cert_id,
            payload={
                "deletion_type": deletion_type,
                "pre_root": pre_merkle_root,
                "post_root": post_merkle_root,
                "record_count": deleted_record_count,
            },
        )
        return certificate

    async def verify(self, certificate: Certificate) -> dict[str, Any]:
        """Independently re-derive content hash, signature and Merkle roots."""
        body = {
            "certificate_id": certificate.id,
            "subject_user_id": certificate.subject_user_id,
            "deletion_type": certificate.deletion_type,
            "deleted_record_count": certificate.deleted_record_count,
            "dataset_id": certificate.dataset_id,
            "model_id": certificate.model_id,
            "model_version": certificate.model_version,
            "shard_ids": certificate.shard_ids,
            "pre_merkle_root": certificate.pre_merkle_root,
            "post_merkle_root": certificate.post_merkle_root,
            "deleted_record_hashes": certificate.deleted_record_hashes,
            "method": certificate.method,
            "certified_bound": certificate.certified_bound,
            "timestamp": certificate.timestamp,
            "issuer": settings.APP_NAME,
        }
        recomputed_hash = sha256_hex(canonical_json(body))
        hash_ok = recomputed_hash == certificate.content_hash
        sig_ok = verify_sha256(canonical_json(body).encode("utf-8"), certificate.signature)

        from app.services.privacy import recompute_dataset_roots  # local import avoids cycle

        root_state = await recompute_dataset_roots(
            self.session, certificate.dataset_id, certificate.deleted_record_hashes
        )
        post_root_ok = root_state["post_root"] == certificate.post_merkle_root

        verdict = hash_ok and sig_ok and post_root_ok
        certificate.verification_status = "valid" if verdict else "invalid"
        await self.session.flush()

        await self.audit.log(
            event_type="certificate.verified",
            actor="verifier",
            subject=certificate.subject_user_id,
            certificate_id=certificate.id,
            payload={"verdict": "valid" if verdict else "invalid"},
        )
        return {
            "certificate_id": certificate.id,
            "verified": verdict,
            "hash_integrity": hash_ok,
            "signature_valid": sig_ok,
            "post_root_matches_current_state": post_root_ok,
            "recomputed_post_root": root_state["post_root"],
            "deleted_records_still_tombstoned": root_state["tombstoned"],
            "audit_chain_verified": (await self.audit.verify_chain())["verified"],
        }

    def to_json_bytes(self, certificate: Certificate) -> bytes:
        return json.dumps(certificate.certificate_json, indent=2).encode("utf-8")

    def to_pdf_bytes(self, certificate: Certificate) -> bytes:
        """Render a compact certificate PDF (pure Python, no system fonts)."""
        pdf = FPDF(format="A4")
        pdf.set_auto_page_break(auto=True, margin=18)
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(0, 12, "VeriUnlearn Deletion Certificate", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, "Verifiable Machine Unlearning - GDPR Art. 17 / DPDP Act 2023", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

        data = certificate.certificate_json
        rows: list[tuple[str, str]] = [
            ("Certificate ID", data.get("certificate_id", "")),
            ("Subject User ID", data.get("subject_user_id", "")),
            ("Deletion Type", data.get("deletion_type", "")),
            ("Deleted Records", str(data.get("deleted_record_count", ""))),
            ("Method", data.get("method", "")),
            ("Model ID", data.get("model_id") or "-"),
            ("Model Version", str(data.get("model_version", ""))),
            ("Shards", ",".join(str(s) for s in data.get("shard_ids", [])) or "-"),
            ("Certified Bound", str(data.get("certified_bound") or "-")),
            ("Pre Merkle Root", data.get("pre_merkle_root", "")),
            ("Post Merkle Root", data.get("post_merkle_root", "")),
            ("Timestamp", data.get("timestamp", "")),
            ("Content Hash (SHA-256)", data.get("content_hash", "")),
            ("Digital Signature", (data.get("signature") or "")[:64] + "..."),
            ("Issuer", data.get("issuer", "")),
            ("Verification Status", certificate.verification_status),
        ]
        for label, value in rows:
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(48, 7, label)
            pdf.set_font("Courier", "", 8)
            pdf.multi_cell(0, 7, value, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 5, "Verifiable via POST /api/v1/verification/verify", new_x="LMARGIN", new_y="NEXT")
        return bytes(pdf.output())

    async def persist_pdf(self, certificate: Certificate) -> str:
        pdf_dir = Path(settings.DATA_DIR) / "certificates"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        path = pdf_dir / f"{certificate.id}.pdf"
        path.write_bytes(self.to_pdf_bytes(certificate))
        certificate.pdf_path = str(path)
        await self.session.flush()
        return str(path)
