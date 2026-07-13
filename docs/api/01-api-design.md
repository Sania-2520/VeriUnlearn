# VeriUnlearn — API Design

## Version 1.0.0 — Enterprise API Contracts

---

## 1. API Design Principles

- **RESTful** for CRUD, **SSE** for streaming, **WebSocket** for real-time
- **OpenAPI 3.1** specification, auto-generated via FastAPI
- **Versioned** via URL prefix `/api/v1/`
- **Consistent** error format, pagination, filtering
- **Secure** by default (JWT, rate limiting, input validation)
- **Idempotent** mutations where possible
- **CORS** configured per tenant domain

---

## 2. API Contract Specification

### 2.1 Standard Response Envelope

```json
{
  "status": "success" | "error",
  "data": { ... },
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable message",
    "details": { ... }
  },
  "meta": {
    "request_id": "req_abc123",
    "timestamp": "2026-01-01T00:00:00Z",
    "version": "1.0.0"
  }
}
```

### 2.2 Pagination

```json
{
  "data": [...],
  "meta": {
    "page": 1,
    "page_size": 25,
    "total": 100,
    "total_pages": 4,
    "has_next": true,
    "has_previous": false
  }
}
```

Query parameters: `?page=1&page_size=25&sort=-created_at`

### 2.3 Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| VALIDATION_ERROR | 422 | Request validation failed |
| UNAUTHORIZED | 401 | Invalid or expired credentials |
| FORBIDDEN | 403 | Insufficient permissions |
| NOT_FOUND | 404 | Resource not found |
| RATE_LIMITED | 429 | Too many requests |
| CONFLICT | 409 | Resource conflict |
| INTERNAL_ERROR | 500 | Server error |
| SERVICE_UNAVAILABLE | 503 | Service temporarily unavailable |
| UNLEARNING_IN_PROGRESS | 409 | Unlearning already in progress |

---

## 3. Authentication API

### POST /api/v1/auth/register
```
Request:
{
  "email": "user@example.com",
  "password": "securePassword123!",
  "full_name": "John Doe",
  "tenant_slug": "acme-corp"
}

Response 201:
{
  "user": { ... },
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "expires_in": 900
}
```

### POST /api/v1/auth/login
```
Request:
{
  "email": "user@example.com",
  "password": "securePassword123!"
}

Response 200:
{
  "user": { ... },
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "expires_in": 900
}
```

### POST /api/v1/auth/refresh
```
Request:
{
  "refresh_token": "eyJ..."
}

Response 200:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "expires_in": 900
}
```

### POST /api/v1/auth/logout
```
Headers: Authorization: Bearer <token>
Request:
{
  "refresh_token": "eyJ...",
  "all_sessions": false
}

Response 200: { "message": "Logged out successfully" }
```

### GET /api/v1/auth/oauth/{provider}
```
Redirect to OAuth provider (Google/GitHub)
Response 302: Location: provider's OAuth URL
```

### GET /api/v1/auth/oauth/{provider}/callback
```
Query: ?code=...&state=...
Response 200: { user, access_token, refresh_token }
```

### POST /api/v1/auth/verify-email
```
Request:
{
  "token": "verify_token_abc"
}

Response 200: { "message": "Email verified" }
```

### POST /api/v1/auth/forgot-password
```
Request:
{
  "email": "user@example.com"
}

Response 200: { "message": "Reset email sent" }
```

### POST /api/v1/auth/reset-password
```
Request:
{
  "token": "reset_token_abc",
  "password": "newSecurePassword123!"
}

Response 200: { "message": "Password reset successful" }
```

---

## 4. User API

### GET /api/v1/users/me
```
Response 200:
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "avatar_url": "https://...",
  "role": "member",
  "is_email_verified": true,
  "preferences": {
    "theme": "dark",
    "language": "en",
    "notifications": true
  },
  "created_at": "2026-01-01T00:00:00Z"
}
```

### PATCH /api/v1/users/me
```
Request:
{
  "full_name": "John Updated",
  "preferences": { "theme": "light" }
}

Response 200: { "user": { ... } }
```

### GET /api/v1/users/me/sessions
```
Response 200: { "data": [ { "id", "device_name", "last_active", "current" } ] }
```

