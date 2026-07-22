# Release Index & Channels — VeriUnlearn

This document explains how VeriUnlearn is packaged and released, and how to
cut a release. For the step-by-step procedure, see
[RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md). For deployment verification, see
[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md).

---

## Release Channels

| Channel | Artifact | Purpose |
|---------|----------|---------|
| **Stable tag** | Git tag `vX.Y.Z` | Immutable, auditable source release; basis for all other artifacts |
| **Container images** | `veriunlearn/backend:vX.Y.Z`, `veriunlearn/frontend:vX.Y.Z` | Reproducible runtime for Docker Compose & Kubernetes |
| **`latest` image** | `.../backend:latest`, `.../frontend:latest` | Floating pointer to the newest stable build; **not** for production pinning |
| **Helm chart** | `infra/k8s/helm/veriunlearn` with `Chart.yaml` `version` / `appVersion` | Kubernetes deployment; chart version tracks the app `vX.Y.Z` |

### Versioning policy

- Semantic Versioning (`MAJOR.MINOR.PATCH`).
- `PATCH` — fixes and security updates; backward-compatible.
- `MINOR` — new features, backward-compatible API changes.
- `MAJOR` — breaking changes (API, crypto formats, storage layout).
- The Helm chart `appVersion` must equal the application `vX.Y.Z`.

### Image tagging rules

- Every stable tag produces **two** image tags: the immutable `vX.Y.Z` and a
  refreshed `latest`.
- Production deployments **must** pin `image.tag=vX.Y.Z` (or the image digest).
- Never run `latest` in production.

---

## How to Cut a Release

1. Ensure `main` is green and CHANGELOG has a dated `## [X.Y.Z]` section.
2. Bump versions in `config.py`, `api.py`, and Helm `Chart.yaml`
   ([RELEASE_CHECKLIST.md §1](RELEASE_CHECKLIST.md)).
3. `git tag -a vX.Y.Z -m "Release vX.Y.Z" && git push origin main --tags`.
4. Pass security gates: Trivy + Gitleaks clean, CI green.
5. Build & push images (`vX.Y.Z` + `latest`); generate SBOMs.
6. Create the GitHub Release from the tag; attach SBOMs + Helm chart.
7. Deploy to **staging** via Helm; run smoke tests.
8. **Canary** to production, then full rollout once metrics are nominal.
9. Post-deploy verification + communications.

---

## Reference Links

- [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) — full runbook (ordered steps)
- [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) — pre/post-deploy checks
- [production-deployment.md](production-deployment.md) — infra & Helm details
- [CHANGELOG.md](../CHANGELOG.md) — shipped changes
- [SECURITY.md](../SECURITY.md) — vulnerability reporting

---

_License: Apache 2.0 — see [LICENSE](../LICENSE)._
