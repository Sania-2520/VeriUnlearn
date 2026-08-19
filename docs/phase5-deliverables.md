# Phase 5 — Verifiable Machine Unlearning: Deliverables

**VeriUnlearn** — cryptographic evidence that unlearning operations are valid and
complete. Built on the Phase 1–4 codebase; no existing APIs, auth, frontend
layout, or deletion flows were modified. New functionality is strictly additive.

---

## 1. New files

| File | Purpose |
|---|---|
| `backend/app/services/merkle_engine.py` | Merkle Tree Engine: incremental insert/delete, batch deletion, partial (subset) verification, pre/post root comparison, serialisable tree snapshots for visualisation. |
| `backend/app/services/proofs.py` | Cryptographic Proof Generator: immutable proof objects (id, subject, pre/post roots, leaf hashes, nonce, timestamp, content hash, RSA signature) + independent verification (replay protection via nonce, timestamp sanity). |
| `backend/app/services/verification_engine.py` | Deletion Verification Engine: 8-check full verification job (records, embeddings, vectors, versions, Merkle, signature, audit, consistency) → persisted `VerificationReport`. |
| `backend/app/repositories/verification_repo.py` | Repositories for `VerificationReport` and `CryptoProof`. |
| `backend/app/schemas/verification.py` | Pydantic schemas for the verification API. |
| `backend/alembic/versions/203c60186717_phase5_verifiable_unlearning.py` | Migration: `verification_reports` + `crypto_proofs` tables. |
| `backend/tests/test_phase5.py` | 10 tests: Merkle engine, proofs, verification engine, verification API. |
| `frontend/app/(app)/verification/page.tsx` | Verification dashboard: run jobs, history, stats, pipeline flow, external public key. |
| `frontend/app/(app)/verification/[id]/page.tsx` | Report detail: check breakdown, Merkle tree visualisation, hash comparison, JSON/PDF download. |
| `docs/phase5-deliverables.md` | This document. |

## 2. Modified files

| File | Change |
|---|---|
| `backend/app/services/crypto.py` | **Bug fix** in `MerkleTree.proof()`: odd-count levels pair the final node with *itself*; the proof now appends a self-pair entry so verification reconstructs the correct parent. Previously proofs for leaves on odd levels failed to verify. |
| `backend/app/db/models.py` | Added `VerificationReport` and `CryptoProof` models (Phase 5 section). |
| `backend/app/repositories/__init__.py` | Export the new repositories. |
| `backend/app/schemas/__init__.py` | Export the new verification schemas. |
| `backend/app/api/v1/verification.py` | Extended from a single `POST /verify/{id}` into the full Phase 5 API surface (legacy endpoint kept). |
| `frontend/app/(app)/layout.tsx` | Added "Verification" nav item. |

## 3. Database migration

```bash
cd backend
../.venv/Scripts/python -m alembic upgrade head   # adds 203c60186717
```

New tables (additive, only what Phase 5 requires — the hash-chained audit trail
already lives in `audit_events`, certificates in `certificates`):
- `verification_reports` — one row per verification job: verdict, per-check
  results, Merkle snapshot, duration.
- `crypto_proofs` — persisted immutable proof objects (nonce, roots, leaf
  hashes, content hash, RSA signature, verification status).

## 4. API documentation

