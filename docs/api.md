# VeriUnlearn API Reference

Base URL: `http://localhost:8000/api/v1` · Interactive docs: `/docs` (OpenAPI) · Health: `GET /health`

All endpoints except `auth/*` require `Authorization: Bearer <token>`.

## Auth

| Method | Path | Description |
|---|---|---|
| POST | `/auth/register` | `{email, full_name, password}` → `{access_token, user}` |
| POST | `/auth/login` | `{email, password}` → `{access_token, user}` |
| GET | `/auth/me` | Current user |
| POST | `/auth/logout` | Record logout audit event |

## Datasets

| Method | Path | Description |
|---|---|---|
| POST | `/datasets/upload` | Multipart `file` (csv/json/jsonl/txt) + `shard_count` form field |
| POST | `/datasets/bootstrap/adult` | Download + ingest Adult Census (`limit`, `shard_count` query params) |
| GET | `/datasets` | List datasets |
| GET | `/datasets/{id}` | Dataset detail |
| DELETE | `/datasets/{id}` | Delete dataset (cascade) |

## Models & Inference

| Method | Path | Description |
|---|---|---|
| POST | `/models/train?dataset_id=…` | Train a SISA sharded model + score record influence |
| GET | `/models` | List models |
| GET | `/models/{id}` | Model detail (metrics, weights hash, version) |
| GET | `/models/{id}/shards` | Per-shard state (weights hash, accuracy, record version) |
| POST | `/models/{id}/predict` | `{features: {…}}` → soft-voted prediction |
| DELETE | `/models/{id}` | Delete model |

## Privacy Auditor

| Method | Path | Description |
|---|---|---|
| POST | `/privacy/search?query=…` | Scan all shards; matches with confidence, source, model, shard, sensitivity, influence, embedding, adapter. Optional JSON body adds structured filters (name, email, phone, aadhaar, pan, record_id, chat_id, …) |
| POST | `/privacy/scan` | `{dataset_id?, identity_key?}` — full PII scan → `{report_id, scanned_records, findings_count, risk_score, counts_by_severity, categories}` (audit-logged) |
| GET | `/privacy/overview` | Aggregate privacy stats (records, embeddings, footprints, risk) |
| GET | `/privacy/reports?limit=` | Persisted scan reports (list) |
| GET | `/privacy/report/{id}` | Full scan report with findings + severity counts |
| GET | `/privacy/records/{id}` | Record viewer: text, metadata, file, dataset, chunk/embedding/hash |
| GET | `/privacy/footprint/{identity_key}` | Full footprint: record ids, embeddings, knowledge clusters, affected neurons, adapters, influence stats |
| GET | `/privacy/history?limit=` | Current user's search history |
| POST | `/privacy/export` | `{query?, identity_key?, filters?}` → downloadable JSON of matches |

## Unlearning

| Method | Path | Description |
|---|---|---|
| POST | `/unlearning/impact` | `{scope: records|chat|dataset, identity_key?/record_ids?/chat_id?/dataset_id?}` → impact report (affected shards, embeddings, est. retrain time) — run before deleting |
| POST | `/unlearning/selective` | Body `{identity_key?|record_ids?, deletion_type, method}` — method ∈ `retrain` (SISA), `certified` (Newton), `influence` (gradient scrub). Returns `202` + request id; runs in background |
| POST | `/unlearning/full-reset` | `{identity_key}` — complete identity reset across all datasets |
| GET | `/unlearning/requests` | List deletion requests |
| GET | `/unlearning/requests/{id}` | Poll request status + result (roots, certificate id, bound) |
| GET | `/unlearning/history?limit=` | Persisted deletion reports (scope, method, before/after, vectors removed, certificate id) |

## Certificates

| Method | Path | Description |
|---|---|---|
| GET | `/certificates` | List certificates |
| GET | `/certificates/{id}` | Certificate detail (roots, hashes, signature, zk proof) |
| GET | `/certificates/{id}/download` | Signed certificate JSON |
| GET | `/certificates/{id}/pdf` | Certificate PDF |

## Verification (Phase 5)

