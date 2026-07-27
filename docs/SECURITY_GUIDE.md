# Security Guide — VeriUnlearn

## Threat Model

| Threat | Mitigation |
|---|---|
| Unauthorized API access | JWT access tokens (15min TTL) + refresh tokens (7d), OAuth 2.0 |
| Credential theft | MFA (TOTP), API key scoping, session revocation, rate-limited auth |
| Data breach | At-rest encryption (AES-256), in-transit TLS 1.3, field-level encryption |
| ML model extraction | Rate limiting, input validation, anomaly detection, output perturbation |
| Membership inference | Differential privacy, certified removal, adversarial regularization |
| Poisoning attacks | Input sanitization, data provenance tracking, validation engine |
| Replay attacks | Nonce + timestamp verification, JTI blacklist, short token TTL |
| Privilege escalation | RBAC with 8 roles, 24 permissions, per-endpoint authorization checks |
| Path traversal | Input sanitization, validated file paths, restricted file access |
| CORS misconfiguration | Origin whitelisting, restricted HTTP methods |
| DoS / DDoS | Rate limiting (Redis sliding window), connection limits, resource quotas |
| Supply chain | Dependency scanning (Trivy), SBOM generation, signed container images |

---

## Authentication & Authorization

### Authentication Methods

| Method | Endpoint | Use Case |
|--------|----------|----------|
| JWT (access + refresh) | `POST /api/v1/auth/login` | Standard web UI sessions |
| OAuth 2.0 (Google, GitHub) | `GET /api/v1/auth/oauth/{provider}` | Social login / SSO |
| API Keys (`vu_` prefix) | `POST /api/v1/auth/api-keys` | Programmatic / M2M access |
| MFA (TOTP) | `POST /api/v1/auth/mfa/verify` | Elevated security sessions |

### JWT Token Specification

| Field | Value |
|-------|-------|
| Algorithm | HS256 (configurable via `JWT_ALGORITHM`) |
| Access token TTL | 15 minutes (`JWT_ACCESS_TOKEN_EXPIRE_MINUTES`) |
| Refresh token TTL | 7 days (`JWT_REFRESH_TOKEN_EXPIRE_DAYS`) |
| Key length | 64 bytes (`JWT_SECRET_KEY`) |
| Claims | `sub`, `exp`, `iat`, `jti`, `role`, `tenant_id` |

### RBAC Role Model

| Role | Key Permissions |
|------|----------------|
| `admin` | All 24 permissions |
| `user` | Training R/W, Unlearning R/W/Execute, Documents R/W/D, Consent R/W, Governance R |
| `ml_engineer` | Training R/W, Unlearning R/W/Execute, Documents R/W, Risk R, Lineage R |
| `researcher` | Training R, Unlearning R, Documents R, Lineage R (read-only) |
| `compliance_officer` | Consent R/W, Policy R/W, Compliance R/W/Approve, Governance R/W, Retention R/W, Audit Log |
| `legal_team` | Consent R/W, Compliance R/Approve, Governance R, Lineage R |
| `auditor` | Unlearning R, Audit Log, Documents R, Policy R, Compliance R, Governance R, Lineage R |
| `viewer` | Read-only: Users, Training, Unlearning, Documents, Consent, Governance, Lineage |

Permission checks are enforced on every endpoint via FastAPI dependency injection using `get_current_user()` and role guards.

### API Key Security

- Generated with `vu_` prefix for easy identification
- Stored as SHA-384 hash (never plaintext)
- Scoped to specific permissions and expiry dates
- Revocable via admin dashboard or API

---

## API Security

### Rate Limiting

| Scope | Limit | Window | Backend |
|-------|-------|--------|---------|
| Auth endpoints | 5 requests | per second | Redis sliding window |
| API endpoints | 30 requests | per second | Redis sliding window |
| Benchmark endpoints | 5 requests | per second | Redis sliding window |
| Per-tenant API | 100 requests | per second | Redis sliding window |

Rate limit headers are returned on every response:
```
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 27
X-RateLimit-Reset: 1682345678
```

### CORS Configuration

- Restricted to configured origins (`ALLOWED_HOSTS` environment variable)
- In production, `ALLOWED_HOSTS` is set to the specific domain(s)
- Debug mode (`APP_DEBUG=true`) allows broader CORS for development

### Security Headers

Enforced via Nginx reverse proxy:

| Header | Value | Protection |
|--------|-------|------------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | HTTPS enforcement |
| `X-Content-Type-Options` | `nosniff` | MIME-sniffing prevention |
| `X-Frame-Options` | `DENY` | Clickjacking protection |
| `X-XSS-Protection` | `1; mode=block` | Cross-site scripting |
| `Content-Security-Policy` | Restricted by deployment | XSS, data injection |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Referrer leakage |
| `Permissions-Policy` | Restricted features | API/feature abuse |