All endpoints require `Authorization: Bearer <jwt>` under `/api/v1`.

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/verification/run` | `{certificate_id?, deletion_request_id?, dataset_id?}` | `{report_id, verdict, checks_passed, checks_total, duration_seconds}` |
| GET | `/verification/{report_id}` | — | full report (8 checks + Merkle snapshot) |
| GET | `/verification/history` | `?limit=` | list of reports |
| GET | `/verification/certificate/{certificate_id}` | — | independent certificate verification (hash, signature, roots, audit) |
| POST | `/verification/verify/{certificate_id}` | — | legacy equivalent of the above |
| POST | `/verification/verify-proof` | `{root, leaf, proof[]}` | Merkle membership verification |
| POST | `/verification/proofs` | `{subject_id, subject_type, claim, pre/post roots, leaf_hashes}` | issued signed proof |
| GET | `/verification/proofs/{proof_id}` | — | stored proof |
| GET | `/verification/audit` | `?limit=` | audit-chain status + recent events |
| GET | `/verification/public-key` | — | RSA public key PEM for external verification |
| GET | `/verification/download/json/{report_id}` | — | report JSON download |
| GET | `/verification/download/pdf/{report_id}` | — | report PDF download |

## 5. Certificate format specification

A deletion certificate (issued by `CertificateService`, unchanged from
Phases 1–2) is a signed JSON document:

```json
{
  "certificate_id": "uuid",
  "subject_user_id": "identity key",
  "deletion_type": "records|chat|dataset|identity_reset",
  "deleted_record_count": 8,
  "dataset_id": "uuid", "model_id": "uuid", "model_version": 2,
  "shard_ids": [0, 2],
  "pre_merkle_root": "sha256…",
  "post_merkle_root": "sha256…",
  "deleted_record_hashes": ["sha256…", "…"],
  "method": "retrain|certified|influence",
  "certified_bound": 1.4e3,
  "timestamp": "ISO-8601 UTC",
  "issuer": "VeriUnlearn",
  "content_hash": "sha256(canonical body)",
  "signature": "base64 RSA-PKCS1v15-SHA256 over canonical body bytes"
}
```

Available as JSON and PDF via `/certificates/{id}/download` and
`/certificates/{id}/pdf`. Verification re-derives the canonical body, recomputes
the hash, checks the RSA signature, and compares the recomputed post-root
against the current dataset state.

## 6. Verification workflow

1. A deletion request completes → certificate minted (pre/post Merkle roots,
   record hashes, signature) → ZK commitment → audit events appended.
2. `POST /verification/run` executes 8 independent checks:
   `records` (all claimed hashes tombstoned) · `embeddings` (no live embeddings
   on tombstones, index rows deleted) · `vectors` (store no longer holds them) ·
   `versions` (model/shard versions match certificate) · `merkle` (recomputed
   post-root == certificate; deleted leaves provably absent) · `signature`
   (hash + RSA) · `audit` (hash chain intact) · `consistency` (DB ↔ index ↔
   store agree).
3. Verdict `valid` only when all 8 pass; the report is persisted and linked to
   the certificate, and the certificate's status is updated.
4. Third parties verify externally: fetch `/verification/public-key`, check the
   certificate signature, recompute the Merkle root from dataset state.

## 7. Merkle Tree implementation explanation

- **Leaf** = SHA-256 of `{record_id, content_hash, state: active|deleted}`.
  Deleting a record changes its leaf to a tombstone, so the post-root provably
  excludes the data while covering the dataset namespace.
- **Tree**: leaves are sorted + deduplicated, then hashed pairwise up to a
  single root (`H(left ‖ right)`, odd nodes duplicated).
- **Incremental updates**: `insert`/`delete`/`delete_many` return *new*
  immutable trees, so pre/post roots are cheap to compare (`compare` classifies
  the transition: unchanged / reduced / expanded / mixed).
- **Partial verification**: `proof_for_leaves` emits the root + the excluded
  hashes; `verify_subset` recomputes `root(leaves ∪ excluded)` and compares —
  an auditor can prove N records are gone without the whole dataset.
- **Membership proofs**: `proof(leaf)` emits the sibling path; `verify`
  recomputes the root from leaf + siblings. (Odd-level self-pairing was a real
  bug fixed in this phase.)
- **Snapshot**: full level structure serialised for the dashboard.

## 8. Digital signature implementation explanation

- **Key management**: 2048-bit RSA keypair generated once and persisted under
  `KEYS_DIR` (`server_private.pem` / `server_public.pem`), configurable via
  `RSA_KEY_BITS` and path settings — production can mount pre-provisioned keys.
- **Signing**: RSA-PKCS1v15 with SHA-256 over the canonical (sorted, compact)
  JSON body bytes.
- **External verification**: the public key is exposed at
  `/verification/public-key` so any party can verify certificates and proofs
  offline.
- **Proofs** additionally bind a fresh 24-byte nonce (replay protection) and an
  ISO timestamp; verification rejects missing nonces and future timestamps.

## 9. Testing instructions

```bash
cd backend
../.venv/Scripts/python -m pytest tests -q      # 39 tests (29 prior + 10 Phase 5)
cd ../frontend
npm run build                                    # typecheck + production build
```

Phase 5 tests: `test_phase5.py` — Merkle incremental/batch/partial/membership/
snapshot, proof issue/verify/tamper, full verification engine (8/8 valid),
report persistence, all API endpoints (run, get, certificate verify, legacy
POST verify, verify-proof valid+invalid, proofs CRUD, history, audit, public
key, JSON/PDF downloads).

## 10. Manual verification checklist

1. `cd backend && python -m alembic upgrade head && python -m app.seed`
2. `python -m uvicorn app.main:app --port 8000`
3. Login (`admin@veriunlearn.dev` / `admin12345`), open **Verification** page.
4. Run a deletion from Privacy Auditor / Surgical Unlearning (mints a
   certificate).
5. In **Verification**, select the certificate → *Run verification* → expect
   **VALID, 8/8 checks**.
6. Open the report: check breakdown, Merkle tree visualisation, download
   JSON/PDF.
7. Open the certificate detail → *Verify certificate* → passes.
8. Fetch the public key (Verification page) and confirm the PEM downloads.
9. `GET /verification/audit` → chain intact.

## 11. Known limitations

- **In-memory vector store is process-local**: with `VECTOR_STORE_BACKEND=memory`
  a freshly restarted server reports 0 vectors, so the *consistency* check
  treats the store as "must not exceed DB counts" rather than requiring
  equality. With Qdrant (shared) the check is strict.
- **`merkle_nodes` table not materialised**: tree levels are recomputed from
  record state and stored as a snapshot in each verification report. For very
  large datasets a persisted node cache (Phase 6) would cut recompute cost.
- **Merkle recompute is O(n log n)** per verification job; fine at demo scale
  (8k records ≈ 3s), optimisable with cached roots per dataset version.
- **Proof timestamps are server-issued** (no external TSA / RFC 3161); a Phase 6
  option is to anchor timestamps to the blockchain ledger.
- **Certificates sign body bytes, not the content-hash string** — consistent
  everywhere, but external verifiers must replicate the canonical body exactly.

## 12. Extension points for Phase 6 (Security Evaluation & Benchmarking)

- `VerificationReport.checks` is a stable, machine-readable per-check contract —
  the benchmark suite can score methods (retrain / certified / influence) by
  *which* verification checks pass after deletion, e.g. "certified removal
  passes all 8; influence scrub may fail the Merkle check on partial scrubs".
- `VerificationService.run()` accepts `certificate_id | deletion_request_id |
  dataset_id` — benchmark harness can drive batch verification across many
  deletions and record timings (`duration_seconds`) per method.
- `CryptoProof` rows keyed by `subject_id` let attack-evaluation scripts attach
  proofs to each benchmark run and verify them after the fact.
- `audit_chain_check` and `ProofService.verify` are pure functions reusable in
  security-test assertions (tamper an event/proof → assert failure).
- The `merkle_snapshot` JSON in each report enables visual before/after root
  comparison charts (Recharts) for the benchmark dashboard.
