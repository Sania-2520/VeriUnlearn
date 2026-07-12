from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.crypto.hashing import sha256_hash
from app.crypto.merkle import MerkleTree, MerkleTreeBuilder
from app.crypto.signing import SigningService
from app.models.unlearning import UnlearningResult


PROOF_FIELDS = {"merkle_root", "signature", "certificate_path", "certificate_hash"}
DB_MANAGED_FIELDS = {"id", "created_at", "updated_at"}
CERTIFICATE_DERIVED_FIELDS = {"certificate_hash", "public_key", "qr_code_base64"}


class ProofVerificationService:
    def __init__(self) -> None:
        self.merkle = MerkleTreeBuilder()
        self.signer = SigningService()

    def build_result_tree(self, result: UnlearningResult) -> MerkleTree:
        return self.merkle.build(self._result_payload(result))

    def verify_result(self, result: UnlearningResult) -> dict[str, Any]:
        errors: list[str] = []

        tree = self.build_result_tree(result)
        merkle_valid = bool(result.merkle_root) and tree.root == result.merkle_root
        if not merkle_valid:
            errors.append("Merkle root mismatch")

        signature_valid = False
        if result.merkle_root and result.signature:
            signature_valid = self.signer.verify(result.merkle_root, result.signature)
        if not signature_valid:
            errors.append("Result signature invalid")

        certificate_valid = False
        certificate_hash_valid = False
        certificate_signature_valid = False
        certificate_errors: list[str] = []

        if result.certificate_path:
            certificate_path = Path(result.certificate_path)
            if certificate_path.exists():
                try:
                    certificate = json.loads(certificate_path.read_text())
                    certificate_valid = self._certificate_matches_result(certificate, result, certificate_errors)
                    certificate_hash_valid = self._verify_certificate_hash(certificate, result)
                    certificate_signature_valid = self._verify_certificate_signature(certificate)
                except Exception as exc:
                    certificate_errors.append(f"Certificate parse failed: {exc}")
            else:
                certificate_errors.append("Certificate file not found")
        else:
            certificate_errors.append("Certificate path missing")

        errors.extend(certificate_errors)

        verified = merkle_valid and signature_valid and certificate_valid and certificate_hash_valid and certificate_signature_valid
        return {
            "result_id": result.id,
            "request_id": result.request_id,
            "verified": verified,
            "merkle_valid": merkle_valid,
            "signature_valid": signature_valid,
            "certificate_valid": certificate_valid,
            "certificate_hash_valid": certificate_hash_valid,
            "certificate_signature_valid": certificate_signature_valid,
            "public_key": self.signer.public_key,
            "errors": errors,
        }

    def _result_payload(self, result: UnlearningResult) -> dict[str, Any]:
        return {
            c.name: getattr(result, c.name)
            for c in result.__table__.columns
            if c.name not in PROOF_FIELDS and c.name not in DB_MANAGED_FIELDS and getattr(result, c.name) is not None
        }

    def _certificate_matches_result(self, certificate: dict[str, Any], result: UnlearningResult, errors: list[str]) -> bool:
        checks = {
            "request_id": certificate.get("request_id") == result.request_id,
            "algorithm": certificate.get("algorithm") == result.algorithm,
            "execution_mode": certificate.get("execution_mode") == result.execution_mode,
            "merkle_root": certificate.get("merkle_root") == result.merkle_root,
            "result_signature": certificate.get("result_signature") == result.signature,
        }
        for key, ok in checks.items():
            if not ok:
                errors.append(f"Certificate field mismatch: {key}")
        return all(checks.values())

    def _verify_certificate_hash(self, certificate: dict[str, Any], result: UnlearningResult | None) -> bool:
        canonical_json = self._certificate_canonical_json(certificate)
        cert_hash = sha256_hash(canonical_json)
        if result is not None:
            return cert_hash == certificate.get("certificate_hash") == result.certificate_hash
        return cert_hash == certificate.get("certificate_hash")

    def _verify_certificate_signature(self, certificate: dict[str, Any], public_key: str | None = None) -> bool:
        signature = certificate.get("digital_signature")
        if not signature:
            return False
        canonical = self._certificate_canonical_json(certificate)
        if public_key:
            return self.signer.verify_with_key(canonical, signature, public_key)
        return self.signer.verify(canonical, signature)

    def _certificate_canonical_json(self, certificate: dict[str, Any]) -> str:
        canonical = dict(certificate)
        canonical["digital_signature"] = None
        for field in CERTIFICATE_DERIVED_FIELDS:
            canonical.pop(field, None)
        return json.dumps(canonical, indent=2, default=str)

    def verify_certificate_file(
        self, certificate_path: str | Path, pinned_public_key: str | None = None
    ) -> dict[str, Any]:
        path = Path(certificate_path)
        if not path.exists():
            return {
                "verified": False,
                "certificate_hash_valid": False,
                "certificate_signature_valid": False,
                "consistent": False,
                "public_key_matched": False,
                "errors": ["Certificate file not found"],
            }

        try:
            certificate = json.loads(path.read_text())
        except Exception as exc:
            return {
                "verified": False,
                "certificate_hash_valid": False,
                "certificate_signature_valid": False,
                "consistent": False,
                "public_key_matched": False,
                "errors": [f"Certificate parse failed: {exc}"],
            }

        certificate_hash_valid = self._verify_certificate_hash(certificate, None)
        embedded_public_key = certificate.get("public_key")
        verify_key = pinned_public_key or embedded_public_key
        certificate_signature_valid = self._verify_certificate_signature(certificate, verify_key)

        consistent = bool(
            certificate.get("merkle_root")
            and certificate.get("result_signature")
            and certificate.get("certificate_id")
            and certificate.get("verification_status") == "VERIFIED"
        )

        public_key_matched = True
        if pinned_public_key:
            public_key_matched = pinned_public_key == embedded_public_key

        errors: list[str] = []
        if not certificate_hash_valid:
            errors.append("Certificate hash mismatch")
        if not certificate_signature_valid:
            errors.append("Certificate signature invalid")
        if pinned_public_key and not public_key_matched:
            errors.append("Pinned public key does not match certificate public key")
        if not consistent:
            errors.append("Certificate missing required proof fields")

        return {
            "verified": certificate_hash_valid and certificate_signature_valid and consistent and public_key_matched,
            "certificate_hash_valid": certificate_hash_valid,
            "certificate_signature_valid": certificate_signature_valid,
            "consistent": consistent,
            "public_key_matched": public_key_matched,
            "public_key": embedded_public_key or self.signer.public_key,
            "certificate_id": certificate.get("certificate_id"),
            "request_id": certificate.get("request_id"),
            "errors": errors,
        }
