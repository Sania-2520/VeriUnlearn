# Changelog

## [1.0.0] — 2026-07-13

### Added
- **Enterprise ML Engine**: Full LoRA adapter lifecycle (registry, versioning, routing, rollback, canary), continual learning (EWC, replay buffer, drift detection), knowledge distillation, GPU scheduler with async training jobs, automatic checkpointing
- **Benchmarking Platform**: 9 datasets (synthetic + real-world), 4 algorithms, automated metric calculation (accuracy, precision, recall, F1, latency, privacy leakage, MIA), CSV/JSON export, leaderboards
- **Explainable AI**: SHAP, LIME, Integrated Gradients, Gradient/Occlusion/Perturbation attribution, counterfactual explanations, embedding visualizations (PCA/UMAP), privacy heatmaps, drift detection
- **Backend API Routes**: Adapters (register, activate, rollback, canary, health, latency), Training (LoRA, distill, submit, jobs, GPU, queue, checkpoints), Continual Learning (stats, samples, drift, EWC, tasks), Benchmarks (run, summary, results, leaderboard, CSV export)
- **Enterprise Testing**: Load/throughput tests, concurrent request tests, response time benchmarks, API integration tests
- **Documentation**: Developer guide, frontend guide, security guide, user manual, troubleshooting guide, contributing guide, IEEE paper structure
- **Production Release**: Version 1.0.0, CHANGELOG, enhanced README with badges and screenshots, release notes

### Security
- Nginx security headers (HSTS, XSS, clickjacking, MIME-sniffing)
- IP-restricted /metrics endpoint
- Rate-limited auth endpoints
- Input validation on all ML engine endpoints
- Security audit and scan (Trivy + Gitleaks) in CI

### Infrastructure
- ML Engine service in docker-compose.yml
- Alertmanager with Slack/PagerDuty routing
- Prometheus alertmanager target wired up
- Makefile deploy/seed/benchmark/graphs targets
- Demo seed data script
- Updated CI/CD pipelines

## Development

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
- Added 69+ documentation files across architecture, API, security, and user guides
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
