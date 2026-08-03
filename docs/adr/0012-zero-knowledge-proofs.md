# ADR-0012: Groth16-style zk-SNARK prototype for verification

- **Status:** Accepted (Prototype) (2026-05)

## Context

Zero-knowledge proofs let a verifier confirm a deletion happened *without* learning which
samples were deleted or the leaf index — stronger privacy than a plain Merkle proof.

## Decision

`ZKProofService` wraps a Keccak-256 Merkle inclusion proof in a Groth16-style envelope
(proving key, verification key, π_A/π_B/π_C proof points) with an Ed25519-signed root.
Routes: `/proof/generate-zksnark`, `/proof/verify-zksnark` (backend: `/verify/zksnark/*`).

The zero-knowledge property holds: verifier learns leaf + root but not leaf index / siblings.

## Consequences

- ✅ Demonstrates privacy-preserving verification; good research artifact.
- ✅ Compatible envelope shape for swapping in a real Groth16/PLONK backend later.
- ❌ **Prototype only**: no real trusted setup; proof math is illustrative, not a
  production soundness proof.
- ⛔ **Enforced in code**: the simulator refuses to generate proofs when
  `APP_ENV`/`VERIUNLEARN_ENV` is `production`/`prod` unless
  `VERIUNLEARN_ALLOW_SIMULATED_ZK=true` is explicitly set (see
  `packages/ml-engine/verification/zksnark_service.py`).
- ❌ Not post-quantum; circuit complexity for large models unresolved (open problem).

## Alternatives considered

- Full Circom/Groth16 (rejected: trusted-setup ceremony + toolchain out of scope for v1).
- Bulletproofs (deferred: smaller proofs but slower verify at scale).
- See [FUTURE_ROADMAP.md](../FUTURE_ROADMAP.md) Phase 11 for production ZKP plan.
