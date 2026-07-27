# VeriUnlearn API Reference

## Base URLs

| Environment | Backend API | ML Engine API |
|-------------|-------------|---------------|
| Local development | `http://localhost:8000` | `http://localhost:8001` |
| Docker | `http://localhost:8000` | `http://localhost:8001` |
| Production | `https://api.veriunlearn.com` | `https://ml.veriunlearn.com` |

All endpoints return JSON. Authenticated endpoints require `Authorization: Bearer <token>` header.

---

## Authentication & Account Management

### `POST /api/v1/auth/register`

Create a new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "full_name": "Jane Smith",
  "organization": "Acme Corp"
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "Jane Smith",
  "role": "user",
  "created_at": "2026-07-27T12:00:00Z"
}
```

### `POST /api/v1/auth/login`

Authenticate with email and password.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900
}
```

### `POST /api/v1/auth/refresh`

Refresh an expired access token.

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_in": 900
}
```

### `POST /api/v1/auth/logout`

Invalidate current session.

**Response (200):**
```json
{ "message": "Logged out successfully" }
```

### `POST /api/v1/auth/mfa/setup`

Enable TOTP MFA.

**Response (200):**
```json
{
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code_url": "otpauth://totp/...",
  "recovery_codes": ["code1", "code2", "code3", "code4", "code5"]
}
```

### `POST /api/v1/auth/mfa/verify`

Verify TOTP code and complete MFA setup.

**Request:**
```json
{
  "totp_code": "123456"
}
```

**Response (200):**
```json
{ "message": "MFA enabled successfully" }
```

### `POST /api/v1/auth/oauth/{provider}`

OAuth 2.0 authentication (Google, GitHub).

**Response (302):** Redirects to OAuth provider.

### `POST /api/v1/auth/api-keys`

Generate a new API key.

**Request:**
```json
{
  "name": "CI/CD Pipeline Key",
  "permissions": ["unlearning:execute", "verify:read"],
  "expires_at": "2027-01-01T00:00:00Z"
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "key": "vu_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "name": "CI/CD Pipeline Key",
  "permissions": ["unlearning:execute", "verify:read"],
  "expires_at": "2027-01-01T00:00:00Z"
}
```
> **Security note**: The full key is returned only once. Store it securely.

### `GET /api/v1/auth/api-keys`
### `DELETE /api/v1/auth/api-keys/{id}`

---

## Deletion Requests & Unlearning

### `POST /api/v1/unlearning/requests`

Submit a data deletion (unlearning) request.

**Request:**
```json
{
  "target_type": "document",
  "target_id": "9a8b7c6d-5e4f-4031-9a2b-1c0d9e8f7a6b",
  "gdpr_article": "17",
  "priority": "high",
  "algorithm": "sisa",
  "reason": "User requested data deletion per GDPR Art. 17"
}
```

**Response (202):**
```json
{
  "request_id": "uuid",
  "status": "pending",
  "estimated_completion_ms": 1250,
  "algorithm_selected": "sisa",
  "checkpoint_id": "uuid",
  "created_at": "2026-07-27T12:00:00Z"
}
```

### `GET /api/v1/unlearning/requests`

List all unlearning requests (paginated).

### `GET /api/v1/unlearning/requests/{id}`

Get request status and results.

**Response (200):**
```json
{
  "request_id": "uuid",
  "status": "completed",
  "target_type": "document",
  "target_id": "...",
  "algorithm_used": "sisa",
  "results": {
    "model_updated": true,
    "utility_retained": 0.94,
    "mia_before": 0.45,
    "mia_after": 0.12,
    "forget_quality": 0.88
  },
  "verification_status": "verified",
  "certificate_id": "uuid",
  "trust_score": 0.92,
  "created_at": "2026-07-27T12:00:00Z",
  "completed_at": "2026-07-27T12:00:05Z"
}
```

### `POST /api/v1/unlearning/requests/{id}/retry`

Retry a failed unlearning request.

### `GET /api/v1/unlearning/jobs`

List unlearning jobs.

### `GET /api/v1/unlearning/jobs/{id}`

### `POST /api/v1/unlearning/jobs/{id}/cancel`

Cancel a running unlearning job.

### `POST /api/v1/unlearning/bulk`

Submit multiple deletion requests at once.

**Request:**
```json
{
  "targets": [
    { "target_type": "document", "target_id": "id1" },
    { "target_type": "conversation", "target_id": "id2" }
  ],
  "algorithm": "hybrid"
}
```

**Response (202):**
```json
{
  "batch_id": "uuid",
  "requests": ["req_id1", "req_id2"],
  "status": "pending"
}
```

---

## Cryptographic Verification & Certificates

### `POST /api/v1/verify/proofs/generate`

Generate a cryptographic proof for a completed unlearning request.

**Request:**
```json
{
  "request_id": "c1d2e3f4-5678-90ab-cdef-1234567890ab"
}
```

**Response (200):**
```json
{
  "proof_id": "uuid",
  "merkle_root": "a1b2c3d4e5f6g7h8...",
  "signature_hex": "ed25519_signature_hex...",
  "certificate_hash": "sha256_hash...",
  "verified": true,
  "trust_score": 0.94,
  "strategies": {
    "hash_verification": { "passed": true, "score": 1.0 },
    "merkle_verification": { "passed": true, "score": 1.0 },
    "influence_verification": { "passed": true, "score": 0.92 },
    "membership_inference": { "passed": true, "score": 0.88 },
    "forget_quality": { "passed": true, "score": 0.91 }
  }
}
```

### `POST /api/v1/verify/proofs/verify`

Re-verify an existing proof.

**Request:**
```json
{
  "proof_id": "d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f90"
}
```

**Response (200):**
```json
{
  "proof_id": "uuid",
  "valid": true,
  "merkle_root": "...",
  "signature_valid": true,
  "verification_method": "api",
  "timestamp": "2026-07-27T12:00:00Z"
}
```

### `POST /api/v1/verify/certificates/generate`

Generate a signed deletion certificate.

**Request:**
```json
{
  "request_id": "uuid"
}
```

**Response (200):**
```json
{
  "certificate_id": "uuid",
  "certificate": {
    "version": "1.0",
    "request_id": "uuid",
    "algorithm_used": "sisa",
    "merkle_root": "...",
    "signature": "ed25519_sig...",
    "public_key": "ed25519_pubkey...",
    "trust_score": 0.94,
    "issued_at": "2026-07-27T12:00:00Z",
    "expires_at": "2027-07-27T12:00:00Z",
    "qr_code": "data:image/png;base64,..."
  }
}
```

### `POST /api/v1/verify/zksnark/generate`

Generate a zk-SNARK proof (prototype).

### `POST /api/v1/verify/zksnark/verify`

Verify a zk-SNARK proof (prototype).

### `GET /api/v1/verify/trust-scores/{request_id}`

Get trust score breakdown for a specific request.

---

## Training & Model Management

### `POST /api/v1/training/lora`

Start LoRA fine-tuning.

**Request:**
```json
{
  "dataset_id": "uuid",
  "base_model": "Qwen/Qwen2.5-1.5B-Instruct",
  "hyperparameters": {
    "lora_r": 16,
    "lora_alpha": 32,
    "lora_dropout": 0.1,
    "learning_rate": 0.0002,
    "num_epochs": 3,
    "batch_size": 4
  }
}
```

**Response (202):**
```json
{
  "job_id": "uuid",
  "status": "queued",
  "position_in_queue": 2
}
```

### `GET /api/v1/training/jobs`

List training jobs.

### `GET /api/v1/training/jobs/{id}`

### `POST /api/v1/training/jobs/{id}/cancel`

### `POST /api/v1/adapters/register`

Register a new LoRA adapter version.

**Request:**
```json
{
  "name": "my-adapter",
  "version": "1.0.0",
  "base_model": "Qwen/Qwen2.5-1.5B-Instruct",
  "metadata": { "description": "Customer support fine-tune v1" }
}
```

**Response (201):**
```json
{
  "adapter_id": "uuid",
  "name": "my-adapter",
  "version": "1.0.0",
  "status": "inactive"
}
```

### `POST /api/v1/adapters/activate`
### `POST /api/v1/adapters/deactivate`
### `POST /api/v1/adapters/{name}/rollback`
### `POST /api/v1/adapters/canary/setup`
### `POST /api/v1/adapters/{name}/canary/promote`
### `GET /api/v1/adapters`
### `GET /api/v1/adapters/{name}/versions`
### `GET /api/v1/adapters/{name}/health`
### `GET /api/v1/adapters/{name}/latency`

---

## Inference & Chat

### `POST /api/v1/inference/generate`

Generate text with the active model.

**Request:**
```json
{
  "prompt": "What is machine unlearning?",
  "max_tokens": 512,
  "temperature": 0.7,
  "adapter_name": "my-adapter"
}
```

**Response (200):**
```json
{
  "id": "uuid",
  "text": "Machine unlearning is...",
  "tokens_used": 128,
  "latency_ms": 345,
  "model": "Qwen/Qwen2.5-1.5B-Instruct",
  "adapter": "my-adapter"
}
```

### `POST /api/v1/inference/generate/stream`

Streaming generation (Server-Sent Events).

### `POST /api/v1/inference/batch`

Batch inference for multiple prompts.

### `POST /api/v1/chat`

Conversational AI with RAG.

**Request:**
```json
{
  "message": "What documents do I have about GDPR?",
  "conversation_id": "uuid"
}
```

### `GET /api/v1/chat`
### `GET /api/v1/chat/{conversation_id}`

---

## Governance & Compliance

### `POST /api/v1/governance/consents`

Grant consent.

**Request:**
```json
{
  "user_id": "uuid",
  "purpose": "data_processing",
  "scope": "model_training",
  "expires_at": "2027-07-27T00:00:00Z"
}
```

### `POST /api/v1/governance/consents/{id}/withdraw`

Withdraw consent (triggers unlearning cascade).

### `GET /api/v1/governance/consents`

### `GET /api/v1/governance/policies`

List policy templates.

### `POST /api/v1/governance/policies`

Evaluate dataset/model against policies.

### `GET /api/v1/governance/approvals`
### `POST /api/v1/governance/approvals`
### `POST /api/v1/governance/approvals/{id}/approve`
### `POST /api/v1/governance/approvals/{id}/reject`

### `GET /api/v1/governance/risk`

Get risk assessment and governance score.

**Response (200):**
```json
{
  "overall_score": 0.87,
  "privacy_risk": 0.12,
  "compliance_risk": 0.08,
  "exposure_risk": 0.15,
  "recommendations": ["Review data retention policies", "Update consent forms"]
}
```

### `GET /api/v1/governance/lineage?target_id={id}`

Full data lineage trace.

### `POST /api/v1/compliance/webhooks`

Register a compliance webhook.

**Request:**
```json
{
  "url": "https://audit.example.com/webhook",
  "events": ["unlearning.completed", "consent.withdrawn", "policy.violation"],
  "secret": "shared_hmac_secret"
}
```

### `GET /api/v1/compliance/webhooks`
### `DELETE /api/v1/compliance/webhooks/{id}`

### `POST /api/v1/gdpr/export`

Request GDPR data export.

### `DELETE /api/v1/gdpr/account`

Request account deletion.

---

## Document & RAG Management

### `POST /api/v1/documents`

Upload a document for RAG indexing.

**Request:** Multipart form data with file.

### `GET /api/v1/documents`
### `GET /api/v1/documents/{id}`
### `DELETE /api/v1/documents/{id}`

### `POST /api/v1/documents/search`

Semantic search over indexed documents.

---

## Benchmarks & Research

### `POST /api/v1/benchmarks/run`

Run a benchmark suite.

**Request:**
```json
{
  "dataset": "sentiment_synthetic",
  "algorithms": ["sisa", "influence_function", "certified_removal", "hybrid"],
  "trials": 5,
  "seed": 42
}
```

**Response (202):**
```json
{
  "benchmark_id": "uuid",
  "status": "running",
  "estimated_completion_s": 120
}
```

### `GET /api/v1/benchmarks/summary`
### `GET /api/v1/benchmarks/results`
### `GET /api/v1/benchmarks/config`
### `GET /api/v1/benchmarks/leaderboard`

Get algorithm ranking across all benchmark runs.

### `GET /api/v1/benchmarks/results?format=csv`
### `GET /api/v1/benchmarks/results?format=json`

Export benchmark results.

---

## Monitoring & Health

### `GET /health`

Backend health check.

**Response (200):**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 86400,
  "database": "connected",
  "redis": "connected",
  "qdrant": "connected",
  "minio": "connected",
  "ml_engine": "connected"
}
```

