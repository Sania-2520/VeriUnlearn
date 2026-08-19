# VeriUnlearn — Release Notes v1.0.0

**Release date:** 2026-08-16
**Status:** First stable release — Phases 1–7 complete; final packaging, documentation,
lint pass, and testing evidence included.
**License:** MIT

---

## What's new in 1.0.0

The 1.0.0 release packages the completed platform: verifiable machine unlearning
(SISA / certified / influence), Merkle-RSA-audit deletion evidence, an 8-check
verification engine, a reproducible 6-method benchmark + 4-family attack suite, and the
enterprise layer (RBAC, admin, compliance dashboards, monitoring, notifications, API
keys, analytics, CI/CD). The release pass adds:

- Full documentation set under `docs/` (guides, IEEE paper, project report, presentation
  outline, diagrams, testing & performance reports, demo scripts, viva guide, resume
  materials, completion summary).
- Lint cleanup: 61 unused imports + 4 unused variables removed (no behaviour change).
- Measured evidence: 65 tests / 78% coverage; API p50 ≤ 14 ms; benchmark numbers recorded.
- Load & stress test: `backend/scripts/load_test.py` + `docs/load-test-report.md`
  (27 req/s single-client, sub-15 ms p50, zero errors; SQLite ceiling at ≥25 concurrent).
- Final verification pass (2026-08-17): suite re-run green, migration chain + compose
  configs validated, app version aligned to 1.0.0.
- Open-source packaging: MIT license, code of conduct, contributing + security policies,
  issue/PR templates, changelog.

See [`CHANGELOG.md`](../CHANGELOG.md) for the full change list.

## Migration notes (from any prior phase build)

1. **Always back up** the DB and `backend/keys/` (RSA keypair) before upgrading.
2. **Run migrations**: `cd backend && python -m alembic upgrade head`
   (prod containers do this automatically on start). All migrations are additive — no
   applied migration was edited; the chain is `bd3d39814aa2 → 97fe9443fb40 →
   203c60186717 → e3bb87e588e3 → 10a9fd591a22`.
3. **New required env vars** (see `backend/.env.example`): `SECRET_KEY`, and in production
   `POSTGRES_PASSWORD`, `METRICS_TOKEN`, `CORS_ORIGINS`, `EMAIL_PROVIDER`/`SMTP_*`.
   The prod compose fails fast if `SECRET_KEY`/`POSTGRES_PASSWORD` are missing.
4. **RBAC seeding**: `alembic upgrade head` seeds the 5 roles + permission rows; existing
   `admin/operator/auditor` accounts map onto the matrix automatically (legacy map in
   `app/core/rbac.py`).
5. **Frontend**: rebuild with `NEXT_PUBLIC_API_URL` set to your backend origin.

## Known issues

1. Certified removal is exact for convex (linear/logistic) models only.
2. MIA is confidence-based (no shadow-model training); recovery rate is fixed at 0.0
   pending an embedding-extraction harness.
3. Optional backends (LoRA/GPU, blockchain) are dependency-gated and not exercised in CI.
4. No automated frontend unit tests — CI gates on `next build` type-check.
5. In-memory benchmark is memory-bound at large shard/eval sizes (eval cap 2,000).
6. GPU metrics and multi-node aggregation are not yet collected.
7. Dev SQLite is single-process; use the `full`/prod profile (PostgreSQL + Redis) for
   multi-instance rate limiting.

## Compatibility matrix

| Component | Version | Notes |
|---|---|---|
| Python | 3.12 (CI), 3.13 (dev-verified) | |
| Node.js | 20 / 22 | Next.js 15 |
| FastAPI | 0.115.6 | pinned |
| SQLAlchemy | 2.0.36 | async |
| Next.js | 15.x | App Router |
| PostgreSQL | 16 | prod compose |
| Redis | 7 | prod compose |
| Qdrant | latest | optional vector store |
| Prometheus | 2.53 | prod compose |
| Grafana | 11.1 | prod compose |
| Docker Compose | v2 | dev `core`/`full`, prod profile |

## Roadmap (Phase 8 — post-1.0.0)

1. GPU-accelerated deep-model unlearning; certified-removal extension to non-convex models.
2. Shadow-model MIA auditing; embedding-extraction harness (fill `recovery_rate`).
3. Background workers (Celery/ARQ) for deletion/verification/benchmark jobs + queue metrics.
4. SSO/OIDC; multi-tenancy with row-level access.
5. Alerting (Prometheus rules → Grafana/webhook); GPU + vector-store telemetry.
6. Compliance evidence bundles (signed zip of snapshot + audit excerpt + certificates).
7. Frontend unit tests (Vitest + Testing Library); formal load tests (locust) in CI.
8. API gateway features: IP allowlists, granular scopes, billing tiers.

## GitHub release package checklist

- [x] Source tarball (tag `v1.0.0`)
- [x] `README.md` (badges, quick start, docs index)
- [x] `LICENSE`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `SECURITY.md`
- [x] `CHANGELOG.md` + these release notes
- [x] `docs/` full guide set
- [x] Dockerfiles + compose files (dev/prod) + `deploy/` (nginx/prometheus/grafana)
- [x] CI/CD workflows (test, benchmark, security, deploy)
- [x] Issue + PR templates
- [x] Migration chain verified head-to-head
