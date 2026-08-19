# Phase 3 & 4 — Deliverables

**VeriUnlearn** — Privacy Auditor & Identity Search (Phase 3) and Surgical Machine
Unlearning (Phase 4). Built on the existing Phase 1/2 codebase; no existing
APIs were changed or removed — all new endpoints are additive, and the existing
auth, dataset upload, ingestion (CSV/JSON/JSONL/TXT/PDF), user management and
unlearning pipeline are untouched.

---

## 1. Files created

### Backend
| File | Purpose |
|---|---|
| `backend/app/services/pii_detection.py` | PII detection engine: regex + Luhn + metadata heuristics, categories (email, phone, government_id, financial, credentials, medical, address, dob, identifier, pii) and severity (low/medium/high/critical) per finding. |
| `backend/app/repositories/privacy_repo.py` | Repository for `PrivacyReport`, `SearchHistory` and `DeletionHistory` (list/get/list_searches/list_reports/get_by_request). |
| `backend/app/schemas/privacy.py` | Pydantic schemas: `SearchRequest`, `ScanRequest`, `ScanResponse`, `ExportRequest`. |
| `backend/app/alembic/versions/bd3d39814aa2_initial_schema.py` | Regenerated incremental initial-schema migration (Phase 1/2). |
| `backend/app/alembic/versions/97fe9443fb40_phase3_privacy_auditor_phase4_surgical_.py` | Migration adding Phase 3/4 columns + tables (`privacy_reports`, `identity_index`, `embedding_index`, `search_history`, `deletion_history`) and record identity/chat/source fields. |
| `backend/tests/test_pii_detection.py` | Unit tests for the PII engine (email, Aadhaar/PAN/passport, phone, credentials, Luhn-valid + Luhn-invalid cards, metadata fields, severity ordering, clean text). |
| `backend/tests/test_phase34.py` | Integration tests: PDF ingestion, full scan + structured search + record viewer + report, impact analysis + chat-scoped deletion + deletion history, dataset-scope deletion, search history persistence. |

### Frontend
| File | Purpose |
|---|---|
| `frontend/app/(app)/privacy/report/[id]/page.tsx` | Privacy Report page: severity bar, category chips, findings table with snippet/confidence/shard. |
| `frontend/app/(app)/privacy/records/page.tsx` | Record Viewer: provenance, original content, metadata, PII findings, hashes, embeddings. |
| `frontend/app/(app)/privacy/history/page.tsx` | Search History: replayable list of past identity searches. |
| `frontend/app/(app)/unlearning/page.tsx` | Phase 4 workflow: record/chat/dataset selection → impact analysis → SISA retraining monitor (animated timeline) → before/after comparison → deletion report. |

## 2. Files modified

| File | Change |
|---|---|
| `backend/app/db/models.py` | Added `identity_key`, encrypted identity columns (name/email/phone/aadhaar/pan/passport/dob/address), `sensitivity`, `chat_id`, `source_filename`, `source_timestamp`, `chunk_index`, `embedding_id`, `vector_id`, `content_hash`, `influence_score`, tombstone fields to `DatasetRecord`; new models `PrivacyReport`, `IdentityIndex`, `EmbeddingIndex`, `SearchHistory`, `DeletionHistory`. |
| `backend/app/services/pii.py` | Deterministic identity synthesis extended: full name, email, phone, Aadhaar, PAN, passport, DOB, address; `classify_sensitivity`. |
| `backend/app/services/ingestion.py` | CSV/JSON/JSONL/TXT/PDF ingestion; real identity columns detected from headers; chat_id detection; label inference; stratified shard assignment; source file/page metadata; embedding + identity indexing. |
| `backend/app/services/privacy.py` | `search_identities` (multi-field + structured filters + confidence), `scan_all` (persisted reports), `get_report`, `get_record_detail`, `identity_footprint` (clusters, neurons, influence, sensitivity), `privacy_overview`, `list_history`, `recompute_dataset_roots`. |
| `backend/app/services/unlearning.py` | `resolve_records` scopes (`records`/`chat`/`dataset`), `analyze_impact` (embeddings, vectors, chunks, shards, influence, dependencies, est. retrain time), before/after snapshots, `DeletionHistory` report row, per-dataset duration. |
| `backend/app/api/v1/privacy.py` | `POST /privacy/search`, `POST /privacy/scan`, `GET /privacy/reports`, `GET /privacy/report/{id}`, `GET /privacy/records/{id}`, `GET /privacy/footprint/{key}`, `GET /privacy/history`, `GET /privacy/overview`, `POST /privacy/export` (existing `/search` form preserved). |
| `backend/app/api/v1/unlearning.py` | `POST /unlearning/impact`, `GET /unlearning/history` (existing `/selective`, `/full-reset`, `/requests` untouched). |
| `backend/app/schemas/unlearning.py` | Added `ImpactRequest`, `DeletionHistoryOut` (existing schemas untouched). |
| `backend/app/repositories/__init__.py` | Export `privacy_repo` modules. |
| `backend/app/schemas/__init__.py` | Export new schema modules. |
| `backend/requirements.txt` | Added `pypdf` for PDF text extraction. |
| `frontend/app/(app)/layout.tsx` | Added "Surgical Unlearning" nav item. |
| `frontend/app/(app)/privacy/page.tsx` | Added full-dataset scan button + report link, search history link, structured-filters hint, record viewer link. |
| `.gitignore` | Ignore `backend/models/` weights dir. |
| `README.md` | Phase 3/4 feature + endpoint summary. |
| `backend/alembic/versions/80e4a3fba8a6_initial_schema.py` | Removed (replaced by incremental `bd3d39814aa2` + `97fe9443fb40`). |

