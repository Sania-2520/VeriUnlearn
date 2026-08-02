# VeriUnlearn — Documentation Index

Index of all files under `docs/` and `artifacts/` with a one-line description.

## docs/ (existing)

| File | Description |
|------|-------------|
| `docs/RELEASE.md` | Top-level release overview for v1.0. |
| `docs/RELEASE_CHECKLIST.md` | Pre-release gate checklist (tag, CHANGELOG, CI, scans). |
| `docs/DEPLOYMENT_CHECKLIST.md` | Pre/post-deploy checklist for Compose + Helm. |
| `docs/deployment.md` | Detailed deployment guide (Compose, Helm, cloud). |
| `docs/production-deployment.md` | Production hardening and scaling notes. |
| `docs/disaster-recovery.md` | Backup/restore procedures, RPO/RTO targets, recovery scenarios. |
| `docs/DEMO_WALKTHROUGH.md` | Step-by-step product demo script. |
| `docs/DEMO_VIDEO_OUTLINE.md` | Outline/screenplay for the demo video. |
| `docs/PRESENTATION_ASSETS.md` | Slide/deck asset list for talks. |
| `docs/verification.md` | Verification concepts (Merkle, signatures, certs). |
| `docs/verification-guide.md` | How-to for generating/verifying proofs. |
| `docs/security-guide.md` | Security controls guide. |
| `docs/user-manual.md` | End-user manual for the dashboard. |
| `docs/troubleshooting-guide.md` | Common failures and fixes. |
| `docs/machine-unlearning-guide.md` | Conceptual unlearning guide. |
| `docs/governance-guide.md` | GDPR/CCPA governance workflows. |
| `docs/frontend-guide.md` | Frontend architecture/usage. |
| `docs/developer-guide.md` | Contributor dev setup. |
| `docs/diagrams.md` | Architecture/sequence diagrams. |
| `docs/PLUGIN_SDK_GUIDE.md` | Plugin/adapter SDK guide. |
| `docs/contributing.md` | Contribution process. |
| `docs/FUTURE_ROADMAP.md` | Product/tech roadmap. |
| `docs/adr/README.md` | ADR index. |
| `docs/adr/0001-monorepo-packages.md` … `0014-audit-hash-chain.md` | Architecture Decision Records. |
| `docs/adr/ADR-0001-architecture.md` | **New** — 3-tier frontend/backend/ml-engine split ADR. |

## artifacts/ (this release-prep batch)

| File | Description |
|------|-------------|
| `artifacts/AUDIT_REPORT.md` | Full repo audit: security, correctness, maintainability + remediation status. |
| `artifacts/TECHNICAL_DEBT.md` | Catalog of debt (orphaned modules, test gaps, dup logic, config sprawl) + severity/remediation. |
| `artifacts/BUG_FIX_SUMMARY.md` | Tier-1 fix changelog with file:line + before/after. |
| `artifacts/BENCHMARK_PLAN.md` | Eval suite: datasets, algorithms, metrics, outputs, harness location. |
| `artifacts/DOCS_INDEX.md` | This file. |
| `artifacts/DEPLOYMENT_CHECKLIST.md` | Consolidated v1.0 RC deploy checklist (extends `docs/DEPLOYMENT_CHECKLIST.md`). |
| `artifacts/SECURITY_AUDIT.md` | Threat model + controls (auth, RBAC, deletion, provenance, ZK, secrets, audit). |
| `artifacts/PERFORMANCE_REPORT.md` | Latency/runtime/memory per algorithm + proxy overhead + scaling notes. |
| `artifacts/RELEASE_NOTES_v1.0.md` | User-facing + technical v1.0 RC release notes. |
| `artifacts/IEEE_ASSET_LIST.md` | Enumerated IEEE submission assets (sections, figures, code, video, deck). |
| `artifacts/LIMITATIONS.md` | Honest current limitations (real-model wiring, eval not run, orphans, single-tenant). |
| `artifacts/FUTURE_WORK.md` | Roadmap (wire orphans, real-model eval, multi-tenant, more algos, formal verification). |
| `artifacts/ARCHITECTURE.md` | Mermaid diagrams: context, request flow, RBAC, CI/CD. |