### DELETE /api/v1/users/me/sessions/{session_id}
```
Response 200: { "message": "Session revoked" }
```

---

## 5. Chat API

### GET /api/v1/chat/sessions
```
Query: ?page=1&page_size=25&folder_id=uuid&pinned=true&search=keyword
Response 200:
{
  "data": [
    {
      "id": "uuid",
      "title": "Chat title",
      "folder_id": "uuid",
      "is_pinned": false,
      "message_count": 12,
      "model": "gpt-4",
      "last_activity_at": "2026-01-01T00:00:00Z",
      "created_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

### POST /api/v1/chat/sessions
```
Request:
{
  "title": "New Chat",
  "folder_id": null,
  "ai_provider_id": "uuid",
  "model": "gpt-4",
  "system_prompt": "You are a helpful assistant.",
  "temperature": 0.7,
  "max_tokens": 4096
}

Response 201: { "session": { ... } }
```

### GET /api/v1/chat/sessions/{session_id}
```
Response 200: { "session": { ... }, "messages": [...] }
```

### PATCH /api/v1/chat/sessions/{session_id}
```
Request:
{
  "title": "Updated title",
  "is_pinned": true,
  "folder_id": "uuid"
}

Response 200: { "session": { ... } }
```

### DELETE /api/v1/chat/sessions/{session_id}
```
This triggers the unlearning pipeline.
Response 202:
{
  "message": "Deletion initiated",
  "unlearning_request_id": "uuid",
  "estimated_completion": "2026-01-01T00:05:00Z"
}
```

### POST /api/v1/chat/sessions/{session_id}/messages
```
Request:
{
  "content": "Hello, how are you?",
  "parent_id": null
}

Response 200 (SSE stream):
event: token
data: {"token": "Hello", "index": 0}

event: token
data: {"token": "! ", "index": 1}

event: done
data: {"message_id": "uuid", "usage": {"input_tokens": 10, "output_tokens": 50}}

event: error
data: {"error": "Provider error", "code": "PROVIDER_ERROR"}
```

### POST /api/v1/chat/sessions/{session_id}/messages/{message_id}/regenerate
```
Response 200: SSE stream (same as above)
```

### POST /api/v1/chat/sessions/{session_id}/messages/{message_id}/feedback
```
Request:
{
  "feedback": "like" | "dislike"
}

Response 200: { "message": "Feedback recorded" }
```

### GET /api/v1/chat/sessions/{session_id}/export
```
Query: ?format=markdown|json|pdf
Response 200: File download
```

### POST /api/v1/chat/sessions/import
```
Request: multipart/form-data with file
Response 201: { "session": { ... } }
```

---

## 6. Folders API

### GET /api/v1/chat/folders
```
Response 200: { "data": [ { "id", "name", "parent_id", "sort_order", "chat_count" } ] }
```

### POST /api/v1/chat/folders
```
Request: { "name": "Work", "parent_id": null }
Response 201: { "folder": { ... } }
```

### PATCH /api/v1/chat/folders/{folder_id}
```
Request: { "name": "Updated", "sort_order": 1 }
Response 200: { "folder": { ... } }
```

### DELETE /api/v1/chat/folders/{folder_id}
```
Response 200: { "message": "Folder deleted" }
```

---

## 7. AI Providers API

### GET /api/v1/providers
```
Response 200:
{
  "data": [
    {
      "id": "uuid",
      "name": "OpenAI",
      "provider_type": "openai",
      "models": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
      "is_active": true,
      "priority": 1
    }
  ]
}
```

### POST /api/v1/providers
```
Request:
{
  "name": "OpenAI",
  "provider_type": "openai",
  "api_key": "sk-...",
  "models": ["gpt-4", "gpt-4-turbo"],
  "config": { "organization_id": "org-..." }
}

Response 201: { "provider": { ... } }
```

### POST /api/v1/providers/{provider_id}/test
```
Response 200:
{
  "success": true,
  "latency_ms": 350,
  "models_available": ["gpt-4", "gpt-4-turbo"]
}
```

---

## 8. RAG API

### POST /api/v1/rag/documents/upload
```
Request: multipart/form-data
  - file: (binary)
  - metadata: { "tags": ["legal", "contract"] }

