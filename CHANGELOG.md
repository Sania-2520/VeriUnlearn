# Changelog

All notable changes to VeriUnlearn are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-08-16

First stable release. Phases 1–7 complete: foundation, datasets & training, privacy
auditor, surgical unlearning, verification & certificates, research benchmark suite, and
the enterprise platform layer. This release is the final-phase packaging: full
documentation, final lint pass, coverage measurement, release prep, and open-source
packaging.

### Added

- **Foundation (Phases 1–2)**: dataset ingestion (CSV/JSON/JSONL/TXT/PDF), SISA sharded
  training, JWT auth, model registry.
- **Privacy (Phases 3–4)**: PII detection, identity search + footprint analysis, impact
  analysis, surgical unlearning (records/chat/dataset scope; SISA/certified/influence
  methods), persisted deletion reports.
- **Verification (Phase 5)**: Merkle deletion proofs, RSA-signed certificates
  (JSON/PDF), 8-check verification engine, ZK-style commitments, optional blockchain
  anchoring.
- **Research (Phase 6)**: non-destructive 6-method benchmark, 4-family attack suite
  (MIA/inversion/extraction/poisoning), versioned experiments, research metrics,
  CSV/JSON/Excel + LaTeX exports.
- **Enterprise (Phase 7)**: five-role RBAC, admin portal, GDPR/DPDP compliance
  dashboards with persisted snapshots + exports, Prometheus metrics + Grafana dashboard,
  structured logging, in-app + SMTP notifications with retry, API keys with quotas and
  usage logs, system monitoring UI, analytics endpoints, Docker Compose prod stack
  (nginx/postgres/redis/qdrant/prometheus/grafana), GitHub Actions CI/CD.
- **Documentation**: complete guide set under `docs/` (developer, user, administrator,
  installation, configuration, troubleshooting, FAQ, glossary, best practices),
  publication-ready IEEE paper, academic project report, presentation outline, editable
  Mermaid diagrams, testing & performance reports, demo scripts, viva guide, resume
  materials, release notes, and completion summary.
- **Open-source packaging**: MIT license, code of conduct, contributing guide, security
  policy, issue/PR templates, changelog.
- **Load & stress testing**: `backend/scripts/load_test.py` — concurrency-ramp load test
  against the real app + `docs/load-test-report.md` (27 req/s single-client, sub-15 ms
  p50, zero errors; SQLite ceiling quantified at ≥25 concurrent).

### Changed

- **Lint cleanup**: removed 61 unused imports and 4 unused variables across backend and
  tests (no behavioural change; full suite re-verified).
- **Docs**: expanded `docs/api.md` (Phase 7 endpoints + privacy scan/reports/history and
  unlearning impact/history rows), `docs/deployment.md` (production stack), `README.md`
  (phase-7 deliverables link, badges).
- **Version alignment**: app now reports `1.0.0` (FastAPI metadata + `/health`) and the
  frontend package is `veriunlearn-frontend@1.0.0`, matching the release.
- **Verification pass (2026-08-17)**: re-ran the full suite — 65 passed, 78% coverage
  (5,324 statements), ruff `F`/`E9` clean, `next build` clean, fresh-DB migration chain
  verified (head `10a9fd591a22`, 31 tables, 5 roles/21 permissions seeded), both compose
  files validated with `docker compose config`.

### Fixed

- Stale API documentation (admin roles now reflect the 5-role matrix).

### Security

- Security headers, CSRF origin check, rate limiting, API-key hashing, RBAC enforcement,
  Bandit + npm audit CI — see `docs/phase7-deliverables.md` §13.

### Known issues

- Certified removal is exact for convex models only.
- MIA is confidence-based (no shadow models); recovery rate fixed at 0.0.
- Optional backends (LoRA/GPU, blockchain) are dependency-gated and lack CI coverage.
- No automated frontend unit tests (build type-check only).

See `docs/release-1.0.0.md` for migration notes, the compatibility matrix, and the
Phase 8 roadmap.