| Method | Path | Description |
|---|---|---|
| POST | `/verification/run` | Full deletion-verification job (8 checks: records, embeddings, vectors, versions, Merkle, signature, audit, consistency) → persisted report `{report_id, verdict, checks_passed, checks_total, duration_seconds}` |
| GET | `/verification/{report_id}` | Full report: per-check results + Merkle tree snapshot |
| GET | `/verification/history` | List verification reports |
| GET | `/verification/certificate/{cert_id}` | Independent certificate verification (hash, signature, roots, audit) |
| POST | `/verification/verify/{cert_id}` | Legacy equivalent of the above → `{verified, hash_integrity, signature_valid, post_root_matches_current_state, deleted_records_still_tombstoned, audit_chain_verified}` |
| POST | `/verification/verify-proof` | Verify a Merkle membership proof `{root, leaf, proof[]}` → `{verified, reason}` |
| POST | `/verification/proofs` | Issue an immutable cryptographic proof (nonce + RSA signature) |
| GET | `/verification/proofs/{proof_id}` | Fetch a stored proof |
| GET | `/verification/audit` | Audit-chain status + recent events |
| GET | `/verification/public-key` | Server RSA public key (external verification) |
| GET | `/verification/download/json/{report_id}` | Verification report JSON |
| GET | `/verification/download/pdf/{report_id}` | Verification report PDF |

See [`docs/phase5-deliverables.md`](phase5-deliverables.md) for the full Phase 5 specification.

## Compliance & Audit (Phase 7)

| Method | Path | Description |
|---|---|---|
| GET | `/compliance/overview` | GDPR/DPDP scores + status, risk, request stats, certificate integrity, audit chain state |
| POST | `/compliance/report` | Capture + persist a GDPR/DPDP compliance snapshot `{report_id, gdpr_score, dpdp_score, risk_score, …}` |
| GET | `/compliance/reports?limit=` | Persisted compliance snapshots (trending) |
| GET | `/compliance/export?format=csv|json` | Download compliance history |
| GET | `/audit` | Hash-chained audit events |
| GET | `/audit/verify` | Recompute the chain; returns `{verified, event_count, broken_event_id}` |

## Attack Lab

| Method | Path | Description |
|---|---|---|
| POST | `/attacks/membership/{model_id}` | MIA AUC + attack success on train vs holdout |
| POST | `/attacks/membership/after-unlearning` | `{model_id, deleted_record_ids}` — membership leak on deleted records |
| POST | `/attacks/backdoor/{model_id}?poison_fraction=0.2` | Trigger fires before/after unlearning poisoned rows |
| POST | `/attacks/inversion/{model_id}?target_label=1` | Gradient-ascent reconstruction error |

## Benchmark

| Method | Path | Description |
|---|---|---|
| POST | `/benchmarks/run?dataset_id=…&n_delete=50` | original vs `sisa_retrain` vs `certified_removal` vs `influence_scrub`: accuracy, F1, deletion time, utility loss, certified bound |

## Research — Benchmark (Phase 6)

| Method | Path | Description |
|---|---|---|
| POST | `/benchmark/run` | Non-destructive 6-method benchmark (original, full retrain, SISA, influence, certified, VeriUnlearn) with utility/cost/privacy metrics; persists rows, optionally under `experiment_id` |
| GET | `/benchmark/results` | Persisted benchmark rows (optional `method` filter, `limit`) |
| GET | `/benchmark/history` | Distinct benchmark runs grouped by dataset/experiment |
| GET | `/benchmark/export?format=csv|json|xlsx` | Download benchmark results (IEEE-ready tables) |

## Research — Attacks (Phase 6)

| Method | Path | Description |
|---|---|---|
| POST | `/attack/mia` | Membership-inference report: AUC, accuracy/precision/recall/F1, privacy leakage, membership confidence; optional `deleted_record_ids` for multi-stage comparison |
| POST | `/attack/inversion` | Gradient-ascent inversion: reconstruction error, information leakage, similarity score |
| POST | `/attack/extraction` | `{model_id, deleted_record_ids}` — recovery of embeddings/vectors/metadata/served text + extraction success rate |
| POST | `/attack/poisoning` | `attack_type` ∈ `backdoor|label_flip|gradient` — persistence ratio, detection rate, removal success, robustness, residual influence |
| GET | `/attack/results` | Persisted attack results (optional `model_id` filter) |

## Research — Metrics (Phase 6)

| Method | Path | Description |
|---|---|---|
| GET | `/metrics/system` | Live + persisted CPU/RAM/disk samples (time-series) |
| GET | `/metrics/privacy` | Research metrics matrix (forget quality, privacy gain, retention, accuracy drop, utility loss, deletion efficiency, verification overhead) + compliance readiness + LaTeX table |
| GET | `/metrics/security` | Aggregated attack outcomes: MIA mean AUC/leakage, poisoning persistence, extraction rate |

## Research — Experiments (Phase 6)