### `GET /metrics`

Prometheus metrics endpoint (IP-restricted in production).

### `GET /api/v1/usage`

Get current usage quotas and limits.

**Response (200):**
```json
{
  "api_requests_today": 1450,
  "unlearning_requests_today": 23,
  "storage_used_mb": 456,
  "api_limit_per_second": 30
}
```

### `GET /api/v1/admin/dashboard`

Admin dashboard statistics.

---

## Audit

### `GET /api/v1/audit`

Query audit log (paginated, filterable).

**Query parameters:** `event_type`, `actor_id`, `resource_id`, `from_date`, `to_date`, `page`, `page_size`

### `POST /api/v1/audit/chain/anchor`

Manually trigger blockchain anchoring.

### `GET /api/v1/audit/chain/verify`

Verify integrity of the audit hash chain.

**Response (200):**
```json
{
  "chain_integrity": true,
  "total_entries": 1042,
  "first_entry_hash": "...",
  "last_entry_hash": "...",
  "last_anchored_at": "2026-07-27T06:00:00Z"
}
```

---

## ML Engine Internal Endpoints

The ML Engine runs on port 8001 and is consumed internally by the backend. Direct access is not required for normal operation.

### Unlearning
| Method | Path | Description |
|--------|------|-------------|
| POST | `/unlearn` | Execute unlearning via hybrid controller |
| POST | `/unlearn/e2e` | End-to-end unlearning pipeline |
| GET | `/unlearn/e2e/history` | E2E deletion history |
| GET | `/unlearn/e2e/stats` | E2E pipeline statistics |

