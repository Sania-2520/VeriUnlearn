# VeriUnlearn — IEEE Asset List

**Date:** 2026-07-18 · **Target:** v1.0 RC → IEEE submission
Enumerated assets required for the IEEE publication, each referenced to a file in the repo.

---

## 1. Paper Sections (suggested mapping)

| Section | Content | Source |
|---------|---------|--------|
| Abstract / Intro | Verifiable unlearning SaaS | `README.md`, `docs/RELEASE.md` |
| Background | Unlearning taxonomy | `docs/machine-unlearning-guide.md` |
| Architecture | 3-tier design | `artifacts/ARCHITECTURE.md`, `docs/adr/ADR-0001-architecture.md`, `docs/adr/0003-separate-ml-engine.md` |
| Algorithms | SISA/Influence/Certified/Hybrid | `packages/ml-engine/unlearning/` + `unlearning/hybrid_controller.py` |
| Verification | Merkle + signatures + certs | `packages/ml-engine/verification/merkle_tree.py`, `signatures.py` |
| Security/Privacy | MIA, inversion, ZK | `packages/ml-engine/security/attacks/membership_inference.py`, `verification/zksnark/`, `docs/adr/0012-zero-knowledge-proofs.md` |
| Compliance | GDPR/CCPA | `packages/backend/app/api/v1/compliance.py`, `docs/governance-guide.md` |
| Evaluation | Benchmarks | `artifacts/BENCHMARK_PLAN.md`, `demo/benchmark-reports/sample-report.json` |
| Limitations/Future | Honesty | `artifacts/LIMITATIONS.md`, `artifacts/FUTURE_WORK.md` |

## 2. Figures

| Figure | Description | Source |
|--------|-------------|--------|
| Fig 1 | System context diagram | `artifacts/ARCHITECTURE.md` (Mermaid A) |
| Fig 2 | Unlearn+verify request flow | `artifacts/ARCHITECTURE.md` (Mermaid B) |
| Fig 3 | RBAC permission model | `artifacts/ARCHITECTURE.md` (Mermaid C), `packages/backend/app/core/rbac.py` |
| Fig 4 | CI/CD pipeline | `artifacts/ARCHITECTURE.md` (Mermaid D) |
| Fig 5 | Benchmark table (forget/MIA/utility/runtime) | `demo/benchmark-reports/sample-report.json`, `evaluation/export.py` (LaTeX) |
| Fig 6 | Privacy/utility trade-off plots | `evaluation/visualization.py` |
| Fig 7 | Certificate / Merkle proof example | `proofs/certificates/VUC-*/certificate.json` |

## 3. Code Artifacts

- Monorepo: `packages/frontend`, `packages/backend`, `packages/ml-engine`, `packages/shared`.
- Repro harness: `evaluation/` (runner, datasets, algorithms, metrics, export, reproducibility).
- Infra-as-code: `infra/kubernetes/helm/veriunlearn/`, `docker-compose.yml`, `scripts/*.sh`.
- License: `LICENSE` (Apache-2.0); `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`.

## 4. Demo Video

- Outline: `docs/DEMO_VIDEO_OUTLINE.md`.
- Walkthrough: `docs/DEMO_WALKTHROUGH.md`.
- Asset generation: `scripts/generate_demo_assets.py`, `scripts/demo.sh`.
- Demo models/sample certs: `demo/models/*.json`, `demo/verification-certificates/`.

## 5. Presentation

- Asset list: `docs/PRESENTATION_ASSETS.md`.
- Diagrams source: `docs/diagrams.md`, `artifacts/ARCHITECTURE.md`.

## 6. Reproducibility Package

- `evaluation/reproducibility.py` records commit SHA + dataset hashes.
- Benchmark JSON schema: `demo/benchmark-reports/sample-report.json`.
- v1.0 eval output: `<to be populated by eval harness>` (not yet run — LIMITATIONS).

---

## Submission Readiness Checklist

- [x] Architecture + diagrams.
- [x] Algorithm + verification descriptions with cited modules.
- [x] Demo video outline + assets.
- [ ] **Final benchmark numbers** (harness run pending).
- [ ] **Real-model eval** (torch wiring pending).
- [ ] Presentation deck built from `PRESENTATION_ASSETS.md`.