### Input Validation

- All endpoints validate input via Pydantic v2 models (type checks, length limits, regex patterns)
- ML Engine endpoints have additional validation: XSS pattern detection, SQL injection pattern detection
- File uploads: size limits, MIME type validation, filename sanitization
- Path traversal prevention via `os.path.basename()` checks

---

## Data Encryption

### Encryption at Rest

| Data Store | Encryption Method | Key Management |
|------------|-------------------|----------------|
| PostgreSQL | AES-256 (TDE or application-level) | Environment variable or KMS |
| Redis | Optional AES-256 (require `requirepass`) | Environment variable |
| MinIO | SSE-S3 or SSE-KMS | MinIO config or KMS |
| Disk/Volume | LUKS or cloud-provider encryption | Cloud KMS |

### Encryption in Transit

| Connection | Protocol | Details |
|------------|----------|---------|
| Frontend → Nginx | TLS 1.3 | Let's Encrypt / custom CA |
| Nginx → Backend | HTTP (internal network) | Service mesh recommended |
| Backend → PostgreSQL | TLS 1.3 | Mutual TLS in production |
| Backend → Redis | AUTH + TLS | `REDIS_*` environment variables |
| Backend → ML Engine | HTTP (internal) | Internal Docker network |
| Backend → Qdrant | gRPC with TLS | Optional, configured via `QDRANT_GRPC_*` |
| Backend → MinIO | HTTPS | MinIO TLS configuration |

---

## Cryptographic Verification

### Digital Signatures (Ed25519)

- **Library**: PyNaCl (`nacl.signing.SigningKey` / `VerifyKey`)
- **Key size**: 32 bytes (private), 32 bytes (public)
- **Signature size**: 64 bytes
- **Use**: Signing verification certificates, proof artifacts, audit entries
- **Key management**: Signing key stored in `APP_SECRET_KEY` / secrets manager; verification key embedded in certificates

### Hashing (SHA-256)

- **Library**: `hashlib`
- **Use**: Artifact fingerprinting, audit chain linking, Merkle tree construction
- **Salt**: Per-operation random salt for additional security

### Merkle Trees

- **Implementation**: `app.crypto.merkle`
- **Leaf hashes**: SHA-256 of individual verification artifacts
- **Root**: Ed25519-signed for authenticity
- **Proofs**: Inclusion proofs enable third-party verification without disclosing all leaves

### API Key Hashing

- **Algorithm**: SHA-384
- **Storage**: Only hash stored; plaintext key returned once at creation
- **Prefix**: `vu_` for identification (not stored)

### Audit Chain

- **Structure**: Each entry contains `prev_hash` (SHA-256 of previous entry)
- **Blockchain anchoring**: Celery beat task runs every 6 hours, computing Merkle root over chain and anchoring via `SimulatedBlockchain`
- **Tamper evidence**: Any modification breaks the hash chain

### zk-SNARK Proofs (Prototype)

- **Wrapping**: Keccak-256 Merkle inclusion proof in Groth16-style envelope
- **Components**: `proving_key`, `verification_key`, π_A/π_B/π_C points, Ed25519-signed root
- **Zero-knowledge property**: Verifier learns leaf and root but not leaf index or other leaves
- **Endpoints**: `POST /api/v1/verify/zksnark/generate`, `POST /api/v1/verify/zksnark/verify`

---

## Secret Management

### Environment Variables

- All secrets stored in environment variables (never committed to repository)
- `.env` file is gitignored; `.env.example` contains placeholder values only
- Secret validator rejects placeholder keys when `APP_ENV=production`

### Production Secret Storage

| Platform | Method |
|----------|--------|
| Docker | `.env` file or Docker secrets |
| Kubernetes | Kubernetes Secrets (created via Terraform/Kustomize) |
| AWS EKS | AWS Secrets Manager + CSI driver |
| GitHub Actions | GitHub Secrets (`DOCKER_REGISTRY`, etc.) |

### Key Rotation

| Secret | Rotation Frequency | Method |
|--------|-------------------|--------|
| `JWT_SECRET_KEY` | 90 days | Deploy new value, old tokens invalidated |
| `APP_SECRET_KEY` | 180 days | Deploy new value, certificates re-signed |
| `POSTGRES_PASSWORD` | 90 days | Zero-downtime rotation via managed DB |
| API Keys | On-demand | Revoke old key, issue new key |

---

## Audit Logging

### Audit Events

All security-relevant events are logged to the tamper-evident audit chain:

