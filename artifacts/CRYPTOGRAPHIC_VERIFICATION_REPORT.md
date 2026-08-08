# Cryptographic Verification Report

**VeriUnlearn v1.0 Release Candidate** — 2026-08-08

## Executive conclusion

**There is no production zk-SNARK implementation in this repository, and none
was fabricated.** Per the mission's Task 4 guidance, the shipped scheme is an
**honest, clearly-labelled prototype** and all public materials have been
corrected so no zero-knowledge guarantee is falsely claimed.

## What is real

- **Ed25519 signing / verification** (`ml-engine` signatures module) — real
  cryptographic signatures with real public keys, fully exercised by tests.
- **Merkle tree construction and inclusion proofs** — real hash-based
  structures (`ml-engine/verification`), used for deletion proofs.
- **Hash-anchored deletion certificates** — certificates embed a merkle root /
  content hash and are stored and retrieved via the verification service.
- **End-to-end verification pipeline** — proof generation, storage, verification
  records, audit trail, and certificate issuance all run real code paths.

## What is SIMULATED (and now labelled as such)

- **zk-SNARK "proofs"** (`ZKProofService`) are **hash-based simulations**, not
  cryptographic zero-knowledge proofs. No Groth16/Plonk circuit, no trusted
  setup, no proving key, no real verifier exists — and implementing a true
  production zk-SNARK is a major research/engineering effort explicitly out of
  scope for this block (requires external pairing-curve tooling and trusted
  setup ceremonies).

## Corrections applied (Task 4 honesty requirement)

| Artifact | Before | After |
|---|---|---|
| `docs/adr/0012-zero-knowledge-proofs.md` | Claimed the "zero-knowledge property holds" | States clearly the shipped scheme is SIMULATED (hash-based) and does not provide cryptographic ZK guarantees |
| `README.md` | Unqualified zk-SNARK claim | Qualified: SIMULATED, not a real zk proof |
| `STATUS.md` | Misleading "proved ZK" line | Corrected to reflect the simulated scheme |
| `docs/research/05-paper-3-cryptographic-verification.md` | Read as a proposed-system outline | Added an implementation-status banner distinguishing the shipped prototype from the paper's future zk integration |
| API response | — | `generate_zksnark_proof` returns `"proving_scheme": "SIMULATED"` plus an explicit disclaimer field |

## What every public API now represents accurately

- `POST /proofs/generate-zksnark` → returns a SIMULATED proof with an explicit
  disclaimer; callers cannot mistake it for a real ZK proof.
- `POST /proofs/generate` → real Ed25519-signed merkle proof.
- `POST /proofs/{id}/verify` → real signature verification, augmented with
  optional ML Engine confirmation.
- `GET /certificates/{hash}` → real stored-certificate lookup with fallback
  generation, or 404.

## Validation

- `tests/test_zksnark.py` — 19 tests pass, all asserting the simulated nature
  (no cryptographic claims).
- Backend verification service + repository + API tests pass (including the new
  `get_certificate` lookup tests).
