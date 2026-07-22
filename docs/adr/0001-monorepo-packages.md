# ADR-0001: Monorepo with `packages/` layout

- **Status:** Accepted (2025-11)
- **Deciders:** Core architecture team

## Context

VeriUnlearn spans a backend API, an ML training/serving engine, a web frontend, and
infrastructure. We needed a structure that allowed independent deployment and testing of
each component while sharing types and tooling.

## Decision

Use a monorepo rooted at the repo top with `packages/backend`, `packages/ml-engine`,
`packages/frontend`, and `packages/shared`. Top-level `infra/`, `docs/`, `nginx/` hold
cross-cutting concerns.

## Consequences

- ✅ Single source of truth; atomic cross-component changes.
- ✅ Shared CI, lint, and dependency policies.
- ❌ Larger repo; `node_modules` and model artifacts must be git-ignored (see `.gitignore`).
- ❌ Build tooling must distinguish Python vs Node workspaces (Makefile orchestrates both).

## Alternatives considered

- Multi-repo (rejected: cross-cutting changes span APIs + engine constantly).
- Single package with subfolders (rejected: couples deploy lifecycle of API and GPU engine).
