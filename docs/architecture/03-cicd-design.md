# VeriUnlearn — CI/CD Pipeline Design

## Version 1.0.0 — Enterprise Delivery

---

## 1. Pipeline Philosophy

- **Shift Left**: Security, quality, and performance testing early
- **Immutable Artifacts**: Every build produces versioned, signed artifacts
- **Progressive Delivery**: Canary → Staging → Production
- **Observability**: Every deployment tracked and monitored
- **Self-Service**: Teams can deploy independently within guardrails

---

## 2. GitHub Actions Workflows

### 2.1 CI Pipeline (`.github/workflows/ci.yml`)

```yaml
name: CI Pipeline
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  lint-typecheck:
    name: Lint & Type Check
    strategy:
      matrix:
        package: [backend, frontend, ml-engine]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup ${{ matrix.package }}
        uses: ./.github/actions/setup-${{ matrix.package }}
      - name: Lint
        run: make lint-${{ matrix.package }}
      - name: Type Check
        run: make typecheck-${{ matrix.package }}

  security-scan:
    name: Security Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: SAST (Semgrep)
        uses: semgrep/semgrep-action@v1
        with:
          config: p/default
      - name: Secrets Scan (Gitleaks)
        uses: gitleaks/gitleaks-action@v2
      - name: Dependency Scan (Snyk)
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}

  test:
    name: Test
    needs: [lint-typecheck, security-scan]
    strategy:
      matrix:
        package: [backend, frontend, ml-engine]
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: veriunlearn
          POSTGRES_PASSWORD: test
          POSTGRES_DB: veriunlearn_test
        ports: [5432:5432]
      redis:
        image: redis:7-alpine
        ports: [6379:6379]
    steps:
      - uses: actions/checkout@v4
      - name: Setup ${{ matrix.package }}
        uses: ./.github/actions/setup-${{ matrix.package }}
      - name: Unit Tests
        run: make test-${{ matrix.package }}-unit
      - name: Integration Tests
        run: make test-${{ matrix.package }}-integration
      - name: Upload Coverage
        uses: codecov/codecov-action@v3

  build:
    name: Build
    needs: [test]
    strategy:
      matrix:
        package: [backend, frontend, ml-engine]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      - name: Login to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Build & Push
        uses: docker/build-push-action@v5
        with:
          context: ./packages/${{ matrix.package }}
          push: ${{ github.event_name == 'push' }}
          tags: |
            ghcr.io/${{ github.repository }}/${{ matrix.package }}:${{ github.sha }}
            ghcr.io/${{ github.repository }}/${{ matrix.package }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
      - name: Container Scan (Trivy)
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ghcr.io/${{ github.repository }}/${{ matrix.package }}:${{ github.sha }}
          format: sarif
          output: trivy-results.sarif
      - name: Upload Scan Results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: trivy-results.sarif

  performance-test:
    name: Performance Test
    needs: [build]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy Test Environment
        run: make deploy-staging
      - name: Run k6 Load Tests
        run: make test-performance
      - name: Upload Results
        uses: actions/upload-artifact@v3
        with:
          name: performance-results
          path: test-results/performance/
```

### 2.2 CD Pipeline (`.github/workflows/cd.yml`)

```yaml
name: CD Pipeline
on:
  push:
    tags: [v*.*.*]
  workflow_dispatch:
    inputs:
      environment:
        description: 'Deploy environment'
        required: true
        default: 'staging'
        type: choice
        options: [staging, production]

jobs:
  deploy-staging:
    name: Deploy to Staging
    if: github.event_name == 'push' || github.event.inputs.environment == 'staging'
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - name: Configure kubectl
        uses: azure/setup-kubectl@v3
      - name: Deploy Helm
        run: |
          helm upgrade --install veriunlearn ./infra/kubernetes/helm \
            --namespace veriunlearn-staging \
            --values ./infra/kubernetes/helm/values/staging.yaml \
            --set image.tag=${{ github.sha }} \
            --wait --timeout 10m
      - name: Smoke Tests
        run: make test-smoke-staging
      - name: Integration Tests
        run: make test-integration-staging

  deploy-production:
    name: Deploy to Production
    needs: [deploy-staging]
    if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      - name: Deploy Canary (10%)
        run: |
          helm upgrade --install veriunlearn ./infra/kubernetes/helm \
            --namespace veriunlearn-production \
            --values ./infra/kubernetes/helm/values/production.yaml \
            --set canary.enabled=true \
            --set canary.weight=10 \
            --set image.tag=${{ github.sha }} \
            --wait --timeout 10m
      - name: Monitor Canary (15 min)
        run: sleep 900 && make verify-canary-health
      - name: Full Rollout
        run: |
          helm upgrade --install veriunlearn ./infra/kubernetes/helm \
            --namespace veriunlearn-production \
            --values ./infra/kubernetes/helm/values/production.yaml \
            --set image.tag=${{ github.sha }} \
            --wait --timeout 10m
      - name: Post-Deploy Verification
        run: make test-smoke-production
      - name: Notify
        uses: slackapi/slack-github-action@v1
        with:
          payload: '{"text": "VeriUnlearn v${{ github.ref_name }} deployed to production"}'
```

