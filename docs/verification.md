# Independent Verification

VeriUnlearn issues a cryptographic deletion certificate for every unlearning
request. The certificate is **independently verifiable**: any auditor can check
its integrity and authenticity without trusting the issuing server.

## What is proven

Each certificate carries:

- `merkle_root` — SHA-256 Merkle root over the unlearning result's content
  (all non-null result columns except DB-managed and proof fields).
- `result_signature` — an Ed25519 signature over the Merkle root, produced by
  the server's signing key.
- `certificate_hash` — SHA-256 hash of the canonical certificate body.
- `digital_signature` — Ed25519 signature over the canonical certificate body.
- `public_key` — the Ed25519 public key (hex) used to verify the signature.

Verification confirms three things:

1. **Integrity** — `certificate_hash` matches the recomputed hash of the
   certificate body.
2. **Authenticity** — `digital_signature` validates against the embedded
   `public_key`.
3. **Consistency** — the certificate contains the required proof fields
   (`merkle_root`, `result_signature`, `certificate_id`).

## Option A — Verify via the running server

```
GET /api/v1/unlearning/results/{request_id}/verify
```

Returns `verified: true` plus `merkle_valid`, `signature_valid`,
`certificate_valid`, `certificate_hash_valid`, and
`certificate_signature_valid`.

Download the raw certificate file with:

```
GET /api/v1/unlearning/results/{request_id}/certificate
```

## Option B — Verify a certificate file offline (no server)

Any auditor can verify a certificate file independently using the bundled CLI.
It needs only the certificate JSON — no database, no running server, no local
signing key (the public key is embedded in the certificate).

```bash
cd backend
python scripts/verify_certificate.py path/to/CERT-....json
```

Exit code is `0` when the certificate verifies, `1` otherwise. Example output:

```
VeriUnlearn Certificate Verification
----------------------------------------
Certificate ID : CERT-20260101-120000-140500
Request ID     : 7
Public key     : 8e4a...c1
Hash valid     : True
Signature valid: True
Consistent     : True
VERIFIED       : True
```

## How the canonical hash/signature are computed

Both the server (at issuance) and the verifier (at audit time) compute the
canonical certificate body identically:

- Start from the full certificate object.
- Set `digital_signature` to `null`.
- Drop the derived fields `certificate_hash`, `public_key`, `qr_code_base64`.
- Serialize with `json.dumps(body, indent=2, default=str)`.

The SHA-256 of that string is `certificate_hash`; its Ed25519 signature is
`digital_signature`. Recomputing and comparing is what makes verification
deterministic and reproducible by any third party.

## Trust model

The Ed25519 key pair lives at `<adapter_storage_dir>/signing_key` (override with
the `SIGNING_KEY_PATH` env var to point at a KMS-backed or mounted key) and is
created automatically on first use.

By default the CLI verifies the `digital_signature` against the **public key
embedded inside the certificate**. For stronger assurance, pin a trusted public
key out-of-band and verify against it instead:

```bash
# Export the server's trusted public key (distribute this securely)
python scripts/verify_certificate.py --export-public-key

# Verify a certificate against the pinned key (not the embedded one)
python scripts/verify_certificate.py cert.json --public-key <trusted-hex-key>
```

When `--public-key` is supplied, verification additionally checks that the
embedded key matches your pinned key, so a tampered or substituted key is
rejected.
