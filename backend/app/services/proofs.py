"""Cryptographic Proof Generator (Phase 5).

Creates **immutable proof objects** that attest a machine-unlearning operation:

- a generated ``proof_id`` (UUIDv4)
- the subject (certificate / deletion request / dataset) and what is claimed
- the pre/post Merkle roots (the actual state transition being proven)
- the leaf hashes covered by the proof
- a **nonce** (fresh per proof → replay protection)
- an ISO **timestamp**
- a SHA-256 **content hash** of the canonical body
- an RSA **signature** over that hash by the server authority

``verify`` independently re-hashes the body, checks the nonce/timestamp, and
validates the RSA signature — so the proof can be checked by any party holding
the public key (external verification).
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.security import sign_sha256, verify_sha256
from app.services.crypto import canonical_json, sha256_hex


class ProofService:
    """Issues and verifies immutable deletion proofs."""

    @staticmethod
    def _fresh_nonce() -> str:
        return os.urandom(24).hex()

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def issue(
        *,
        subject_id: str,
        subject_type: str,
        pre_merkle_root: str,
        post_merkle_root: str,
        leaf_hashes: list[str],
        claim: str,
        issuer: str = "VeriUnlearn",
    ) -> dict[str, Any]:
        """Build and sign an immutable proof object."""
        proof_id = str(uuid.uuid4())
        nonce = ProofService._fresh_nonce()
        timestamp = ProofService._now_iso()

        body = {
            "proof_id": proof_id,
            "subject_id": subject_id,
            "subject_type": subject_type,
            "claim": claim,
            "pre_merkle_root": pre_merkle_root,
            "post_merkle_root": post_merkle_root,
            "leaf_hashes": sorted(leaf_hashes),
            "nonce": nonce,
            "timestamp": timestamp,
            "issuer": issuer,
        }
        content_hash = sha256_hex(canonical_json(body))
        signature = sign_sha256(content_hash.encode("utf-8"))
        return {
            **body,
            "content_hash": content_hash,
            "signature": signature,
            "scheme": "rsa-pkcs1v15-sha256",
        }

    @staticmethod
    def verify(proof: dict[str, Any]) -> dict[str, Any]:
        """Independent verification: structure, hash, nonce, timestamp, signature.

        Returns a detailed verdict so callers can surface *why* a proof failed.
        """
        required = [
            "proof_id", "subject_id", "subject_type", "claim",
            "pre_merkle_root", "post_merkle_root", "leaf_hashes",
            "nonce", "timestamp", "content_hash", "signature",
        ]
        missing = [k for k in required if not proof.get(k)]
        if missing:
            return {
                "verified": False,
                "reason": f"missing fields: {', '.join(missing)}",
                "hash_integrity": False,
                "signature_valid": False,
                "nonce_present": False,
                "timestamp_valid": False,
            }

        body = {
            "proof_id": proof["proof_id"],
            "subject_id": proof["subject_id"],
            "subject_type": proof["subject_type"],
            "claim": proof["claim"],
            "pre_merkle_root": proof["pre_merkle_root"],
            "post_merkle_root": proof["post_merkle_root"],
            "leaf_hashes": sorted(proof["leaf_hashes"]),
            "nonce": proof["nonce"],
            "timestamp": proof["timestamp"],
            "issuer": proof.get("issuer", "VeriUnlearn"),
        }
        hash_ok = sha256_hex(canonical_json(body)) == proof["content_hash"]
        sig_ok = verify_sha256(proof["content_hash"].encode("utf-8"), proof["signature"])

        # Timestamp sanity: must parse and not be in the future.
        timestamp_valid = False
        try:
            ts = datetime.fromisoformat(proof["timestamp"])
            timestamp_valid = ts.timestamp() <= datetime.now(timezone.utc).timestamp() + 60
        except (ValueError, TypeError):
            timestamp_valid = False

        verified = hash_ok and sig_ok and bool(proof["nonce"]) and timestamp_valid
        return {
            "verified": verified,
            "reason": "ok" if verified else "integrity or signature check failed",
            "hash_integrity": hash_ok,
            "signature_valid": sig_ok,
            "nonce_present": bool(proof["nonce"]),
            "timestamp_valid": timestamp_valid,
        }