Response 202:
{
  "document_id": "uuid",
  "filename": "contract.pdf",
  "status": "processing",
  "estimated_chunks": 45
}
```

### GET /api/v1/rag/documents
```
Query: ?page=1&page_size=25&status=indexed&file_type=pdf
Response 200: { "data": [ { "id", "filename", "status", "chunk_count", "created_at" } ] }
```

### GET /api/v1/rag/documents/{document_id}
```
Response 200:
{
  "id": "uuid",
  "filename": "contract.pdf",
  "status": "indexed",
  "chunks": 45,
  "metadata": { ... },
  "created_at": "..."
}
```

### DELETE /api/v1/rag/documents/{document_id}
```
Response 202: { "message": "Deletion initiated", "unlearning_request_id": "uuid" }
```

### POST /api/v1/rag/search
```
Request:
{
  "query": "What are the GDPR requirements?",
  "top_k": 5,
  "filters": { "document_id": "uuid" },
  "hybrid": true
}

Response 200:
{
  "results": [
    {
      "chunk_id": "uuid",
      "document_id": "uuid",
      "content": "...",
      "score": 0.95,
      "metadata": { "page": 5, "heading": "Chapter 3" }
    }
  ]
}
```

---

## 9. Memory API

### GET /api/v1/memory
```
Query: ?type=user&category=fact&page=1&page_size=50
Response 200: { "data": [ { "id", "type", "category", "content", "importance", "created_at" } ] }
```

### POST /api/v1/memory
```
Request:
{
  "type": "persistent",
  "category": "fact",
  "content": { "key": "name", "value": "John" },
  "importance": 0.8
}

Response 201: { "memory": { ... } }
```

### DELETE /api/v1/memory/{memory_id}
```
Response 200: { "message": "Memory deleted" }
```

### DELETE /api/v1/memory/clear
```
Request:
{
  "types": ["session", "conversation", "persistent"]
}

Response 202: { "message": "Memory clear initiated" }
```

### PATCH /api/v1/memory/config
```
Request:
{
  "persistent_memory_enabled": true,
  "retention_days": 90,
  "max_entries": 1000
}

Response 200: { "config": { ... } }
```

---

## 10. Unlearning API

### POST /api/v1/unlearning/requests
```
Request:
{
  "target_type": "conversation",
  "target_id": "uuid",
  "reason": "User GDPR deletion request",
  "gdpr_article": "17",
  "priority": "normal"
}

Response 202:
{
  "request_id": "uuid",
  "status": "queued",
  "estimated_completion": "2026-01-01T00:05:00Z",
  "deletion_plan": {
    "postgres_tables": ["chat_sessions", "messages", "memory_entries"],
    "redis_keys": ["chat:stream:*"],
    "qdrant_collections": ["documents", "memory"],
    "minio_paths": ["uploads/temp/*"],
    "ml_actions": ["influence_removal", "sisa_retrain"]
  }
}
```

### GET /api/v1/unlearning/requests/{request_id}
```
Response 200:
{
  "id": "uuid",
  "status": "processing",  # pending, queued, processing, completed, failed, verified
  "progress": 0.45,
  "current_step": "Removing Qdrant embeddings",
  "steps": [
    { "name": "PostgreSQL deletion", "status": "completed", "duration_ms": 150 },
    { "name": "Redis cache clear", "status": "completed", "duration_ms": 45 },
    { "name": "Qdrant embedding removal", "status": "processing", "duration_ms": null },
    { "name": "MinIO file deletion", "status": "pending" },
    { "name": "ML influence removal", "status": "pending" },
    { "name": "Proof generation", "status": "pending" }
  ],
  "created_at": "...",
  "completed_at": null
}
```

### GET /api/v1/unlearning/requests
```
Query: ?status=completed&target_type=conversation&page=1
Response 200: { "data": [ { ... } ] }
```

### POST /api/v1/unlearning/requests/{request_id}/retry
```
Response 202: { "message": "Retry initiated" }
```

### GET /api/v1/unlearning/queue
```
Admin endpoint:
Response 200:
{
  "pending": 23,
  "processing": 5,
  "completed_today": 150,
  "failed": 2,
  "average_processing_time_ms": 3200
}
```

---

## 11. Verification API

### GET /api/v1/verify/proofs/{proof_id}
```
Response 200:
{
  "id": "uuid",
  "request_id": "uuid",
  "proof_type": "merkle",
  "merkle_root": "a1b2c3d4...",
  "merkle_tree_depth": 12,
  "signature_hex": "ed25519_sig...",
  "public_key_hex": "ed25519_pub...",
  "verified": true,
  "verified_at": "2026-01-01T00:05:00Z",
  "certificate": "-----BEGIN DELETION CERTIFICATE-----\n..."
}
```

### POST /api/v1/verify/proofs/{proof_id}/verify
```
Response 200:
{
  "is_valid": true,
  "verification_details": {
    "merkle_root_valid": true,
    "signature_valid": true,
    "tree_integrity": true,
    "timestamp_valid": true
  },
  "verified_at": "2026-01-01T00:05:00Z"
}
```

### GET /api/v1/verify/proofs
```
Query: ?request_id=uuid&verified=true&page=1
Response 200: { "data": [ { ... } ] }
```

### GET /api/v1/verify/certificates/{certificate_hash}
```
Response 200: { "certificate": { ... } }
```

---

## 12. Security API

### POST /api/v1/security/assessments
```
Request:
{
  "model_version_id": "uuid",
  "tests": ["membership_inference", "model_extraction", "model_inversion"],
  "config": {
    "membership_inference": { "attack_percentage": 0.1, "num_shadow_models": 5 },
    "model_extraction": { "num_queries": 1000, "strategy": "adaptive" }
  }
}

