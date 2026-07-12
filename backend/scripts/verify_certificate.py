"""Standalone, offline verifier for VeriUnlearn deletion certificates.

This tool allows an external auditor to independently verify a certificate
file WITHOUT access to the running server or database. It checks:

  1. certificate_hash  - the embedded SHA-256 hash matches the certificate body
  2. digital_signature - the Ed25519 signature is valid
  3. consistency       - the certificate carries the required proof fields

Trust model:
  By default the signature is verified against the PUBLIC KEY EMBEDDED in the
  certificate. For stronger assurance, pin a trusted public key with
  --public-key <hex> (or distribute a known-keys file). When pinned, the
  signature must validate against YOUR key, not the one in the file.

Usage:
    python scripts/verify_certificate.py <certificate.json>
    python scripts/verify_certificate.py <certificate.json> --public-key <hex>
    python scripts/verify_certificate.py --export-public-key

Exit code is 0 when the certificate verifies, 1 otherwise.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.proof_verification_service import ProofVerificationService  # noqa: E402


def main(argv: list[str]) -> int:
    args = argv[1:]
    export_key = False
    pinned_key: str | None = None
    cert_path: str | None = None

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--export-public-key":
            export_key = True
        elif arg == "--public-key":
            i += 1
            pinned_key = args[i]
        elif arg.startswith("--public-key="):
            pinned_key = arg.split("=", 1)[1]
        elif arg.startswith("-"):
            print(f"Unknown option: {arg}")
            return 2
        else:
            cert_path = arg
        i += 1

    verifier = ProofVerificationService()

    if export_key:
        print(verifier.signer.public_key)
        return 0

    if not cert_path:
        print("Usage: python scripts/verify_certificate.py <certificate.json> [--public-key <hex>]")
        return 2

    report = verifier.verify_certificate_file(cert_path, pinned_public_key=pinned_key)

    print("VeriUnlearn Certificate Verification")
    print("-" * 40)
    print(f"Certificate ID : {report.get('certificate_id')}")
    print(f"Request ID     : {report.get('request_id')}")
    print(f"Public key     : {report.get('public_key')}")
    if pinned_key:
        print(f"Pinned key     : {pinned_key}")
        print(f"Key matched    : {report.get('public_key_matched')}")
    print(f"Hash valid     : {report.get('certificate_hash_valid')}")
    print(f"Signature valid: {report.get('certificate_signature_valid')}")
    print(f"Consistent     : {report.get('consistent')}")
    print(f"VERIFIED       : {report.get('verified')}")
    if report.get("errors"):
        print("Errors:")
        for error in report["errors"]:
            print(f"  - {error}")

    return 0 if report.get("verified") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
