# Release Checklist & Runbook — VeriUnlearn

End-to-end runbook for cutting and shipping a VeriUnlearn release across
**Docker images**, the **Helm chart**, and **GitHub Releases**. Work the steps
in order; each step must be complete (or explicitly waived) before the next.

> Channels & artifacts: stable git tag `vX.Y.Z`, `latest` (and pinned
> `vX.Y.Z`) container images, and a matching Helm chart version. See
> [docs/RELEASE.md](RELEASE.md).

---

## 0. Pre-Conditions

- [ ] You are on `main` and it is green in CI (`.github/workflows/ci.yml`).
- [ ] You have maintainer rights (tagging + image push).
- [ ] Release notes drafted in `CHANGELOG.md` under a `## [X.Y.Z]` header.
- [ ] No open blocker issues milestoned for this release.

## 1. Version Bump

- [ ] Bump version in `packages/backend/app/core/config.py`
- [ ] Bump version in `packages/ml-engine/api.py`
- [ ] Bump Helm `Chart.yaml` `version:` and `appVersion:` to match `vX.Y.Z`
- [ ] Commit the version bump: `git commit -m "chore(release): vX.Y.Z"`

## 2. CHANGELOG

- [ ] `CHANGELOG.md` has a dated `## [X.Y.Z] — YYYY-MM-DD` section
- [ ] Added / Fixed / Changed / Security groups populated from merged PRs
- [ ] Migration notes, breaking changes, and upgrade steps called out

## 3. Tag the Release

- [ ] `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
- [ ] `git push origin main --tags`
- [ ] Confirm the tag triggers (or is picked up by) the release pipeline

## 4. CI & Security Gates

- [ ] CI is green for the tagged commit (lint, type-check, backend + ML engine
      + frontend tests, coverage ≥ 88%)
- [ ] **Trivy** image/filesystem scan clean (no `HIGH`/`CRITICAL` unapproved)
- [ ] **Gitleaks** secret scan clean
- [ ] Dependency / SCA scan reviewed (no new critical CVEs)

## 5. Build & Push Images

- [ ] Build backend image: `veriunlearn/backend:vX.Y.Z` and `:latest`
- [ ] Build frontend image: `veriunlearn/frontend:vX.Y.Z` and `:latest`
- [ ] Push both tags to the registry (`DOCKER_REGISTRY` in GH secrets)
- [ ] Verify images pulled and `docker inspect` shows correct labels/digest

## 6. SBOM

- [ ] Generate SBOM (e.g., `syft` / Trivy SBOM) for each image
- [ ] Attach SBOM to the GitHub Release (or store in registry attestation)
- [ ] Record image digests (`docker images --digests`) in release notes

## 7. Create GitHub Release

- [ ] Draft release from tag `vX.Y.Z`
- [ ] Title: `VeriUnlearn vX.Y.Z`
- [ ] Body: copy the CHANGELOG section + upgrade/rollback notes
- [ ] Attach SBOMs, Helm chart `.tgz`, and any release artifacts
- [ ] Publish (or mark Pre-release if canary-first)

## 8. Deploy to Staging (Helm)

- [ ] `helm upgrade --install veriunlearn infra/k8s/helm/veriunlearn \
        --namespace veriunlearn-staging --create-namespace \
        --set image.tag=vX.Y.Z --set secrets.jwtSecret=$(openssl rand -hex 32)`
- [ ] `kubectl -n veriunlearn-staging rollout status deploy/...`
- [ ] Run [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) smoke tests on
      staging
- [ ] Verify health: `curl https://staging.<domain>/health` (backend + ML)

## 9. Canary to Production

- [ ] Promote image `vX.Y.Z` to production namespace (weight 10–20% traffic
      if ingress supports canary; otherwise a single replica first)
- [ ] Watch error rate, p95 latency, and unlearning-job success for 15–30 min
- [ ] If metrics nominal, complete rollout: 100% `image.tag=vX.Y.Z`
- [ ] Otherwise: `helm rollback veriunlearn <prev-revision>` and restore DB

## 10. Post-Deploy Verification (Production)

- [ ] All pods `Ready`; readiness/liveness probes green
- [ ] Backend `/health` and ML Engine `/health` return 200 over HTTPS
- [ ] Prometheus targets `up`; Grafana dashboards populated
- [ ] One live deletion request + proof generation succeeds end-to-end
- [ ] Audit log hash chain intact (no gaps)
- [ ] Alertmanager test alert acknowledged

## 11. Communications

- [ ] Announce in release channel (Slack/PagerDuty summary)
- [ ] Update docs site / README badges if version-dependent
- [ ] Close the milestone; thank contributors
- [ ] Tweet/blog post if part of public launch (judged competition)

---

## Rollback Quick-Reference

```bash
# Helm
helm rollback veriunlearn <PREV_REVISION> -n veriunlearn

# Compose (pin prior tag)
docker compose up -d --no-deps backend frontend ml-engine

# Database (if migration applied)
docker compose exec backend alembic downgrade <PREV>
# or restore pre-deploy pg_dump
```

---

_See also: [docs/RELEASE.md](RELEASE.md),
[docs/DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md),
[docs/production-deployment.md](production-deployment.md)._
