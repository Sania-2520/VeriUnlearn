# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] — 2026-07-27

### Added

#### Phase 3 — Cryptographic Verification

- **5 verification strategies**: Hash Verification, Merkle Verification, Influence Verification, Membership Inference Attack, Forget Quality
- **Ed25519 digital signatures** via PyNaCl (`nacl`) for certificate and proof artifact signing
- **SHA-256 Merkle tree** implementation for batch inclusion proofs
- **zk-SNARK proof service** (Groth16-style prototype) with generate/verify endpoints
- **Deletion certificates**: X.509-style JSON certificates with embedded public key, Merkle root, Ed25519 signature, and QR code for offline verification
- **Trust score computation**: Weighted composite (0–1) from 5 verification strategy outputs
- **Blockchain anchoring service**: SHA-256 Merkle root over audit chain, anchored via simulated blockchain every 6 hours
- **Proof verification logging**: Method tracking (api, cli, blockchain, manual) with full audit trail

#### Phase 4 — Governance & Compliance

- **Consent lifecycle**: Grant, withdraw, expire, update with immutable `ConsentHistory` trail
- **Policy engine**: Configurable policies with GDPR/CCPA/DPDP regulation templates, violation detection
- **Compliance workflow engine**: Orchestrated compliance processes with `ComplianceWorkflow` and `ComplianceReport`
- **Multi-level approval system**: Escalation chains with configurable timeouts, approve/reject actions
- **Risk assessment service**: AI model risk scoring (privacy, compliance, exposure)
- **Governance scoring**: Aggregate `GovernanceScore` computation
- **Data lineage**: Full traceability from dataset → model → deletion → certificate
- **Retention policy enforcement**: Automated data purging based on configured policies
- **In-app notifications**: Event-driven alerts for governance events
- **Compliance webhooks**: HMAC-SHA256 signed webhook dispatch with auto-retry and auto-disable

#### Phase 5 — MLOps & Platform Engineering

- **Experiment tracking**: MLflow-style experiment runs with metrics, artifacts, and parameter logging
- **Pipeline engine**: Reusable pipeline definitions with sequential/parallel step dependencies
- **Model serving**: Health-checked inference endpoints, canary deployments, A/B testing
- **Prometheus metrics tracking**: Request latency, error rates, job durations, queue depths
- **Observability middleware**: Request tracing with duration logging and status code tracking
- **Operational dashboard**: System health, service status, resource utilization views

#### Phase 6 — Research & Benchmark Suite

