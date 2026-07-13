# Contributing to VeriUnlearn

## How to Contribute

1. **Fork** the repository
2. **Create a feature branch**: `git checkout -b feat/my-feature`
3. **Implement** your changes following the code standards
4. **Run tests**: `make test` (backend + ML engine + frontend)
5. **Run lint**: `make lint`
6. **Commit**: `git commit -m "feat: description"`
7. **Push**: `git push origin feat/my-feature`
8. **Open a Pull Request** against `main`

## Development Workflow

```bash
# Setup
make install
docker compose up -d postgres redis qdrant minio
make db-migrate

# Development (3 terminals)
make dev-backend    # Terminal 1 - FastAPI
make dev-frontend   # Terminal 2 - Next.js
make worker         # Terminal 3 - Celery

# Before submitting PR
make lint
make test
make test-unit
```

## Code Review Checklist

- [ ] Follows PEP 8 / ESLint rules
- [ ] Type hints present on all functions
- [ ] Tests cover new functionality
- [ ] API changes are backward-compatible
- [ ] No TODO/FIXME comments
- [ ] Error handling with appropriate logging
- [ ] No hardcoded secrets or credentials
- [ ] Async implementation for I/O operations
- [ ] OpenAPI docs updated if API changed

## Adding Dependencies

- **Backend**: Add to `packages/backend/requirements.txt`
- **ML Engine**: Add to `packages/ml-engine/requirements.txt`
- **Frontend**: `cd packages/frontend && npm install <package>`

## Release Process

1. Update version in `packages/ml-engine/api.py` and `packages/backend/app/core/config.py`
2. Update `CHANGELOG.md`
3. Tag the release: `git tag v1.0.0 && git push origin v1.0.0`
4. Create GitHub Release with release notes
