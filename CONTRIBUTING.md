# Contributing to VeriUnlearn

Thank you for your interest in contributing to **VeriUnlearn** — an
end-to-end framework for verifiable machine unlearning with cryptographic
proofs. This guide covers everything you need to set up the project, make
changes, and open a high-quality pull request.

For a deeper, topic-by-topic guide (architecture, API contracts, testing
strategy), see [docs/contributing.md](docs/contributing.md).

---

## 1. Quick Setup

The fastest way to get a working environment:

```bash
# 1. Clone the repository
git clone https://github.com/Sania-2520/VeriUnlearn.git
cd VeriUnlearn

# 2. Create your environment file from the example
cp .env.example .env

# 3. One-command setup (installs deps, starts infra, migrates, seeds demo data)
./scripts/setup.sh --seed

# OR, using the Makefile convenience target:
make setup
```

`make setup` / `./scripts/setup.sh --seed` will:

- Install backend (Python 3.12+) and frontend (Node.js) dependencies
- Bring up PostgreSQL, Redis, Qdrant, and MinIO via Docker Compose
- Apply Alembic database migrations
- Seed demo data so you can explore the UI immediately

### Docker-only development

If you prefer not to install toolchains locally, run the full stack in
containers:

```bash
docker compose up --build
```

This starts the backend (`:8000`), ML Engine (`:8001`), frontend (`:3000`),
and the monitoring stack (Grafana `:3001`, Prometheus `:9090`).

---

## 2. Branching & Pull Request Flow

We use a simple GitHub-flow model against the `main` branch.

1. **Fork** the repository and clone your fork.
2. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feat/short-description
   # or: fix/short-description, docs/short-description, chore/short-description
   ```
3. **Implement** your change, keeping the scope focused.
4. **Run lint and tests** (see below) and ensure they pass.
5. **Commit** using [Conventional Commits](#3-conventional-commits).
6. **Push** your branch and open a **Pull Request** against `main`.

### Conventional Commits

We follow the [Conventional Commits](https://www.conventionalcommits.org)
specification. Prefix your commit subject with a type:

| Type | Use for |
|------|---------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding or updating tests |
| `chore` | Build process, tooling, dependency bumps |
| `perf` | Performance improvement |
| `security` | Security hardening |

Example: `feat: add zk-SNARK verification endpoint for deletion proofs`

---

## 3. Lint & Test Commands

Run these before opening a PR.

### Backend (FastAPI / Python)

```bash
ruff check .
mypy app
pytest
```

### Frontend (Next.js / TypeScript)

```bash
cd packages/frontend
npm run lint
npm run typecheck
npm run build
```

### Whole repository

```bash
make lint
make test
```

CI (`.github/workflows/ci.yml`) runs the same lint, type-check, and test
suites for the backend, ML engine, and frontend on every push.

---

## 4. Code Style

- **Backend**: PEP 8, enforced by `ruff`; full type hints on all functions;
  async I/O via `asyncio`; OpenAPI docs updated for any API change.
- **ML Engine**: PyTorch 2.12+ + PEFT/LoRA; type-annotated; tests under
  `packages/ml-engine/tests/`.
- **Frontend**: ESLint + Prettier; TypeScript strict mode; Tailwind CSS +
  shadcn/ui component conventions.
- Keep API changes backward-compatible unless a major version bump is planned.
- No `TODO`/`FIXME` comments in committed code; handle errors with appropriate
  logging.

---

## 5. Security Guidelines

Security is a first-class concern for an unlearning/ compliance platform.

- **Never commit secrets or credentials.** Use `.env` (git-ignored) and
  reference variables from `.env.example`.
- The secret validator rejects placeholder keys in `APP_ENV=production`.
- **Run a secret scan** before every commit:
  ```bash
  gitleaks detect --source . --redact
  ```
  CI runs `gitleaks` (and `trivy`) on every push.
- Report vulnerabilities privately to **security@veriunlearn.com** — do **not**
  open public issues. See [SECURITY.md](SECURITY.md).
- Prefer Ed25519 / SHA-256 primitives already in `app/core/crypto`; do not
  introduce new cryptographic dependencies without discussion.

---

## 6. Sign-off (DCO) — Optional

We do **not** require a Developer Certificate of Origin sign-off. However, you
may add one if you prefer:

```bash
git commit -s -m "feat: ..."
```

This appends a `Signed-off-by:` line confirming you have the right to submit
the contribution under the project license (Apache 2.0).

---

## 7. Adding Dependencies

- **Backend**: `packages/backend/requirements.txt`
- **ML Engine**: `packages/ml-engine/requirements.txt`
- **Frontend**: `cd packages/frontend && npm install <package>`

Pin versions where possible and note the reason for new dependencies in the PR
description (licensing and supply-chain review apply).

---

## 8. Release Process

Contributors should not tag releases themselves. The maintainers handle
versioning per [docs/RELEASE.md](docs/RELEASE.md) and
[docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md). If your PR includes a
user-facing change, please add a `CHANGELOG.md` entry under `Unreleased`.

---

By contributing, you agree that your contributions will be licensed under the
Apache 2.0 License. See [LICENSE](LICENSE) and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