- **Algorithm registry**: 7 built-in algorithms with dynamic class loading, seeding, and plugin support
- **Automated benchmarking**: Multi-trial evaluation across datasets with configurable parameters
- **Privacy attack simulation**: Membership inference attack (MIA) with before/after comparison
- **Algorithm leaderboards**: Ranked comparison across all benchmark runs
- **Cross-algorithm comparison**: Side-by-side analysis with statistical significance (paired t-test, Wilcoxon, Cohen's d)
- **Publication-ready reports**: IEEE-paper-quality markdown with LaTeX table export
- **Reproducibility packages**: Config fingerprint (SHA-256), hardware snapshot, git info, package versions
- **Plugin system**: 8 plugin types (Algorithm, Metric, Report, Dashboard, Verification, Policy, DataSource, Visualization) with `importlib` dynamic loading

#### Explainable AI

- **SHAP, LIME, Integrated Gradients** feature attribution
- **Gradient/Occlusion/Perturbation** attribution methods
- **Counterfactual explanations**: What-if analysis for model predictions
- **Embedding visualizations**: PCA and UMAP dimensionality reduction
- **Privacy heatmaps**: Per-feature privacy risk visualization
- **Model drift detection**: Distribution shift monitoring across retraining cycles
- **Algorithm reasoning**: Human-readable explanations for algorithm selection decisions

#### Enterprise ML Engine

- **LoRA adapter lifecycle**: Registry, versioning, routing, rollback, canary deployments
- **Continual learning**: Elastic Weight Consolidation (EWC), replay buffer, drift detection
- **Knowledge distillation**: Teacher-student model compression
- **GPU scheduler**: Async training jobs with queue management
- **Automatic checkpointing**: Pre-unlearning model snapshots for rollback safety
- **Model registry**: Version management with integrity hashes

#### Backend API Routes

- **v2 Engine routers** (5): `unlearning_engine`, `verification_engine`, `governance_engine`, `mlops_engine`, `research_engine`
- **Governance endpoints**: Consents CRUD, policies evaluate, approvals workflow, risk assessment, lineage queries
- **Verification endpoints**: Proof generate/verify, certificate generate/verify, zk-SNARK generate/verify, trust score query
- **Benchmark endpoints**: Run, summary, results, leaderboard, CSV/JSON export, comparison
- **Adapter endpoints**: Register, activate, deactivate, rollback, canary setup/promote, health, latency
- **Continual learning endpoints**: Stats, tasks, samples, EWC, replay buffer, drift alerts
- **Explainability endpoints**: Samples, features, compare, privacy-heatmap, drift

#### Enterprise Testing

- **Total test suite**: 753 tests (backend 237, ML Engine 434, evaluation 76, frontend 6)
- **Load/throughput tests**: Concurrent request handling, response time benchmarks
- **API integration tests**: End-to-end workflows for all v1 and v2 routers
- **Security tests**: Authentication bypass, path traversal, CORS, rate limiting
- **Governance tests**: Consent lifecycle, policy evaluation, approval workflows
- **Verification tests**: Merkle tree construction, Ed25519 signing, proof verification

#### Documentation

- **Architecture Guide**: 4-layer architecture, component descriptions, data flow, technology decisions
- **Security Guide**: Threat model, authentication, API security, cryptography, compliance mapping, incident response
- **Troubleshooting Guide**: Installation, Docker, database, ML Engine, performance, certificate issues
- **API Reference**: Complete endpoint documentation with request/response schemas and error codes
- **Benchmark Guide**: How to run benchmarks, interpret results, add algorithms/datasets, reproduce publications
- **FAQ**: 30+ questions covering unlearning, proofs, compliance, datasets, performance
- **Machine Unlearning Guide**: Algorithm details, pipeline walkthrough, rollback safety
- **Verification Guide**: Cryptographic primitives, proof flow, trust score computation
- **Governance Guide**: Consent management, policy engine, approvals, risk, lineage
- **Contributing Guide**: Full development workflow, code standards, CI/CD, security guidelines
- **Deployment Guide**: Docker, Helm, Terraform for AWS EKS, production considerations
- **Developer Guide**: Local setup, project structure, testing, adding new modules
- **Architecture Decision Records**: 15 ADRs covering all key technical decisions
- **Mermaid diagrams**: Context, sequence, ER, and folder structure diagrams
- **IEEE paper structure**: Research documentation template

#### Infrastructure

- **Helm chart**: Kubernetes deployment with configurable resources, replicas, secrets
- **Terraform**: AWS EKS provisioning module with VPC, node groups, IAM roles
- **Docker Compose**: 14 services with health checks, dependency ordering, resource limits
- **Nginx**: Reverse proxy with TLS termination, security headers, rate limiting (edge)
- **Monitoring stack**: Prometheus, Grafana, Loki, Alertmanager with Slack/PagerDuty routing
- **CI/CD pipelines**: GitHub Actions for lint, typecheck, test, build, security scan (Trivy + Gitleaks)
- **SBOM generation**: CycloneDX-format Software Bill of Materials for container images
- **Demo seed data**: Scripts for generating sample datasets, models, deletion requests, and certificates
- **Backup/restore scripts**: Automated `pg_dump` with S3-compatible storage

#### Security

- **RBAC with 8 roles**: admin, user, ml_engineer, researcher, compliance_officer, legal_team, auditor, viewer
- **24 fine-grained permissions** across all resource types
- **MFA (TOTP)**: Time-based one-time password authentication
- **API key management**: `vu_` prefix, SHA-384 hashed storage, scoped permissions, expiry
- **JWT with refresh tokens**: 15-minute access + 7-day refresh token rotation
- **Rate limiting**: Redis sliding window (5 req/s auth, 30 req/s API, 100 req/s tenant)
- **Security headers**: HSTS, X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, CSP, Referrer-Policy
- **Input validation**: Pydantic v2 on all endpoints, XSS/SQL injection pattern detection on ML Engine
- **Audit hash chain**: SHA-256 chained immutable audit trail with blockchain anchoring
- **Secret validation**: Placeholder key rejection in production mode
- **CORS restriction**: Origin whitelisting per environment
- **Vulnerability reporting**: security@veriunlearn.com with 24h acknowledgment

### Fixed

#### Security Fixes
- Fixed authentication bypass vulnerability in JWT validation middleware
- Patched path traversal vulnerability in file upload endpoints (sanitized all file paths)
- Fixed CORS misconfiguration allowing overly permissive origins in default config
- Removed 18 instances of `__import__()` abuse — replaced with proper import statements
- Fixed 17 bare `except:` blocks — replaced with specific exception handling
- Hardened JWT token validation (expiration, signature, issuer checks)
- Enforced HTTPS redirect and secure cookie flags in production mode
- Added rate limiting to auth endpoints to prevent brute-force attacks

#### Database & ORM Fixes
- Fixed 14 transaction management issues (commit → flush conversions)
- Added 30+ database indexes for foreign key columns
- Fixed SQLAlchemy 2.0 deprecation warnings across all models
- Corrected async session handling in Celery tasks
- Fixed connection pool exhaustion under concurrent load

#### Deployment Fixes
- Added Docker health checks for all services in docker-compose.yml
- Fixed secrets management for production environment variables
- Corrected Helm chart values for resource limits and replica counts
- Fixed Nginx reverse-proxy configuration for WebSocket streaming endpoints
- Added proper service dependency ordering with `service_healthy` conditions
- Fixed volume mount permissions for PostgreSQL and MinIO

#### Testing Fixes
- Fixed flaky tests due to shared state between test cases
- Added proper test isolation with database transaction rollback
- Fixed load test timeouts under high concurrency
- Corrected mock expectations for external service clients

#### Documentation Fixes
- Fixed broken cross-references between documentation files
- Corrected API endpoint URLs in API reference (mismatched with implementation)
- Fixed outdated benchmark results with current reference numbers
- Corrected environment variable names in deployment guide

### Changed

- **Infrastructure**: Migrated from simple Docker setup to full Helm chart + Terraform for AWS EKS
- **RBAC**: Expanded from 5 roles to 8 roles with 24 fine-grained permissions
- **API**: Added v2 engine routers (5) alongside existing v1 routers (17) — both active
- **Testing**: Expanded from ~170 tests to 753 tests across 4 test suites
- **Documentation**: Expanded from 15 to 90+ documentation files
- **Event system**: Expanded from 15 to 44 named events across 4 domains
- **Services**: Expanded from ~20 to 55+ domain services
- **Database models**: Expanded from ~15 to 47+ SQLAlchemy entities
- **Docker Compose**: Expanded from 6 to 14 services (added ML Engine, monitoring stack, Qdrant)
- **Benchmarking architecture**: Replaced simple comparison scripts with full BenchmarkService + LeaderboardService + ComparisonService

### Deprecated

- v1 benchmark endpoints — replaced by v2 `research_engine` endpoints (still functional)
- Direct ML Engine benchmark calls — use backend API proxy for consistency

---

## Development (Pre-Release)

### Security Fixes
- Fixed authentication bypass vulnerability in middleware chain
- Patched path traversal in file upload endpoints
- Hardened JWT token validation and refresh flow
- Added input sanitization across all API endpoints
- Enforced HTTPS redirect and secure cookie flags in production

### Test Coverage Improvements
- Expanded test suite to 753 tests (backend, ml-engine, frontend)
- Added integration tests for adapter lifecycle (register, activate, rollback, canary)
- Added load/throughput and concurrent request test suites
- Improved mock coverage for external services (Qdrant, MinIO, RabbitMQ)
- Added regression tests for previously reported bugs

### Documentation Improvements
- Added 90+ documentation files across architecture, API, security, and user guides
- Expanded developer onboarding guide with Docker-only workflow
- Added API contract documentation for all REST endpoints
- Created troubleshooting guide and FAQ
- Improved inline code documentation across Python and TypeScript packages

### Deployment Fixes
- Added Docker healthchecks for all services in docker-compose.yml
- Fixed secrets management for production environment variables
- Corrected Helm chart values for resource limits and replicas
- Updated CI/CD pipeline to run security scans (Trivy + Gitleaks) on every push
- Fixed Nginx reverse-proxy configuration for WebSocket endpoints

### UX Improvements
- Added loading state indicators across all frontend views
- Implemented React error boundaries for graceful failure handling
- Improved form validation feedback with inline error messages
- Added toast notifications for async operation outcomes
- Enhanced dark mode support across dashboard components

---

## Migration Guide (v0.x → v1.0.0)

### Breaking Changes

1. **Environment variables**: `JWT_SECRET` renamed to `JWT_SECRET_KEY`. Update `.env` accordingly.
2. **API key format**: New keys use `vu_` prefix. Re-generate any existing keys.
3. **Database migrations**: Run `alembic upgrade head` — 30+ new tables added.
4. **RBAC roles**: Roles are now more granular. Existing users mapped to closest roles.
5. **Docker Compose**: Services reorganized. Run `docker compose down --volumes && docker compose up -d` for clean state.

### Upgrade Steps

1. Pull latest: `git pull origin main`
2. Update `.env` with new variables from `.env.example`
3. Rebuild images: `docker compose build --no-cache`
4. Start services: `docker compose up -d`
5. Run migrations: `docker compose exec backend alembic upgrade head`
6. Verify health: `curl http://localhost:8000/health`
7. Re-seed demo data (optional): `python scripts/generate_demo_assets.py`

---

## [Unreleased]

### Planned

- Post-quantum cryptography integration
- Production zk-SNARK trusted setup
- Public blockchain anchoring (Ethereum, Polygon)
- Federated machine unlearning across organizations
- Streaming/real-time unlearning
- Multi-tenant isolation with per-tenant databases
- AI Governance Copilot with natural-language queries
- End-to-end CI/CD pipeline in GitHub Actions
- Frontend test expansion (currently 6 smoke tests)
- Additional real-world dataset benchmarks (IMDB, AG News)

---

## Related Documents

- [Release Notes v1.0.0](docs/RELEASE_NOTES_v1.0.0.md) — Full feature descriptions and known limitations
- [Release Checklist](docs/RELEASE_CHECKLIST.md) — Release runbook
- [Future Roadmap](docs/FUTURE_ROADMAP.md) — Phases 7–12 research roadmap