### Proof & Verification
| Method | Path | Description |
|--------|------|-------------|
| POST | `/proof/generate` | Generate Merkle proof |
| POST | `/proof/verify` | Verify signature |
| POST | `/proof/generate-zksnark` | Generate zk-SNARK proof (prototype) |
| POST | `/proof/verify-zksnark` | Verify zk-SNARK proof (prototype) |
| POST | `/certificate` | Generate deletion certificate |

### Adapter Lifecycle
| Method | Path |
|--------|------|
| POST | `/adapters/register`, `/activate`, `/deactivate`, `/mark-failed` |
| POST | `/adapters/{name}/rollback`, `/canary/setup`, `/{name}/canary/promote` |
| GET | `/adapters`, `/adapters/{name}/versions`, `/{name}/active` |
| GET | `/adapters/{name}/routing`, `/{name}/latency`, `/{name}/health` |
| POST | `/adapters/metrics` |

### Training
| Method | Path |
|--------|------|
| POST | `/train/lora`, `/train/checkpoints/{id}/load` |
| GET | `/train/checkpoints` |

### Explainability
| Method | Path |
|--------|------|
| POST | `/explain/samples`, `/explain/features`, `/explain/compare` |
| POST | `/explain/privacy-heatmap`, `/explain/drift` |
| GET | `/explain/methods` |

