# ADR-0013: Tenant-first data model with row-level isolation

- **Status:** Accepted (2026-05)

## Context

VeriUnlearn targets enterprise multi-team deployments. We needed tenant isolation that is
simple to operate today but extensible to stronger isolation later.

## Decision

Every primary entity carries a `tenant_id` FK to `tenants`. Isolation is enforced by
row-level `tenant_id` filters in service-layer queries (not separate databases). Tenant
config (plans, quotas, feature flags) lives in the `tenants` table as JSONB.

## Consequences

- ✅ One database, simple ops, easy cross-tenant reporting where permitted.
- ✅ Quota enforcement via `max_users`, `max_storage_gb`, `max_api_requests_per_min`.
- ❌ Stronger isolation (schema-per-tenant / DB-per-tenant) requires future work
  (`app.future.multitenant.TenantIsolationProvider`).
- ❌ A query bug that forgets the `tenant_id` filter is a cross-tenant leak risk — mitigated
  by repository pattern + tests, but not cryptographically enforced at the DB layer.

## Alternatives considered

- DB-per-tenant (rejected: ops cost at scale for v1).
- Schema-per-tenant (deferred to Phase 10).
