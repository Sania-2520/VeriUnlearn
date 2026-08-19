## Summary

<!-- What problem does this PR solve? One or two sentences. Link the issue if any. -->

## Type of change

- [ ] Bug fix (non-breaking)
- [ ] New feature (additive, Phase 8 roadmap item)
- [ ] Documentation
- [ ] Tooling / CI / tests
- [ ] Performance / refactor (no behaviour change)

## Checklist

- [ ] Backwards compatible — no existing API/endpoint behaviour changed
- [ ] Tests added/updated and full suite passes: `cd backend && python -m pytest tests -q`
- [ ] Lint clean: `ruff check app tests --select F,E9`
- [ ] Frontend build passes: `cd frontend && npm run build` (if frontend touched)
- [ ] Docs updated (`docs/` guides + `docs/api.md` where relevant)
- [ ] No secrets, no debug leftovers, no unrelated changes

## Evidence

<!-- Test output, screenshots, or measured numbers (see docs/performance-report.md). -->

## Migration notes

<!-- List any new additive migrations; state clearly that no applied migration was edited. -->
