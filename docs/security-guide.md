# Security Guide — VeriUnlearn

## Threat Model

| Threat | Mitigation |
|---|---|
| Unauthorized API access | JWT access tokens (15min TTL) + refresh tokens (7d) |
| Credential theft | MFA (TOTP), API key scoping, session revocation |
| Data breach | At-rest encryption (AES-256), in-transit TLS, field-level encryption |
| ML model extraction | Rate limiting, input validation, anomaly detection |
| Membership inference | Differential privacy, certified removal, adversarial regularization |
| Poisoning attacks | Input sanitization, data provenance tracking |
| Replay attacks | Nonce + timestamp verification, JTI blacklist |
| Privilege escalation | RBAC with 5 roles, permission checks on every endpoint |

## RBAC Roles

| Role | Permissions |
|---|---|
| `viewer` | Read-only access to dashboards and reports |
| `member` | Create/read own resources, chat, explainability |
| `unlearning_auditor` | Submit unlearning requests, verify proofs, view audit trail |
| `compliance_officer` | Manage webhooks, compliance settings, audit logs |
| `admin` | Full access including user management, GPU scheduling, system config |

## API Security

- All endpoints (except health/auth/oauth) require JWT authentication
- Rate limiting: 5 req/s on auth, 30 req/s on API
- CORS restricted to configured origins
- Security headers enforced via nginx:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`
  - `Strict-Transport-Security: max-age=31536000`
- Input validation on all ML engine endpoints (type checks, length limits, XSS prevention)

## Secret Management

- All secrets stored in environment variables
- `.env` file is gitignored
- `.env.example` has placeholder values only
- Production secrets managed via GitHub Secrets or AWS Secrets Manager
- Kubernetes secrets created from Terraform/Kustomize

## Audit Trail

- All security-relevant events logged to tamper-proof audit chain
- Each event contains SHA-256 hash of previous event
- Merkle tree root anchored to blockchain (simulated)
- Audit events include: login, logout, password change, API key creation, MFA changes