| Method | Path | Description |
|---|---|---|
| POST | `/experiments` | Create versioned experiment (name, seed, parameters, dataset) + environment snapshot |
| GET | `/experiments` | List experiments |
| GET | `/experiments/{id}` | Experiment detail + version history + benchmark rows |
| POST | `/experiments/{id}/version` | Branch a new version (fresh parameters/name) |
| POST | `/experiments/compare` | `{experiment_ids: [≥2]}` — side-by-side result comparison |

See [`docs/phase6-deliverables.md`](phase6-deliverables.md) for the full Phase 6 specification.

## RBAC (Phase 7)

Five platform roles — `admin`, `researcher`, `auditor`, `operator`, `viewer` — each mapped to a set of scoped `resource:action` permissions (single source of truth: `backend/app/core/rbac.py`, mirrored in the `roles`/`permissions` tables). Enforced server-side via `require_permission()` (403 on insufficient role), inherited by API-key-authenticated calls, and mirrored by frontend page guards.

## Admin (Phase 7, role: `admin`)

| Method | Path | Description |
|---|---|---|
| GET | `/admin/overview` | Platform counts (users, datasets, models, certificates, deletion requests, API keys, verification reports) |
| GET | `/admin/users` | List users (id, email, full name, role, active, permissions) |
| POST | `/admin/users` | `{email, full_name, password (min 8), role}` → created user (audited) |
| PATCH | `/admin/users/{id}/role` | Body `"role"` ∈ 5-role matrix (audited) |
| PATCH | `/admin/users/{id}/active` | Body `true/false` — activate/deactivate (audited) |
| GET | `/admin/roles` | RBAC role/permission matrix |
| GET | `/admin/deployments` | Deployment history |
| POST | `/admin/deployments` | `{version, environment, status, commit_sha?, artifact?}` — record a deployment (audited) |

## API Keys (Phase 7)

Programmatic access via `X-API-Key: <key>` (alternative to bearer tokens; authenticates as the key's owning user, so RBAC applies). Keys are stored hashed; the raw key is returned exactly once at issuance.

| Method | Path | Description |
|---|---|---|
| POST | `/api-keys` | `{name, scopes?, quota_per_minute? (default 60), expires_in_days? (default 90)}` → `{api_key: {key, id, key_prefix, …}}` |
| GET | `/api-keys` | Own keys with usage logs (last 50 requests: timestamp, path, status) |
| POST | `/api-keys/{id}/revoke` | Revoke (further calls return 401) |

Per-key sliding-window quota is enforced by middleware; platform-wide rate limiting via `RATE_LIMIT_DEFAULT` (slowapi).

## Notifications (Phase 7)

| Method | Path | Description |
|---|---|---|
| GET | `/notifications` | `{notifications, unread}` inbox (events: deletion.completed, verification.completed, certificate.ready, experiment.finished, system.error) |
| GET | `/notifications/unread-count` | `{unread}` badge count |
| POST | `/notifications/read-all` | Mark all read |
| POST | `/notifications/{id}/read` | Mark one read |

Channels: in-app (persisted) + email via provider abstraction (`EMAIL_PROVIDER=null|smtp`), with delivery attempts/retry state surfaced per notification.

## Monitoring (Phase 7)

| Method | Path | Description |
|---|---|---|
| GET | `/monitoring/system` | `{snapshot, history}` — CPU/RAM/disk, dependency health (database, redis, qdrant, vector store), worker queue (in_flight/total), API latency/error rate/uptime + persisted `system_metrics` history |
| GET | `/metrics` | Prometheus text format (`veriunlearn_http_requests_total`, latency histogram, system gauges); optional bearer `METRICS_TOKEN` |

## Analytics (Phase 7)

| Method | Path | Description |
|---|---|---|
| GET | `/analytics/overview` | Deletion/verification/certificate/compliance aggregates |
| GET | `/analytics/deletion-trends?days=` | Time-series of deletion requests (1–365) |
| GET | `/analytics/privacy-trends?days=` | Privacy scan/report trend (1–730) |
| GET | `/analytics/usage?days=` | Platform usage stats (1–365) |
| GET | `/analytics/dataset-growth?days=` | Dataset growth series (1–730) |
| GET | `/analytics/certificates` | Certificate totals/validity stats |
| GET | `/analytics/export?format=csv|json` | Analytics bundle download (overview + deletion trends + certificate stats) |

## Error format

```json
{ "error": "not_found", "message": "Record x not found", "details": {} }
```

Status codes: `401` unauthorized, `403` forbidden, `404` not found, `409` conflict, `422` validation,
`503` service unavailable.