Response 202:
{
  "assessment_id": "uuid",
  "status": "queued",
  "estimated_completion": "2026-01-01T00:10:00Z"
}
```

### GET /api/v1/security/assessments/{assessment_id}
```
Response 200:
{
  "id": "uuid",
  "model_version_id": "uuid",
  "status": "completed",
  "scores": {
    "membership_inference": { "score": 0.03, "risk": "low" },
    "model_extraction": { "score": 0.12, "risk": "low" },
    "model_inversion": { "score": 0.08, "risk": "low" },
    "overall": { "score": 0.07, "risk": "low" }
  },
  "recommendations": [
    "Consider increasing differential privacy epsilon",
    "Model is resistant to current attack vectors"
  ]
}
```

---

## 13. Audit API

### GET /api/v1/audit/events
```
Query: ?event_type=unlearning.complete&resource_type=conversation&actor_id=uuid&from=2026-01-01&to=2026-01-02&page=1
Response 200: { "data": [ { "id", "event_type", "actor", "resource", "timestamp", "event_hash" } ] }
```

### GET /api/v1/audit/events/{event_id}
```
Response 200:
{
  "id": "uuid",
  "event_type": "unlearning.complete",
  "actor": { "id": "uuid", "type": "user", "name": "John Doe" },
  "resource": { "type": "conversation", "id": "uuid" },
  "action": "delete",
  "status": "success",
  "metadata": { "proof_id": "uuid", "algorithm": "hybrid" },
  "event_hash": "a1b2c3d4...",
  "previous_event_hash": "e5f6g7h8...",
  "merkle_node_hash": "i9j0k1l2...",
  "timestamp": "2026-01-01T00:05:00Z"
}
```

### GET /api/v1/audit/chain/status
```
Response 200:
{
  "chain_length": 15000,
  "last_event_hash": "...",
  "merkle_root": "...",
  "blockchain_anchored": true,
  "last_anchored_at": "2026-01-01T00:00:00Z",
  "blockchain_tx_hash": "0x..."
}
```

---

## 14. Compliance API

### POST /api/v1/compliance/reports
```
Request:
{
  "report_type": "gdpr",
  "period_start": "2026-01-01",
  "period_end": "2026-03-31"
}

