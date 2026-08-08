# Remaining Technical Debt

**VeriUnlearn v1.0 Release Candidate** — 2026-08-08

This report lists what remains after the v1.0 release blockers. None of these
are release-blocking or critical; each is a conscious, documented trade-off.

## Functional / capability limits (not defects)

| Area | Debt | Why accepted |
|---|---|---|
| Zero-knowledge proofs | Shipped scheme is SIMULATED (hash-based); real zk-SNARK (Groth16/Plonk) not implemented | Requires a major research/tooling effort (pairing curves, trusted setup); the honest prototype is fully labelled — see CRYPTOGRAPHIC_VERIFICATION_REPORT.md |
| PDF OCR | Depends on the `tesseract` system binary in the ml-engine image; graceful degradation to PyPDF2 text extraction | Documented; the OCR extras are declared in requirements |
| Embedding fallback | Random-vector embeddings when sentence-transformers unavailable | Explicitly labelled dev fallback, never presented as real |
| Vector store fallback | In-memory store when Qdrant unreachable | Documented dev behaviour; production must run Qdrant |

## Process-level debt (non-critical)

| Area | Debt | Notes |
|---|---|---|
| Torch suites on local Windows | `import torch` aborts due to a local OpenMP duplicate-runtime conflict (`libiomp5md.dll`) | Environment issue, not a code defect; suites pass in CI Docker images |
| Module size | LoRA trainer, benchmark framework, conversational pipeline remain large modules | Audited: no duplicate-implementation gaps remain; splitting would change public APIs for no functional gain |
| `asyncio.run` in `training/benchmarks.py` | Benchmark driver bridges the hybrid controller synchronously | Runs under `to_thread` from the API router; intentional and documented |

## Hygiene (trivial)

- A few `nosec` comments acknowledge intentional non-cryptographic randomness
  (backoff jitter, dev embedding fallback) and dev-default secrets that are
  rejected at startup in production.

## Recommendation

None of the above blocks the v1.0 release candidate. The first table's items
are feature-level decisions that should be revisited only as roadmap work
(e.g., a real zk-SNARK integration via an external prover service), not as
release fixes.
