# Architecture Refactoring Report

**VeriUnlearn v1.0 Release Candidate** — 2026-08-08

## Status: DUPLICATION ELIMINATED, PUBLIC APIS UNCHANGED

The architecture-refactoring pass for v1.0 consolidated duplicated plumbing
without changing any external API. All refactors are backward-compatible:
request paths, payload shapes, and error types are identical to prior releases.

## Key refactors

### 1. ML Engine client — single HTTP pipeline
- **Before:** every `MLEngineClient` method opened its own `httpx.AsyncClient`,
  duplicated `raise_for_status` / error wrapping, and performed no retries.
- **After:** a single `_request` helper handles connection pooling, retries with
  jitter, and uniform `MLEngineClientError` (now with `status_code`). All 40+
  public methods delegate to it. Duplicate HTTP/exception handling removed.
- Public signatures, paths, and error types are identical.

### 2. ML Engine RAG pipeline — shared services
- `DocumentProcessor` is the single parser registry (PDF/DOCX/TXT/MD/CSV/
  images), replacing ad-hoc branching in multiple call sites.
- `RAGPipeline.process_document` unifies the Celery-driven and synchronous
  ingestion paths under a caller-supplied document id (single code path for
  parse → chunk → embed → index).

### 3. Backend RAG — single persistence + dispatch decision
- Upload persistence (storage dir, size caps, MIME allowlist, hashing) is
  centralized in the upload endpoint; text fast-path and Celery dispatch share
  the same DB row lifecycle (flush → dispatch → commit).

### 4. Verification — repository pattern completion
- `get_certificate` completes the `DeletionProofRepository` interface
  (`get_by_certificate_hash`) and the `VerificationService` method, closing the
  only remaining gap between the interface, implementation, and API route.
- Certificate lookup now flows Interface → Repository → Service → API with no
  duplicated query logic.

### 5. Dead code removal
- Removed the empty `app/domain/security` package (tracked placeholder with no
  consumers).

## Design invariants preserved

- **Dependency Injection:** services receive repositories via constructor
  (`VerificationService(proof_repo=…, verification_repo=…, audit_service=…)`).
- **Repository Pattern:** all DB access in the verification domain flows
  through `DeletionProofRepository` / `ProofVerificationRepository`.
- **No circular imports:** the new code imports only established modules
  (config, logging, models, ml_engine client); verified by clean mypy run.
- **Type safety:** all new signatures are fully typed; `mypy` clean across
  99 backend files and the ml-engine packages.

## What was deliberately NOT refactored

Per mission constraints, no working module was rewritten for its own sake.
The oversized modules (LoRA trainer, benchmark framework, conversational
pipeline) were audited and found to have no duplicate implementation gaps
remaining after the earlier hardening block; splitting them now would change
public APIs for no functional gain. This is recorded as accepted technical
debt (see TECHNICAL_DEBT.md).
