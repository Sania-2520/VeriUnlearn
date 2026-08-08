# ADR-0012: SIMULATED zk-SNARK prototype for verification

- **Status:** Accepted (Prototype, SIMULATED) (2026-05)

## Context

Zero-knowledge proofs let a verifier confirm a deletion happened *without* learning which
samples were deleted or the leaf index — stronger privacy than a plain Merkle proof.
This ADR records the *prototype* decision for the VeriUnlearn v1.0 platform.

## Decision

`ZKProofService` wraps a Keccak-256 Merkle inclusion proof in a Groth16-style envelope
(proving key, verification key, π_A/π_B/π_C proof points) with an Ed25519-signed root.
Routes: `/proof/generate-zksnark`, `/proof/verify-zksnark` (backend: `/verify/zksnark/*`).

> **Honesty note (SIMULATED).** This is a **hash-based simulation**, not a real
> zero-knowledge proof system. It substitutes SHA-256/Keccak hashing and Ed25519
> signatures for real zero-knowledge elliptic-curve arithmetic (Groth16, PLONK,
> circom). The proof *envelope* (proving key, verification key, π_A/π_B/π_C) is
> illustrative and provides **no cryptographic zero-knowledge guarantees** beyond a
> Merkle-inclusion proof bound by a conventional digital signature.

## Consequences

- ✅ Demonstrates the *shape* of a privacy-preserving verification pipeline; good
  research artifact and integration point.
- ✅ Compatible envelope shape for swapping in a real Groth16/PLONK backend later.
- ❌ **Prototype only**: no real trusted setup; proof math is illustrative, not a
  production soundness proof. **Do not claim zero-knowledge guarantees** for the
  shipped implementation.
- ⛔ **Enforced in code**: the simulator refuses to generate proofs when
  `APP_ENV`/`VERIUNLEARN_ENV` is `production`/`prod` unless
  `VERIUNLEARN_ALLOW_SIMULATED_ZK=true` is explicitly set (see
  `packages/ml-engine/verification/zksnark_service.py`).
- ⛔ API responses are tagged `proving_scheme: "SIMULATED"` with an explicit
  disclaimer in both the backend and the ML Engine.
- ❌ Not post-quantum; circuit complexity for large models unresolved (open problem).

## Alternatives considered

- Full Circom/Groth16 (rejected: trusted-setup ceremony + toolchain out of scope for v1).
- Bulletproofs (deferred: smaller proofs but slower verify at scale).
- See [FUTURE_ROADMAP.md](../FUTURE_ROADMAP.md) Phase 11 for production ZKP plan.
