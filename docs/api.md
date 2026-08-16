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
| POST | `/privacy/search?query=…` | Scan all shards; matches with confidence, source, model, shard, sensitivity, influence, embedding, adapter |
| GET | `/privacy/footprint/{identity_key}` | Full footprint: record ids, embeddings, knowledge clusters, affected neurons, adapters, influence stats |

## Unlearning

| Method | Path | Description |
|---|---|---|
| POST | `/unlearning/selective` | Body `{identity_key?|record_ids?, deletion_type, method}` — method ∈ `retrain` (SISA), `certified` (Newton), `influence` (gradient scrub). Returns `202` + request id; runs in background |
| POST | `/unlearning/full-reset` | `{identity_key}` — complete identity reset across all datasets |
| GET | `/unlearning/requests` | List deletion requests |
| GET | `/unlearning/requests/{id}` | Poll request status + result (roots, certificate id, bound) |

## Certificates

| Method | Path | Description |
|---|---|---|
| GET | `/certificates` | List certificates |
| GET | `/certificates/{id}` | Certificate detail (roots, hashes, signature, zk proof) |
| GET | `/certificates/{id}/download` | Signed certificate JSON |
| GET | `/certificates/{id}/pdf` | Certificate PDF |

## Verification

| Method | Path | Description |
|---|---|---|
| POST | `/verification/verify/{cert_id}` | Re-hash content, verify RSA signature, recompute post-root from live DB, verify audit chain → `{verified, hash_integrity, signature_valid, post_root_matches_current_state, deleted_records_still_tombstoned, audit_chain_verified}` |

## Compliance & Audit

| Method | Path | Description |
|---|---|---|
| GET | `/compliance/overview` | GDPR/DPDP scores + status, risk, request stats, certificate integrity, audit chain state |
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

## Admin (role: `admin`)

| Method | Path | Description |
|---|---|---|
| GET | `/admin/users` | List users |
| PATCH | `/admin/users/{id}/role` | Body `"role"` ∈ `admin|operator|auditor` |

## Error format

```json
{ "error": "not_found", "message": "Record x not found", "details": {} }
```

Status codes: `401` unauthorized, `403` forbidden, `404` not found, `409` conflict, `422` validation,
`503` service unavailable.
