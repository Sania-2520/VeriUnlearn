# VeriUnlearn — Major Project Report

**Verifiable Machine Unlearning Framework for GDPR Right-to-Be-Forgotten Compliance**

*Submitted in partial fulfilment of the requirements for the degree of Bachelor of Technology (Computer Science & Engineering)*

---

## Certificate

*This is to certify that the project report entitled "VeriUnlearn: A Verifiable Machine Unlearning Framework for GDPR Right-to-Be-Forgotten Compliance" is a bonafide record of work carried out by the undersigned student(s) under my supervision, in partial fulfilment of the requirements for the award of the degree. The work has not been submitted previously for any other degree or diploma.*

**Signature of Student(s):** ______________________  **Signature of Guide:** ______________________

**Date:** ______________________

## Acknowledgement

We express our sincere gratitude to our project guide for their invaluable guidance, to the department faculty for their support, and to the open-source community whose libraries (FastAPI, Scikit-learn, Next.js, cryptography, and others) made this work possible. We also acknowledge the research community's foundational work on machine unlearning, SISA, certified removal, and membership-inference auditing, which this project builds upon.

## Abstract

The Right to be Forgotten (GDPR Article 17, DPDP Act 2023) obliges organisations to erase personal data — including its influence on trained machine learning models. Full retraining is expensive and unverifiable. This project presents **VeriUnlearn**, an end-to-end framework that makes unlearning efficient (SISA sharding, certified Newton-step removal, influence functions) and *provable* (Merkle-root deletion proofs, RSA-signed certificates, hash-chained audit trail, optional blockchain anchoring). Evaluation on Adult Census shows certified removal matching full-retraining utility (0.777 accuracy) in 0.32 s with a mathematical drift bound, and post-deletion membership-inference AUC at chance level (0.48). The system ships a reproducible 6-method benchmark, a four-family attack suite, compliance dashboards, RBAC, monitoring, and CI/CD — a production-ready reference implementation.

## Table of Contents

1. Introduction
2. Problem Statement
3. Existing System
4. Proposed System
5. System Architecture
6. Implementation
7. Database Design
8. API Design
9. Algorithms
10. Testing
11. Results
12. Advantages
13. Limitations
14. Future Scope
15. Conclusion
16. References
17. Appendices

## List of Figures

- Fig. 1 — High-level architecture (layers)
- Fig. 2 — Unlearning pipeline sequence
- Fig. 3 — ER diagram
- Fig. 4 — SISA shard retraining
- Fig. 5 — Merkle deletion proof
- Fig. 6 — Benchmark radar / comparison
- Fig. 7 — MIA AUC before/after
- Fig. 8 — Deployment topology

*Editable sources for all figures: `docs/diagrams.md` (Mermaid).*

## List of Tables

- Table 1 — Roles & permissions (RBAC)
- Table 2 — Deletion methods comparison
- Table 3 — Benchmark results (utility/cost)
- Table 4 — Security evaluation results
- Table 5 — API surface summary
- Table 6 — Test suite summary

## 1. Introduction

Machine learning models trained on user data encode personal information. When a user exercises their right to erasure, the data's *influence* on the model must be removed. Retraining from scratch is costly, and there is currently no standard way to *prove* deletion. VeriUnlearn builds a complete platform that performs surgical unlearning and produces cryptographic evidence of deletion, ready for audit by regulators or data subjects.

## 2. Problem Statement

Given dataset `D` with a data subject's records `D_u`, and model `M` trained on `D`, produce `M′` ≈ model trained on `D \ D_u`, minimizing deletion cost, utility loss, residual privacy leakage, and the verifiability gap (absence of checkable evidence).

## 3. Existing System

- Manual deletion from databases (no model influence removal).
- Full retraining (correct but expensive, unverifiable).
- Research prototypes: SISA, certified removal, influence functions — each isolated, non-integrated, non-deployable, without evidence artefacts.

**Gap:** no integrated, production-deployable, verifiable unlearning system with benchmark + attack tooling.

## 4. Proposed System

VeriUnlearn: a modular web platform with (1) SISA-based sharded training; (2) three deletion methods with cost/utility trade-offs; (3) Merkle/RSA/audit-chain/blockchain proof stack; (4) 8-check verification engine; (5) reproducible 6-method benchmark and 4-family attack suite; (6) enterprise layer: RBAC, compliance dashboards, monitoring, notifications, API keys, analytics, CI/CD.

## 5. System Architecture

Six layers: Data → ML → Privacy → Unlearning → Proof & Verification → Platform (see Fig. 1; full detail in `docs/architecture.md`). Backend: FastAPI + SQLAlchemy (async). Frontend: Next.js 15 + TanStack Query. Deploy: Docker Compose + NGINX + Prometheus + Grafana.

## 6. Implementation

**Phases.**

| Phase | Scope | Key artefacts |
|---|---|---|
| 1–2 | Foundation, datasets, models, auth | ingestion, SISA trainer, JWT auth |
| 3–4 | Privacy auditor, surgical unlearning | PII detection, footprint, impact analysis, deletion reports |
| 5 | Verification & certificates | Merkle engine, certificates, proofs, blockchain |
| 6 | Research suite | benchmark, attacks, experiments, research metrics |
| 7 | Enterprise platform | RBAC, admin, compliance, monitoring, notifications, API keys, CI/CD |