### 2.3 Security Pipeline (`.github/workflows/security-scan.yml`)

```yaml
name: Security Scan
on:
  schedule:
    - cron: '0 6 * * 1'  # Every Monday 06:00 UTC
  workflow_dispatch:

jobs:
  full-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Full SAST Scan
        uses: semgrep/semgrep-action@v1
        with:
          config: >-
            p/default p/security-audit p/secrets p/owasp-top-ten
      - name: DAST Scan
        run: |
          docker run --rm -v $(pwd):/zap/wrk:rw \
            ghcr.io/zaproxy/zaproxy:stable \
            zap-full-scan.py -t ${{ secrets.STAGING_URL }} \
            -r zap-report.html
      - name: Dependency Audit
        run: make audit-dependencies
      - name: License Check
        run: make check-licenses
      - name: Upload Report
        uses: actions/upload-artifact@v3
        with:
          name: security-report
          path: |
            semgrep-results.sarif
            zap-report.html
            dependency-audit.json
```

---

## 3. Build & Artifact Strategy

### 3.1 Docker Images

```yaml
Images:
  - ghcr.io/veriunlearn/backend:     {sha}  {latest}  {version}
  - ghcr.io/veriunlearn/frontend:    {sha}  {latest}  {version}
  - ghcr.io/veriunlearn/ml-engine:   {sha}  {latest}  {version}
  - ghcr.io/veriunlearn/celery-worker: {sha}  {latest}  {version}

Base Images:
  - python:3.12-slim  (backend, ml-engine)
  - node:22-alpine     (frontend)

Multi-stage builds with distroless runtime images.
```

### 3.2 Artifact Retention

```
- Docker images: 90 days (immutable by digest)
- Build artifacts: 30 days
- Test reports: 90 days
- Security scan results: 1 year
- Deployment logs: 1 year
```

---

## 4. Environment Strategy

| Environment | Purpose | Deploy Trigger | Slots |
|-------------|---------|----------------|-------|
| Development | Local dev, feature testing | Manual | 1 per dev |
| Review | PR preview environments | PR created | Ephemeral |
| Staging | Integration, pre-prod testing | Push to develop | 1 |
| Canary | 10% traffic validation | Tag push | 1 |
| Production | Live traffic | Tag push (after staging) | 2 (blue/green) |

---

## 5. Release Process

```
┌─────────┐   ┌──────────┐   ┌─────────┐   ┌──────────┐   ┌──────────┐
│ Feature │──▶│ Develop  │──▶│ Release │──▶│   Tag    │──▶│  Deploy  │
│ Branch  │   │  Branch  │   │  Branch │   │  v1.2.3  │   │  Production│
└─────────┘   └──────────┘   └─────────┘   └──────────┘   └──────────┘
     │              │              │               │             │
     │ CI: lint     │ CI: lint     │ CI: full      │ CD: build   │ CD: canary
     │     test     │     test     │     test      │     scan    │     rollout
     │     build    │     build    │     security  │     push    │     verify
     └──────────────┴───────       └───────        └──────        └──────
```

---

## 6. Quality Gates

| Gate | CI | Staging | Production |
|------|----|---------|------------|
| Lint passes | ✅ | ✅ | ✅ |
| Type checks | ✅ | ✅ | ✅ |
| Unit tests pass | ✅ | ✅ | ✅ |
| Integration tests pass | ✅ | ✅ | ✅ |
| Code coverage > 80% | ⚠️ | ✅ | ✅ |
| SAST scan (no critical) | ✅ | ✅ | ✅ |
| Dependency scan (no critical) | ✅ | ✅ | ✅ |
| Container scan (no critical) | ✅ | ✅ | ✅ |
| Performance tests (p95 < 1s) | — | ✅ | ✅ |
| Smoke tests pass | — | ✅ | ✅ |
| Security assessment | — | — | ✅ |

---

## 7. Local Development

```bash
# Clone and setup
git clone https://github.com/veriunlearn/veriunlearn.git
cd veriunlearn
make setup

# Start development environment
make dev

# Run tests
make test
make test-integration

# Build
make build
```

**Make targets:**
```
setup           - Install dependencies
dev             - Start dev environment (docker-compose)
dev-backend     - Start backend only
dev-frontend    - Start frontend only
lint            - Run all linters
typecheck       - Run all type checkers
test            - Run all tests
test-unit       - Run unit tests
test-integration - Run integration tests
test-performance - Run performance tests
build           - Build all packages
clean           - Clean build artifacts
```

---

## 8. Deployment Runbooks

### Rollback Procedure

```bash
# Immediate rollback to previous version
kubectl rollout undo deployment/veriunlearn-backend -n veriunlearn-production

# Rollback with Helm
helm rollback veriunlearn 1 -n veriunlearn-production

# Verify rollback
kubectl rollout status deployment/veriunlearn-backend -n veriunlearn-production
```

### Database Migration

```bash
# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Verify migration
alembic check
```

---

*This CI/CD design ensures repeatable, secure, and observable deployments. All changes follow this pipeline — no direct production access.*
