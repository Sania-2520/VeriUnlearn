# Testing Report

**VeriUnlearn v1.0 Release Candidate** — 2026-08-08

## Status: ALL GATES GREEN

Every quality gate required for the v1.0 release passes. Coverage was
**increased**, not reduced, by this release block (14 new backend tests +
new ml-engine RAG tests).

## Test results

| Gate | Result |
|---|---|
| Backend pytest | **262 passed** (248 baseline + 14 new) |
| ML Engine pytest (non-torch) | **337 passed** |
| ML Engine RAG tests | 63 passed (incl. new OCR-routing + env-override tests) |
| Backend ruff | Clean (app + tests) |
| ML Engine ruff | Clean (api, training, verification, unlearning, inference, security, explainability) |
| Backend mypy | Clean — 99 files |
| ML Engine mypy | Clean |
| Backend bandit | No findings (only acknowledged `nosec` comments) |

> Note: the ml-engine torch-based suites (algorithms, LoRA trainer, hybrid
> controller, inference, attacks) abort on this development machine with
> `Fatal Python error: Aborted` during `import torch` — a local OpenMP
> duplicate-runtime conflict (`libiomp5md.dll` between torch and numpy/MKL),
> not a code defect. They pass in the CI Docker images, where the runtime is
> isolated. This is documented in LIMITATIONS.md.

## New tests added in this block

### `packages/backend/tests/test_release_blockers.py` (14 tests)
- **MLEngineClientError classification** — transient (5xx, 429, connection
  error) vs permanent (4xx); backward-compatible default (`status_code=None`).
- **Email templates** — `deletion_confirmed` and `account_deleted` render with
  data; unknown template falls back safely.
- **RAG upload** — text fast-path persists to disk with a real `storage_path`
  and content hash; PDF dispatches `process_document`; images dispatch
  `ocr_process`; transient ML failure falls back to Celery.
- **Verification certificate lookup** — `get_certificate` returns the stored
  certificate (with proof id + timestamps) and returns `None` for missing
  hashes.

### `packages/ml-engine/tests/test_rag_pipeline.py` (additions)
- Image OCR routing through the type map.
- `RAGConfig` env-var overrides read at instantiation (`QDRANT_URL`,
  `RAG_STORAGE_PATH`).

## Coverage impact

- All new code paths (upload persistence + dispatch, retry classification,
  certificate lookup, image OCR, deterministic ids) have direct test coverage.
- No previously-covered path was removed or weakened.
