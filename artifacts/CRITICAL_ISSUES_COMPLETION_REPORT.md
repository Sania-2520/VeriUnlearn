# Critical Issues Completion Report

**VeriUnlearn v1.0 Release Candidate** — 2026-08-08

This report documents the final critical engineering blockers that were
eliminated to qualify the repository as a v1.0 Release Candidate. Every item
below was a genuine defect, placeholder, or misleading artifact; each has been
resolved with production-quality implementations and test coverage.

## 1. RAG upload never persisted binary documents

**Before:** `POST /api/v1/rag/documents/upload` decoded every upload as UTF-8
text. PDFs, DOCX files, and images produced `""`, leaving documents stuck in a
failed/empty state — the Upload → OCR → Parse → Chunk → Embed → Retrieve chain
was broken for the exact formats that need it most.

**After:**
- Uploads are persisted to `settings.rag_storage_dir/<uuid>/<basename>` with
  size caps and a MIME-type allowlist. The path is traversal-safe: the
  directory is a random UUID and the filename is `os.path.basename`-sanitized.
- Text-like files (txt/md/csv/json/html) are ingested synchronously through
  `ingest_document` so they are immediately searchable; on transient ML Engine
  failure they fall back to the Celery pipeline.
- Binary documents dispatch `process_document` (PDF/DOCX/…) or `ocr_process`
  (images) via Celery, which read the persisted file and drive the real
  parsing → chunking → embedding → vector-store pipeline in the ML Engine.
- Docker: a shared `rag-data` volume at `/data/rag` is mounted by backend,
  worker, and ml-engine containers with aligned `RAG_STORAGE_DIR` /
  `RAG_STORAGE_PATH` env vars, so persisted uploads are readable everywhere.

## 2. Missing Celery retry / progress semantics

**Before:** RAG Celery tasks had no retry policy and only coarse status flags.

**After:**
- `MLEngineClientError` now carries an optional `status_code` with an
  `is_transient` property (None/408/425/429/5xx transient; other 4xx permanent).
- `process_document`, `generate_embeddings`, and `ocr_process` are bound tasks
  with `max_retries=3`, exponential backoff with a 60s cap, and **transient-only
  retries** — permanent 4xx failures are never retried.
- Tasks publish `PROGRESS` states and persist the retry status in the DB row
  (`processing` while retrying, `failed` with `error_message` after exhaustion),
  giving callers accurate progress tracking and failure recovery.

## 3. Missing email templates

**Before:** `EmailTemplate.DELETION_CONFIRMED` and `ACCOUNT_DELETED` constants
existed but `_render_template` fell through to "No template found".

**After:** Both templates are fully implemented as production HTML with inline
styles and rendered data (name, proof id). `send_deletion_confirmation` is
wired to the template.

## 4. Dead placeholder: empty `domain/security` package

**Before:** An empty `app/domain/security/__init__.py` existed as a tracked
placeholder with no consumers.

**After:** Removed from the repository (no imports referenced it). Security
assessment functionality lives in the real `app/api/v1/security.py` + models.

## 5. Non-deterministic `hash()` in request ids

**Before:** MIA/privacy router endpoints derived ids/seeds from the builtin
`hash()` function, which is salted per-process in Python 3 — non-reproducible
across runs and workers.

**After:** Replaced with `hashlib.sha256`-based deterministic ids, making
request ids reproducible and consistent across restarts.

## 6. `get_certificate` was not implemented

**Before:** `VerificationService.get_certificate` could not look up stored
certificates (no repository method existed), forcing generation on every call.

**After:** Added `get_by_certificate_hash` to `DeletionProofRepository` and a
real `get_certificate` service method returning the stored certificate,
proof id, request id, merkle root, and issuance/expiry timestamps. The API
route falls back to ML Engine generation only when no stored certificate
matches, and 404s when neither exists.

## 7. Misleading zero-knowledge claims

**Before:** ADR-0012 claimed the "zero-knowledge property holds" for a
hash-based simulated scheme; README/STATUS made unqualified zk-SNARK claims.

**After:** All public materials now clearly label the scheme as
**SIMULATED** (hash-based) with explicit disclaimers that no cryptographic
zero-knowledge guarantees are provided, and the research paper carries an
implementation-status banner. This fulfills the Task 4 "honest prototype"
requirement: no false claims remain.

## Verification

- Backend: **262 tests pass** (248 baseline + 14 new release-blocker tests).
- ML Engine: **337 non-torch tests pass** (RAG, zk, API integration, etc.).
- `ruff check` clean on both packages; `mypy` clean (99 backend files, ml-engine
  packages); `bandit` reports no issues beyond benign `nosec` acknowledgements.