**Modules (backend).** 30+ services: `crypto`, `sisa`, `certified_removal`, `influence`, `merkle_engine`, `certificate`, `verification_engine`, `zkproof`, `attacks`, `benchmark_engine`, `experiments`, `research_metrics`, `pii_detection`, `privacy`, `unlearning`, `compliance`, `admin`, `analytics`, `api_keys`, `notifications`, `monitoring`, `metrics`, `audit`.

**Frontend.** 20+ pages across dashboard, privacy, unlearning, verification, certificates, audit, compliance, attacks, benchmark, research, monitoring, developer, admin, notifications.

## 7. Database Design

SQLAlchemy models, Alembic migrations (8 additive, one per phase). Core tables: `users`, `datasets`, `dataset_versions`, `models`, `model_shards`, `deletion_requests`, `tombstones`, `certificates`, `verification_reports`, `audit_events`, `privacy_reports`, `search_history`, `benchmark_results`, `attack_results`, `experiments`, `performance_metrics`, plus Phase 7: `roles`, `permissions`, `api_keys`, `notifications`, `system_metrics`, `compliance_reports`, `deployment_logs`, `analytics_cache`. (ER diagram: Fig. 3 / `docs/diagrams.md`.)

## 8. API Design

REST under `/api/v1`; JWT or `X-API-Key` auth; Pydantic validation; standard error envelope `{error, message, details}`; OpenAPI at `/docs`. 60+ endpoints across auth, datasets, models, privacy, unlearning, verification, certificates, compliance, attacks, benchmark, research, admin, api-keys, notifications, monitoring, analytics. (Full reference: `docs/api.md`.)

## 9. Algorithms

- **SISA**: stratified sharding, independent shard training, soft-vote inference; deletion retrains affected shards only.
- **Certified removal**: Newton update `w′ = w − H⁻¹∇L_D(w)`, `H = XᵀDX/n + λI`, bound `‖w′−w‖₂·max‖x‖₂`.
- **Influence scoring**: first-order per-record contribution estimates.
- **Merkle proof**: canonical hashing of tombstones → recomputable pre/post roots; O(log n) membership proofs.
- **MIA**: confidence-separation AUC.
- **Poisoning suite**: backdoor / label-flip / gradient with persistence + detection metrics.

## 10. Testing

**Suite:** 65 tests, ~78% coverage, one file per phase (`test_crypto`, `test_api`, `test_phase34`, `test_phase5`, `test_phase6`, `test_phase7`, `test_pii_detection`, `test_unlearning_flow`).

**Types:** unit (services), integration (AsyncClient over the app), API (auth, RBAC, rate limiting), security (headers, CSRF, API-key middleware), regression (full suite in CI), plus benchmark job in CI. (Full report: `docs/testing-report.md`.)

## 11. Results

| Method | Accuracy | F1 | Deletion time |
|---|---|---|---|
| Original | 0.777 | 0.362 | — |
| SISA retrain | 0.777 | 0.362 | 0.44 s |
| Certified removal | 0.777 | 0.362 | 0.32 s · bound 1.5e3 |
| Influence scrub | 0.760 | 0.143 | 0.13 s |

Privacy: MIA AUC 0.48 post-deletion (chance); backdoor persistence collapses after unlearning; inversion reconstruction degrades.

## 12. Advantages

- Efficient + provable unlearning in one pipeline
- Independently verifiable evidence (certificates, roots, audit chain)
- Reproducible research tooling (seeds, versions, exports, LaTeX)
- Production-ready (RBAC, compliance, monitoring, CI/CD, Docker)
- Open source (MIT)

## 13. Limitations

Certified method is convex-only; MIA is confidence-based (no shadow models); recovery-rate harness pending; in-memory benchmark is memory-bound at large scale; GPU metrics not collected.

## 14. Future Scope

Deep-model unlearning on GPU, shadow-model auditing, embedding-extraction harness, distributed training + multi-node Merkle, SSO/OIDC, alerting, multi-tenancy, compliance evidence bundles.

## 15. Conclusion

VeriUnlearn demonstrates that efficient, verifiable, and auditable machine unlearning is achievable in an integrated, deployable system — a reference implementation for GDPR Art. 17 / DPDP compliance engineering and a benchmark substrate for unlearning research.

## 16. References

1. Bourtoule et al., "Machine Unlearning," IEEE S&P 2021.
2. Guo et al., "Certified Data Removal from Machine Learning Models," ICML 2020.
3. Koh & Liang, "Understanding Black-box Predictions via Influence Functions," ICML 2017.
4. Eisenhofer et al., "Verifiable and Provably Secure Machine Unlearning," 2022.
5. Ginart et al., "Making AI Forget You," NeurIPS 2019.
6. Jagielski et al., "Membership Inference Attacks from First Principles," IEEE S&P 2022.
7. VeriUnlearn project documentation (`docs/`), IEEE paper (`docs/ieee-paper.md`).

## 17. Appendices

- **A. Setup** — `docs/installation.md`
- **B. Configuration** — `docs/configuration.md`
- **C. API reference** — `docs/api.md`
- **D. Diagrams** — `docs/diagrams.md`
- **E. Demo scripts & viva** — `docs/demo-scripts.md`, `docs/viva-guide.md`
- **F. Deployment** — `docs/deployment.md`
- **G. Deliverables per phase** — `docs/phase3-4|5|6|7-deliverables.md`
