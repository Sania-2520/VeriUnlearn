# ADR-0005: Strategy + Registry pattern for algorithms & verification

- **Status:** Accepted (2026-01)

## Context

VeriUnlearn supports multiple unlearning algorithms and multiple verification strategies.
We needed to add new ones without editing call sites.

## Decision

Two parallel registries:
- `AlgorithmRegistry` holds `UnlearningStrategy` implementations (`SISAUnlearning`,
  `InfluenceUnlearning`, `CerturedRemoval`, `BadTeacherUnlearning`,
  `CatastrophicForgetting`, `ReLUErasure`, `HybridAdaptiveController`).
- `VerificationRegistry` holds `VerificationStrategy` implementations (Hash, Merkle,
  Influence, MembershipInference, ForgetQuality).

Selectors use `can_handle()` / `estimate_cost()`; `AdaptiveController` chooses automatically.

## Consequences

- ✅ Open/closed: new algorithm = new class + `register()`. No route changes.
- ✅ Unit-testable in isolation.
- ❌ Registries are module-level singletons; tests must reset them (handled in conftest).

## Alternatives considered

- if/elif dispatch (rejected: unmaintainable at 7+ algorithms).
- Plugin-only (rejected: built-ins should not require DB/importlib loading).
