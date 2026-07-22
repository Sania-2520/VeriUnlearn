# ADR-0009: 8-role / 24-permission RBAC model

- **Status:** Accepted (2026-02)

## Context

Enterprise governance requires fine-grained, auditable access control across many
personas (admin, ML engineer, compliance officer, auditor, etc.).

## Decision

Define 8 roles (`admin`, `user`/`member`, `ml_engineer`, `researcher`, `compliance_officer`,
`legal_team`, `auditor`, `viewer`) and 24 fine-grained permissions in `app.core.rbac`.
Permissions are enforced via FastAPI dependencies on route handlers.

## Consequences

- ✅ Maps cleanly to real org structures (DPO = compliance_officer, auditor = read-only).
- ✅ Permission matrix is centralized and testable (RBAC tests in backend suite).
- ❌ New endpoints must remember to attach the dependency (lint/code-review guard).
- ❌ Tenant-scoped enforcement is row-level, not separate databases (see ADR-0013).

## Alternatives considered

- 3 coarse roles (rejected: too coarse for compliance separation of duties).
- External OPA (rejected: added dependency; in-code RBAC sufficient at this scale).
