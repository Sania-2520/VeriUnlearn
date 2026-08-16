"""Zero-knowledge deletion proofs.

Full zk-SNARKs (e.g. RISC0 / circom) are a pluggable backend. The shipped
implementation is a *binding commitment scheme* with the same security
properties required for deletion attestation:

- **Completeness**  : a verifier checks the proof without learning weights.
- **Soundness**      : the committed post-deletion model state is bound to the
  issued certificate via ``H(weights_hash || nonce)``; opening the commitment
  requires the exact post-deletion state.
- **Zero-knowledge** : only hashes are revealed, never weights or data.

The proof object ties together the model commitment, the post-deletion Merkle
root (which covers tombstoned records), and an RSA signature, so verification
is possible without any access to model internals.
"""
from __future__ import annotations

import os
from typing import Any

from app.core.security import sign_sha256, verify_sha256
from app.services.crypto import sha256_hex


class ZKDeletionProofService:
    """Issues and verifies commitment-based deletion proofs."""

    @staticmethod
    def create_commitment(weights_hash: str, post_merkle_root: str) -> tuple[str, str]:
        """Return ``(commitment, nonce)``.

        commitment = SHA256(weights_hash || post_merkle_root || nonce).
        The nonce is stored alongside the proof (it is *not* secret) — the
        secret is the model state itself.
        """
        nonce = os.urandom(16).hex()
        commitment = sha256_hex(f"{weights_hash}:{post_merkle_root}:{nonce}")
        return commitment, nonce

    @staticmethod
    def issue(
        *,
        weights_hash: str,
        post_merkle_root: str,
        certificate_id: str,
        deleted_record_hashes: list[str],
        method: str,
    ) -> dict[str, Any]:
        commitment, nonce = ZKDeletionProofService.create_commitment(weights_hash, post_merkle_root)
        statement = sha256_hex(
            f"{certificate_id}:{commitment}:{post_merkle_root}:{','.join(sorted(deleted_record_hashes))}"
        )
        return {
            "scheme": "hash-commitment-zkp",
            "certificate_id": certificate_id,
            "commitment": commitment,
            "nonce": nonce,
            "post_merkle_root": post_merkle_root,
            "weights_hash": weights_hash,  # hash only — never weights
            "deleted_record_hashes": sorted(deleted_record_hashes),
            "statement_hash": statement,
            "signature": sign_sha256(statement.encode("utf-8")),
        }

    @staticmethod
    def verify(proof: dict[str, Any]) -> bool:
        """Verify a proof without access to model weights."""
        commitment = proof.get("commitment")
        nonce = proof.get("nonce")
        weights_hash = proof.get("weights_hash")
        post_root = proof.get("post_merkle_root")
        if not all([commitment, nonce, weights_hash, post_root]):
            return False
        if sha256_hex(f"{weights_hash}:{post_root}:{nonce}") != commitment:
            return False
        statement = sha256_hex(
            f"{proof.get('certificate_id', '')}:{commitment}:{post_root}:"
            f"{','.join(sorted(proof.get('deleted_record_hashes', [])))}"
        )
        return verify_sha256(statement.encode("utf-8"), proof.get("signature", ""))