### Continual Learning
| Method | Path |
|--------|------|
| GET | `/continual/stats`, `/continual/tasks`, `/continual/tasks/{id}` |
| POST | `/continual/tasks`, `/continual/samples`, `/continual/ewc/estimate` |
| GET | `/continual/ewc/state`, `/continual/replay/stats` |
| POST | `/continual/replay/sample`, `/continual/drift/record` |
| GET | `/continual/drift/alerts`, `/continual/drift/state` |

### Inference
| Method | Path |
|--------|------|
| POST | `/inference/generate`, `/inference/generate/stream`, `/inference/batch` |
| POST | `/inference/adapters/load`, `/inference/adapters/unload` |
| GET | `/inference/adapters`, `/inference/metrics`, `/inference/health` |

### System
| Method | Path |
|--------|------|
| GET | `/health`, `/controller/health`, `/controller/metrics` |
| GET | `/mlflow/experiment-stats`, `/mlflow/runs` |

---

## Error Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 400 | Bad Request | Missing required field, invalid data format, validation failure |
| 401 | Unauthorized | Missing token, expired token, invalid signature |
| 403 | Forbidden | Insufficient RBAC role, resource not owned by user |
| 404 | Not Found | Resource ID doesn't exist, endpoint path incorrect |
| 409 | Conflict | Duplicate registration, resource in invalid state for operation |
| 422 | Unprocessable Entity | ML Engine validation failure, incompatible algorithm/dataset |
| 429 | Too Many Requests | Rate limit exceeded — check `Retry-After` header |
| 500 | Internal Server Error | Unhandled exception — check server logs |
| 502 | Bad Gateway | ML Engine unreachable, upstream service failure |
| 503 | Service Unavailable | Backpressure, maintenance mode, resource exhaustion |

### Error Response Format

```json
{
  "error": {
    "code": 400,
    "type": "validation_error",
    "message": "Invalid target_type. Must be one of: document, conversation, user_data",
    "details": [
      {
        "field": "target_type",
        "message": "Value 'invalid_type' is not permitted",
        "constraint": "enum"
      }
    ],
    "request_id": "uuid",
    "timestamp": "2026-07-27T12:00:00Z"
  }
}
```

---

## Rate Limiting Headers

Every response includes rate limit information:

```
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 27
X-RateLimit-Reset: 1682345678
Retry-After: 3
```

---

## Related Documents

- [Architecture Guide](ARCHITECTURE_GUIDE.md) — System architecture and data flow
- [Machine Unlearning Guide](machine-unlearning-guide.md) — Algorithm pipeline details
- [Verification Guide](verification-guide.md) — Cryptographic proof flow
- [Benchmark Guide](BENCHMARK_GUIDE.md) — Benchmark endpoints usage
- [Security Guide](SECURITY_GUIDE.md) — Authentication and authorization details
