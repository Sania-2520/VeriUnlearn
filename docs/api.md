# VeriUnlearn API Reference

> Complete REST API documentation for the VeriUnlearn platform.
> Backend (FastAPI) runs on `:8000`, the ML Engine (FastAPI) runs on `:8001`.
> Interactive docs are auto-generated: `http://localhost:8000/docs` (backend) and `http://localhost:8001/docs` (ML engine).

---

## Table of Contents

- [Conventions](#conventions)
- [Authentication](#authentication)
- [OpenAPI / Swagger](#openapi--swagger)
- [Backend API (`/api/v1`)](#backend-api-apiv1)
- [ML Engine API (`:8001`)](#ml-engine-api-8001)
- [Request / Response Examples](#request--response-examples)
- [Error Model](#error-model)
- [Rate Limiting](#rate-limiting)

---

## Conventions

| Item | Value |
|------|-------|
| Base URL (backend) | `http://localhost:8000/api/v1` |
| Base URL (ML engine) | `http://localhost:8001` |
| Auth scheme | `Bearer <JWT access token>` (header `Authorization`) |
| API key auth | `X-API-Key: vu_xxxx` header |
| Content-Type | `application/json` |
| Time format | ISO 8601 UTC (`TIMESTAMPTZ`) |
| Identifiers | UUID v4 |

All responses are JSON. Pagination uses `limit` / `offset` query params (default `limit=50`, `offset=0`).

---

## Authentication

Most endpoints require an access token obtained from `POST /api/v1/auth/login`.

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

The JWT carries the `mfa_verified` claim (required for sensitive endpoints when MFA is enforced),
`role`, `tenant_id`, and `sub` (user id). Refresh tokens are opaque and stored in the `sessions` table.

---

## OpenAPI / Swagger

VeriUnlearn exposes standards-compliant OpenAPI 3.1 schemas:

| Endpoint | Description |
|----------|-------------|
| `GET /openapi.json` | Full backend OpenAPI document |
| `GET /docs` | Swagger UI (backend) |
| `GET /redoc` | ReDoc UI (backend) |
| `GET /api/v1/docs` | Versioned Swagger UI |
| ML engine: `GET /docs`, `GET /openapi.json` | ML engine interactive docs |

### Minimal Swagger UI bootstrap (frontend embedding)

```html
<!DOCTYPE html>
<html>
  <head>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist/swagger-ui.css" />
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script>
    <script>
      window.onload = () => {
        window.ui = SwaggerUIBundle({
          url: "http://localhost:8000/openapi.json",
          dom_id: "#swagger-ui",
          deepLinking: true,
          presets: [SwaggerUIBundle.presets.apis],
        });
      };
    </script>
  </body>
</html>
```

### Downloading the spec

```bash
curl -s http://localhost:8000/openapi.json -o veriunlearn-openapi.json
```

A reduced OpenAPI fragment for the unlearning workflow:

```yaml
openapi: 3.1.0
info:
  title: VeriUnlearn API
  version: 1.0.0
paths:
  /api/v1/unlearning/requests:
    post:
      summary: Create a machine-unlearning (data deletion) request
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UnlearningRequestCreate'
      responses:
        '201':
          description: Request created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UnlearningRequest'
  /api/v1/verify/proofs/generate:
    post:
      summary: Generate a cryptographic deletion proof + certificate
      security:
        - bearerAuth: []
      responses:
        '200':
          description: Proof generated
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
  schemas:
    UnlearningRequestCreate:
      type: object
      required: [target_type, target_id]
      properties:
        target_type:
          type: string
          enum: [conversation, message, document, embedding, memory, user_data]
        target_id:
          type: string
          format: uuid
        reason:
          type: string
        gdpr_article:
          type: string
          enum: ["17", "16", "32"]
        priority:
          type: string
          enum: [low, normal, high, critical]
          default: normal
```

---

## Backend API (`/api/v1`)

### Auth & Identity
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/auth/register` | Create account (email + password) |
| POST | `/auth/login` | Authenticate, receive access + refresh tokens |
| POST | `/auth/refresh` | Rotate refresh token |
| POST | `/auth/logout` | Revoke session |
| POST | `/auth/oauth/{provider}` | OAuth login (google, github) |
| POST | `/auth/email/verify` | Verify email address |
| POST | `/auth/password/reset` | Request / complete password reset |
| POST | `/auth/mfa/setup` | Begin TOTP MFA enrollment |
| POST | `/auth/mfa/verify` | Verify TOTP code |
| GET/POST | `/auth/mfa/disable` | Disable MFA |
| GET | `/users/me` | Current user profile |
| POST | `/auth/api-keys` | Create API key (`vu_` prefix, SHA-384 stored) |
| GET | `/auth/api-keys` | List API keys |
| DELETE | `/auth/api-keys/{id}` | Revoke API key |

### Unlearning & Verification
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/unlearning/requests` | Create deletion request |
| GET | `/unlearning/requests` | List requests (filter by status) |
| GET | `/unlearning/requests/{id}` | Get request detail |
| POST | `/unlearning/requests/{id}/retry` | Retry failed request |
| GET | `/unlearning/jobs` | List unlearning jobs |
| POST | `/verify/proofs/generate` | Generate Merkle + Ed25519 proof |
| POST | `/verify/proofs/verify` | Verify a proof |
| GET | `/verify/proofs` | List proofs |
| POST | `/verify/certificates/generate` | Issue deletion certificate |
| POST | `/verify/zksnark/generate` | Generate zk-SNARK proof |
| POST | `/verify/zksnark/verify` | Verify zk-SNARK proof |
| POST | `/audit/chain/anchor` | Anchor audit chain to blockchain |

### ML Lifecycle
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/training/lora` | Start LoRA training job |
| POST | `/training/datasets` | Upload dataset |
| GET | `/datasets` | List datasets / versions |
| POST | `/adapters/register` | Register LoRA adapter version |
| POST | `/adapters/{name}/activate` | Activate adapter |
| POST | `/adapters/{name}/rollback` | Rollback adapter |
| POST | `/inference/generate` | Run inference |
| POST | `/explain/samples` | Explainable-AI attribution |

### Governance & Compliance
| Method | Path | Purpose |
|--------|------|---------|
| GET/POST | `/compliance/settings` | Compliance configuration |
| POST | `/compliance/webhooks` | Register compliance webhook |
| POST | `/compliance/webhooks/{id}/test` | Test webhook delivery |
| GET | `/compliance/webhooks/{id}/logs` | Webhook delivery logs |
| GET/POST | `/governance/consents` | Consent records |
| GET/POST | `/governance/policies` | Policy engine rules |
| GET/POST | `/governance/approvals` | Multi-level approvals |
| GET | `/governance/risk` | Risk assessment |
| GET | `/governance/lineage` | Data lineage (dataset→model→deletion) |
| POST | `/gdpr/export` | GDPR data export |
| DELETE | `/gdpr/account` | GDPR account deletion |

### Platform
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/chat/sessions` | Create chat session |
| POST | `/chat/sessions/{id}/messages` | Send message (RAG + streaming) |
| POST | `/documents` | Upload document for RAG |
| POST | `/benchmarks/run` | Run benchmark suite |
| GET | `/benchmarks/leaderboard` | Algorithm leaderboard |
| GET | `/experiments` | Experiment tracking |
| GET | `/admin/overview` | Admin stats |
| GET | `/usage` | Quota / rate-limit status |
| GET | `/audit/events` | Tamper-evident audit log |
| GET | `/health`, `/health/ready`, `/health/live` | Health probes |

Full router inventory (28 routers) is in [architecture.md](architecture.md).

---

## ML Engine API (`:8001`)

The backend proxies to the ML engine via the `MLEngineClient` (httpx). Direct engine endpoints:

| Group | Method | Path |
|-------|--------|------|
| Unlearn | POST | `/unlearn`, `/unlearn/e2e` |
| Proof | POST | `/proof/generate`, `/proof/verify`, `/proof/generate-zksnark`, `/proof/verify-zksnark`, `/certificate` |
| Evaluate | POST | `/evaluate/mia`, `/evaluate/privacy` |
| Train | POST | `/train/lora` |
| Adapters | POST/GET | `/adapters/register`, `/adapters/activate`, `/adapters/{name}/rollback`, `/adapters`, ... |
| Explain | POST | `/explain/samples`, `/explain/features`, `/explain/compare`, `/explain/privacy-heatmap` |
| Continual | GET/POST | `/continual/stats`, `/continual/tasks`, `/continual/ewc/estimate`, `/continual/drift/*` |
| Benchmarks | POST/GET | `/benchmarks/run`, `/benchmarks/summary`, `/benchmarks/results` |
| Inference | POST | `/inference/generate`, `/inference/generate/stream`, `/inference/batch` |
| RAG | POST/GET/DELETE | `/rag/documents/ingest`, `/rag/search`, `/rag/documents/{id}` |
| Registry | POST/GET | `/registry/versions`, `/registry/versions/{name}/{id}/rollback` |
| System | GET | `/health`, `/controller/health`, `/mlflow/runs` |

See [api-reference.md](api-reference.md) for the exhaustive table.

---

## Request / Response Examples

### 1. Register a user

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "analyst@acme.example",
  "password": "Str0ng#Passw0rd!",
  "full_name": "Ada Analyst",
  "role": "member"
}
```

```json
{
  "id": "3f1c2b9e-1a2b-4c3d-8e9f-0a1b2c3d4e5f",
  "email": "analyst@acme.example",
  "full_name": "Ada Analyst",
  "role": "member",
  "is_email_verified": false,
  "is_active": true,
  "created_at": "2026-07-17T09:14:22Z"
}
```

### 2. Login

```http
POST /api/v1/auth/login
Content-Type: application/json

{ "email": "analyst@acme.example", "password": "Str0ng#Passw0rd!" }
```

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "rt_8d7c6b5a4e3f...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 3. Create an unlearning request (GDPR Art. 17)

```http
POST /api/v1/unlearning/requests
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "target_type": "conversation",
  "target_id": "9a8b7c6d-5e4f-4031-9a2b-1c0d9e8f7a6b",
  "reason": "User requested erasure under GDPR Article 17",
  "gdpr_article": "17",
  "priority": "high"
}
```

```json
{
  "id": "c1d2e3f4-5678-90ab-cdef-1234567890ab",
  "tenant_id": "11112222-3333-4444-5555-666677778888",
  "requested_by": "3f1c2b9e-1a2b-4c3d-8e9f-0a1b2c3d4e5f",
  "target_type": "conversation",
  "target_id": "9a8b7c6d-5e4f-4031-9a2b-1c0d9e8f7a6b",
  "status": "pending",
  "priority": "high",
  "created_at": "2026-07-17T09:20:11Z"
}
```

### 4. Generate a deletion proof

```http
POST /api/v1/verify/proofs/generate
Authorization: Bearer <access_token>
Content-Type: application/json

{ "request_id": "c1d2e3f4-5678-90ab-cdef-1234567890ab" }
```

```json
{
  "proof_id": "d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f90",
  "proof_type": "merkle",
  "merkle_root": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
  "merkle_tree_depth": 8,
  "signature_algorithm": "ed25519",
  "public_key_hex": "1a2b3c4d5e6f...",
  "signature_hex": "a1b2c3d4e5f6...",
  "certificate_hash": "3b5d...",
  "verified": true,
  "verified_at": "2026-07-17T09:25:44Z"
}
```

### 5. Run a benchmark

```http
POST /api/v1/benchmarks/run
Authorization: Bearer <access_token>
Content-Type: application/json

{ "dataset": "sentiment_synthetic", "algorithms": ["sisa", "influence_function", "certified_removal", "hybrid"], "trials": 5 }
```

```json
{
  "run_id": "b7c8d9e0-1234-5678-90ab-cdef12345678",
  "status": "queued",
  "datasets": ["sentiment_synthetic"],
  "algorithms": ["sisa", "influence_function", "certified_removal", "hybrid"]
}
```

---

## Error Model

All errors follow a uniform JSON envelope:

```json
{
  "error": {
    "code": "unlearning_request_not_found",
    "message": "Unlearning request c1d2... not found",
    "request_id": "req_9a8b7c6d",
    "details": { "resource_id": "c1d2e3f4-..." }
  }
}
```

| HTTP | Common codes |
|------|--------------|
| 400 | `validation_error`, `invalid_credentials` |
| 401 | `unauthorized`, `token_expired` |
| 403 | `permission_denied`, `mfa_required` |
| 404 | `not_found`, `unlearning_request_not_found` |
| 409 | `conflict`, `duplicate_email` |
| 422 | `unprocessable_entity` |
| 429 | `rate_limited` |
| 500 | `internal_error` |

---

## Rate Limiting

`RateLimitAuditMiddleware` enforces a Redis sliding window (per-IP, per-tenant, per-endpoint).
A `429` response includes:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 42
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1752745440
```

Every `429` is recorded as a `rate.limited` audit event with the limit, client IP, and path.
