# ADR-0011: Interface-only `app.future.*` namespace for Phases 7+

- **Status:** Accepted (2026-04)

## Context

Roadmap features (federated, continual, multi-tenant, ZKP, blockchain, confidential compute,
AI copilot, autonomous agents) are large and speculative. We wanted to design contracts now
without committing to implementations that could break the stable API.

## Decision

All future modules live under `app.future.*` as abstract base classes (interfaces) only.
No production implementation ships in this namespace. Existing `EventBus`, plugin system, and
RBAC extend naturally to future modules; core code is not modified to add future modules.

## Consequences

- ✅ Clear contract surface (43 ABCs across 11 modules) for contributors and researchers.
- ✅ Zero breaking changes to Phases 1–6 while designing ahead.
- ❌ Interfaces may drift from eventual implementations (kept honest by roadmap docs).
- ❌ Some duplication risk between `app.ml.*` (real) and `app.future.*` (interfaces).

## Alternatives considered

- Implement futures in a separate repo (rejected: harder to keep contracts aligned).
- Fork-per-feature (rejected: fragments the community).