| Category | Events |
|----------|--------|
| Authentication | login, logout, login_failed, password_change, mfa_enabled, mfa_disabled |
| API Keys | api_key_created, api_key_revoked, api_key_used |
| Authorization | permission_denied, role_changed, user_suspended |
| Unlearning | deletion_requested, validation_passed, unlearning_started, unlearning_completed, rollback_performed |
| Governance | consent_granted, consent_withdrawn, policy_violation, approval_granted, approval_rejected |
| Compliance | data_exported, account_deleted, webhook_dispatched, webhook_failed |
| Admin | user_created, user_deleted, system_config_changed |

### Audit Chain Structure

```json
{
  "index": 1042,
  "timestamp": "2026-07-27T12:34:56.789Z",
  "event_type": "deletion_requested",
  "actor_id": "user_abc123",
  "resource_id": "unlearning_req_xyz789",
  "action": "create",
  "metadata": { "algorithm": "sisa", "samples": 150 },
  "prev_hash": "a1b2c3d4...",
  "hash": "e5f6g7h8..."
}
```

### Log Locations

| Environment | Log Location | Format |
|-------------|-------------|--------|
| Development | `logs/backend.log` | JSON lines |
| Docker | `docker compose logs backend` | JSON lines |
| Kubernetes | `kubectl logs -n veriunlearn deploy/backend` | JSON lines |
| Production | Loki (aggregated) | Structured JSON |

---

## Compliance Mapping

### GDPR (General Data Protection Regulation)

| Article | Requirement | Implementation |
|---------|-------------|----------------|
| Art. 17 | Right to erasure | Unlearning pipeline + cryptographic deletion certificate |
| Art. 32 | Security of processing | Audit hash chain, blockchain anchoring, encryption |
| Art. 15 | Right of access | Data lineage export, `POST /api/v1/gdpr/export` |
| Art. 20 | Right to data portability | Dataset export endpoints |
| Art. 30 | Records of processing | Complete audit trail with immutable chain |
| Art. 33 | Breach notification | Alertmanager integration, compliance webhooks |
| Art. 35 | DPIA | Risk assessment service, governance scoring |

### CCPA / CPRA (California Consumer Privacy Act)

| Requirement | Implementation |
|-------------|----------------|
| Right to know | Lineage export, consent history |
| Right to delete | Unlearning pipeline + verification certificate |
| Right to opt-out | Consent withdrawal → auto-triggered unlearning |
| Non-discrimination | Utility retention monitoring after unlearning |

### DPDP Act 2023 (India)

| Requirement | Implementation |
|-------------|----------------|
| Consent management | Full consent lifecycle with withdrawal → unlearning cascade |
| Right to erasure | Unlearning + cryptographic proof |
| Data fiduciary obligations | Compliance workflow engine, policy templates |
| Breach notification | Webhook dispatch, audit logging |

### EU AI Act

| Requirement | Implementation |
|-------------|----------------|
| Risk classification | Risk assessment service, governance scoring |
| Transparency | Explainability (SHAP, LIME, Integrated Gradients) |
| Human oversight | Approval workflows, audit trail |
| Accuracy / robustness | Benchmark suite, drift detection, forget quality metrics |

---

## Incident Response

### Severity Levels

| Level | Description | Response Time | Fix Timeline |
|-------|-------------|---------------|-------------|
| CRITICAL | Active data breach, auth bypass | 15 minutes | 4 hours |
| HIGH | ML model extraction, privilege escalation | 1 hour | 24 hours |
| MEDIUM | Rate limit bypass, logging gap | 4 hours | 7 days |
| LOW | Information disclosure (non-sensitive) | 24 hours | 30 days |

### Response Process

1. **Detection** — Automated monitoring (Prometheus alerts, Grafana, Sentry)
2. **Triage** — Security team assesses severity and impact
3. **Containment** — Rate limiting, key rotation, service isolation
4. **Eradication** — Patch deployment, configuration fix
5. **Recovery** — Service restoration, data integrity verification
6. **Post-mortem** — Root cause analysis, prevention measures

### Reporting

- **Security issues**: security@veriunlearn.com
- **PGP key**: Available on request
- **Disclosure timeline**: 90 days for fixed vulnerabilities

---

## Related Documents

- [Architecture Guide](ARCHITECTURE_GUIDE.md) — System architecture and security boundaries
- [Verification Guide](verification-guide.md) — Cryptographic primitives and proof flow
- [Governance Guide](governance-guide.md) — Compliance workflows and consent management
- [Deployment Guide](deployment.md) — Production security configuration
- [SECURITY.md](../SECURITY.md) — Vulnerability reporting policy
- [Architecture Decision Records](adr/) — Security-related ADRs
