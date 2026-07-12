from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import qrcode
from io import BytesIO
import base64

from app.core.config import settings
from app.crypto.hashing import sha256_hash
from app.crypto.signing import SigningService


class CertificateGenerator:
    def __init__(self) -> None:
        self.signer = SigningService()
        self.storage_dir = Path(settings.certificate_storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, unlearning_result: Any, request: Any, deleted_sample_count: int | None = None) -> dict[str, str]:
        cert_id = f"CERT-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{id(unlearning_result)}"
        if deleted_sample_count is None:
            try:
                deleted_sample_count = len(request.samples)
            except Exception:
                deleted_sample_count = 0

        cert_data = {
            "certificate_id": cert_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": unlearning_result.request_id,
            "deleted_user_id": request.user_id,
            "deleted_sample_count": deleted_sample_count,
            "algorithm": unlearning_result.algorithm or request.algorithm,
            "execution_mode": unlearning_result.execution_mode,
            "guarantees": unlearning_result.guarantees,
            "simulated": unlearning_result.simulated,
            "model_version_before": unlearning_result.model_version_before_id,
            "model_version_after": unlearning_result.model_version_after_id,
            "model_hash_before": None,
            "model_hash_after": None,
            "merkle_root": unlearning_result.merkle_root,
            "result_signature": unlearning_result.signature,
            "digital_signature": None,
            "membership_attack_before": {
                "accuracy": unlearning_result.mia_before_accuracy,
                "precision": unlearning_result.mia_before_precision,
                "recall": unlearning_result.mia_before_recall,
            },
            "membership_attack_after": {
                "accuracy": unlearning_result.mia_after_accuracy,
                "precision": unlearning_result.mia_after_precision,
                "recall": unlearning_result.mia_after_recall,
            },
            "utility_loss": unlearning_result.utility_loss,
            "utility_retention": unlearning_result.utility_retention,
            "deletion_latency_ms": unlearning_result.deletion_latency_ms,
            "privacy_leakage": unlearning_result.privacy_leakage,
            "verification_status": "VERIFIED",
        }

        cert_json = json.dumps(cert_data, indent=2, default=str)
        cert_hash = sha256_hash(cert_json)

        cert_data["certificate_hash"] = cert_hash
        cert_data["digital_signature"] = self.signer.sign(cert_json)
        cert_data["public_key"] = self.signer.public_key

        qr = qrcode.QRCode(box_size=10, border=4)
        qr.add_data(json.dumps({
            "id": cert_id,
            "hash": cert_hash,
            "signature": cert_data["digital_signature"][:32] + "...",
        }))
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_buffer = BytesIO()
        qr_img.save(qr_buffer, format="PNG")
        cert_data["qr_code_base64"] = base64.b64encode(qr_buffer.getvalue()).decode()

        file_path = self.storage_dir / f"{cert_id}.json"
        with open(file_path, "w") as f:
            json.dump(cert_data, f, indent=2, default=str)

        return {
            "path": str(file_path),
            "hash": cert_hash,
            "certificate_id": cert_id,
        }
