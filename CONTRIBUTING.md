# Contributing to VeriUnlearn

Thanks for contributing! This project values: additive changes, backwards compatibility,
documented evidence, and reproducible science. Please read this guide before opening an
issue or pull request.

## Code of conduct

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

## How to contribute

1. **Discuss first** — open an issue for non-trivial changes before writing code
   (bug reports, feature requests, docs, research results).
2. **Fork & branch** — work on a descriptively named branch (`fix/merkle-leaf-sort`,
   `docs/user-manual`).
3. **Keep it additive** — never rewrite Phases 1–7. New features extend, they don't replace.
4. **Match conventions** — see `docs/developer-guide.md` §3: async, typed, layered,
   validated, audited.
5. **Test** — add/update tests in the matching `test_phaseN.py` file; run the full suite.
6. **Lint** — `ruff check app tests --select F,E9` must pass.
7. **Document** — update the relevant `docs/` guide and `docs/api.md` for any API change.
8. **Open a PR** using the [template](.github/PULL_REQUEST_TEMPLATE.md).

## Pull request checklist

- [ ] Describes the problem, approach, and evidence (test output, screenshots)
- [ ] Backwards compatible — no existing API/endpoint behaviour changed
- [ ] Adds or updates tests; full suite passes
- [ ] Ruff clean (F, E9)
- [ ] Docs updated (`docs/` + `docs/api.md` where relevant)
- [ ] No secrets, no debug leftovers

## Issue guidelines

Use the templates in `.github/ISSUE_TEMPLATE/`. Include: version, environment,
steps to reproduce, expected vs. actual, and logs. For security issues, do **not** open a
public issue — follow [`SECURITY.md`](SECURITY.md).

## Development setup

See [`docs/installation.md`](docs/installation.md) and
[`docs/developer-guide.md`](docs/developer-guide.md). Quick start:

```bash
cd backend && pip install -r requirements.txt
alembic upgrade head && python -m app.seed
python -m pytest tests -q          # 65 tests
cd ../frontend && npm install && npm run dev
```

## Recognition

All contributors are listed in the release notes. Research results submitted for
publication must credit the framework and follow the reproducibility guidelines in
`docs/phase6-deliverables.md`.