Response 202: { "report_id": "uuid", "status": "generating" }
```

### GET /api/v1/compliance/reports/{report_id}
```
Response 200:
{
  "id": "uuid",
  "report_type": "gdpr",
  "period": { "start": "2026-01-01", "end": "2026-03-31" },
  "overall_score": 94.5,
  "sections": {
    "right_to_be_forgotten": { "score": 98, "status": "compliant" },
    "data_minimization": { "score": 92, "status": "compliant" },
    "consent_management": { "score": 95, "status": "compliant" },
    "breach_notification": { "score": 90, "status": "compliant" }
  },
  "findings": [
    { "severity": "low", "category": "data_retention", "description": "...", "recommendation": "..." }
  ],
  "risk_score": 5.5,
  "status": "generated"
}
```

### GET /api/v1/compliance/certificates
```
Query: ?request_id=uuid&page=1
Response 200: { "data": [ { "id", "certificate_hash", "issued_at", "expires_at", "revoked" } ] }
```

### GET /api/v1/compliance/certificates/{certificate_hash}/download
```
Response 200: application/json (full certificate download)
```

---

## 15. Admin API

### GET /api/v1/admin/users
```
Query: ?page=1&page_size=25&role=member&is_active=true
Response 200: { "data": [ { "id", "email", "full_name", "role", "is_active", "last_login", "created_at" } ] }
```

### PATCH /api/v1/admin/users/{user_id}
```
Request: { "role": "admin", "is_active": true }
Response 200: { "user": { ... } }
```

### GET /api/v1/admin/gpu-metrics
```
Response 200:
{
  "gpus": [
    { "id": 0, "name": "A100-80GB", "utilization": 0.45, "memory_used": 40.2, "memory_total": 80, "temperature": 65 }
  ]
}
```

### GET /api/v1/admin/jobs
```
Query: ?status=processing&type=unlearning&page=1
Response 200: { "data": [ { "id", "type", "status", "progress", "started_at", "worker_id" } ] }
```

### GET /api/v1/admin/analytics
```
Query: ?from=2026-01-01&to=2026-03-31&granularity=day
Response 200:
{
  "metrics": {
    "total_chats": 15000,
    "total_messages": 250000,
    "total_documents": 500,
    "total_unlearning_requests": 1200,
    "total_proofs_generated": 1200,
    "average_response_time_ms": 850,
    "active_users": 350,
    "api_requests": 500000
  },
  "over_time": [ { "date": "2026-01-01", "chats": 500, "messages": 8000 } ]
}
```

---

## 16. Health & Monitoring API

### GET /api/v1/health
```
Response 200:
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 86400,
  "components": {
    "postgresql": { "status": "healthy", "latency_ms": 2 },
    "redis": { "status": "healthy", "latency_ms": 1 },
    "qdrant": { "status": "healthy", "latency_ms": 5 },
    "minio": { "status": "healthy", "latency_ms": 3 },
    "rabbitmq": { "status": "healthy", "connections": 12 },
    "celery": { "status": "healthy", "active_workers": 8 }
  }
}
```

### GET /api/v1/health/ready
```
Response 200: { "status": "ready" }
```

### GET /api/v1/health/live
```
Response 200: { "status": "alive" }
```

---

## 17. Webhook API

```json
// Webhook payload format
{
  "event": "unlearning.completed",
  "timestamp": "2026-01-01T00:05:00Z",
  "tenant_id": "uuid",
  "payload": {
    "request_id": "uuid",
    "proof_id": "uuid",
    "certificate_hash": "abc123",
    "target_type": "conversation",
    "target_id": "uuid",
    "algorithm": "hybrid",
    "duration_ms": 3200,
    "verified": true
  }
}
```

Webhook registration via admin API:
```json
POST /api/v1/admin/webhooks
{
  "url": "https://customer.example.com/webhooks/veriunlearn",
  "events": ["unlearning.completed", "unlearning.failed", "proof.generated"],
  "secret": "whsec_..."
}
```

---

## 18. Rate Limiting

```
Headers:
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 985
X-RateLimit-Reset: 1704067200

Tiers:
- Free: 100 req/min
- Starter: 1000 req/min
- Professional: 10000 req/min
- Enterprise: Custom
```

---

## 19. API Changelog

| Version | Date | Changes |
|---------|------|---------|
| v1.0.0 | 2026-01-01 | Initial release |

---

*This API specification is authoritative. All implementations must conform to these contracts. Changes require architectural review and version bump.*
