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
