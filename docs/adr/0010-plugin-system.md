# ADR-0010: DB-backed plugin system via importlib

- **Status:** Accepted (2026-03)

## Context

Researchers need to extend VeriUnlearn with custom algorithms, metrics, reports, and
visualizations without forking the core.

## Decision

`PluginEntry` model stores name, type, version, entry point, config, and enabled flag.
`PluginManagerService` loads modules at runtime via `importlib.import_module(entry_point)`.
Eight plugin types: Algorithm, Metric, Report, Dashboard, Verification, Policy, DataSource,
Visualization. SDK interfaces in `app.future.sdk.interfaces` (`PluginBase` with
`initialize()` / `shutdown()` / `health_check()`).

## Consequences

- ✅ Extensibility without code changes; plugins are first-class DB records.
- ✅ Dynamic loading isolated behind the manager (failure doesn't crash core).
- ❌ Arbitrary code execution risk — only trusted admins can register plugins (RBAC-gated).
- ❌ Plugin lifecycle/versioning must be managed (enabled flag + version column).

## Alternatives considered

- Entry-point-based packaging (rejected: harder to toggle at runtime).
- Embedding in core (rejected: violates open/closed, bloats releases).