## 3. API documentation

All endpoints require `Authorization: Bearer <jwt>`. Base: `http://localhost:8000/api/v1`.

### Phase 3 — Privacy Auditor
| Method | Path | Body / Params | Returns |
|---|---|---|---|
| POST | `/privacy/search` | `?query=` or body `{query?, identity_key?, filters?}` | `{query, filters, match_count, matches[], scanned}` |
| POST | `/privacy/scan` | body `{dataset_id?, identity_key?}` | `{report_id, scanned_records, findings_count, risk_score, counts_by_severity, categories}` |
| GET | `/privacy/reports` | `?limit=` | `{reports[]}` |
| GET | `/privacy/report/{id}` | — | full report incl. `findings[]` |
| GET | `/privacy/records/{id}` | — | record provenance payload |
| GET | `/privacy/footprint/{identity_key}` | — | identity footprint (clusters, neurons, influence, sensitivity, eligibility) |
| GET | `/privacy/history` | `?limit=` | `{history[]}` |
| GET | `/privacy/overview` | — | aggregate overview |
| POST | `/privacy/export` | body `{query?, identity_key?, filters?}` | downloadable JSON |

`filters` keys: `name|full_name`, `email`, `phone`, `aadhaar`, `pan`, `passport`,
`record_id`, `chat_id`, `customer_id`, `employee_id`.

### Phase 4 — Surgical Unlearning
| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/unlearning/impact` | `{identity_key?, record_ids?, chat_id?, dataset_id?, scope: records|chat|dataset}` | impact report (totals + per-dataset details) |
| POST | `/unlearning/selective` | `{identity_key?, record_ids?, chat_id?, dataset_id?, scope, method: retrain|certified|influence}` | `202` + `DeletionRequestOut` |
| POST | `/unlearning/full-reset` | `{identity_key}` | `202` + `DeletionRequestOut` |
| GET | `/unlearning/history` | `?limit=` | `DeletionHistoryOut[]` (before/after snapshots, vectors removed, durations) |
| GET | `/unlearning/requests` / `/{id}` | — | request status (poll for completion) |

## 4. Database migration

Two incremental Alembic migrations, applied on a fresh DB:

```bash
cd backend
../.venv/Scripts/python -m alembic upgrade head
```

1. `bd3d39814aa2` — initial schema (users, datasets, records, models, shards,
   deletion requests, certificates, audit logs).
2. `97fe9443fb40` — Phase 3/4: new record columns + `privacy_reports`,
   `identity_index`, `embedding_index`, `search_history`, `deletion_history`.

Regenerate from scratch:

```bash
rm -f veriunlearn.db
../.venv/Scripts/python -m alembic revision --autogenerate -m "next change"
../.venv/Scripts/python -m alembic upgrade head
../.venv/Scripts/python -m app.seed   # bootstrap Adult Census + admin user
```

## 5. Testing instructions

```bash
cd backend
../.venv/Scripts/python -m pytest tests -q          # 29 tests
cd ../frontend
npm run build                                        # typecheck + production build
```

- `tests/test_pii_detection.py` — PII engine unit tests.
- `tests/test_phase34.py` — Phase 3/4 integration tests (scan, search, impact,
  scoped deletion, history, PDF).
- `tests/test_api.py`, `test_crypto.py`, `test_unlearning_flow.py` — Phase 1/2
  regression (all still green).

## 6. Manual verification checklist

1. `cd backend && ../.venv/Scripts/python -m alembic upgrade head && ../.venv/Scripts/python -m app.seed`
2. `../.venv/Scripts/python -m uvicorn app.main:app --port 8000`
3. Login as `admin@veriunlearn.dev` / `admin12345` (or register a new user).
4. **Privacy Auditor** (`/privacy`): search a seeded name (e.g. `noah`) → results
   show confidence, source, shard, influence, embedding. Click *Scan all datasets*
   → *View report* → severity bar + findings.
5. **Record Viewer** (`/privacy/records?id=…`): text, metadata, hash, embeddings,
   PII findings.
6. **Search History** (`/privacy/history`): past queries listed, re-runnable.
7. **Surgical Unlearning** (`/unlearning`): scope = Records, search + tick
   records → *Impact analysis* (totals, affected shards, est. retrain) →
   *Delete … & unlearn* → animated pipeline → before/after comparison →
   *View deletion certificate*.
8. Re-search the deleted identity → 0 matches; `GET /unlearning/history` shows the
   persisted report with before/after counts and duration.

## 7. Prerequisites before starting Phase 5

- **No blockers.** Phase 5 (cryptographic certificates, Merkle-tree verification,
  blockchain, ZK proofs, attack benchmarking) was already implemented in the
  Phase 1/2 build and remains fully wired; Phase 3/4 only added *extension
  points* on top:
  - `DeletionHistory.certificate_id` / `DeletionHistory.certified_bound` already
    link each deletion report to the issued certificate and its provable bound.
  - `PrivacyReport` rows carry `dataset_id`/`subject` so future compliance
    dashboards can join reports → certificates → audit events.
  - `identity_footprint().deletion_eligible` gates unlearning eligibility on a
    trained model per dataset, the precondition SISA retraining needs.
- Suggested Phase 5 focus if continuing: compliance dashboard wiring
  (reports × certificates × audit), blockchain mode against a live Ethereum
  testnet, and frontend pages for attack benchmarking.
