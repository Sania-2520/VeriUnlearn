# Security Policy

## Reporting a vulnerability

Please **do not open a public issue** for security vulnerabilities. Report privately
to the maintainers (GitHub private vulnerability reporting, or direct email to the
repository maintainers).

Include:

- Affected version(s) and commit(s)
- Description of the vulnerability and its impact
- Steps to reproduce (minimal)
- Suggested fix, if known

We aim to acknowledge reports within 72 hours and to ship a patched release for
confirmed high/critical issues as soon as possible.

## Security model (summary)

- **AuthN**: JWT bearer tokens or `X-API-Key` (hashed at rest, owner-role RBAC).
- **AuthZ**: five-role RBAC enforced server-side (`require_permission`); UI guards are
  defense-in-depth only.
- **Data**: passwords bcrypt-hashed; API keys SHA-256 hashed; deletion leaves
  deterministic tombstones (no plaintext serving post-deletion).
- **Transport**: TLS at the edge (nginx); security headers on every response; CSRF
  origin check for state-changing requests.
- **Limits**: slowapi rate limiting + per-key quotas + nginx `limit_req`.
- **Audit**: hash-chained audit trail with tamper verification.
- **CI**: Bandit + `npm audit --audit-level=high` on push/PR and weekly.

See `docs/phase7-deliverables.md` §13 (security checklist) and `docs/best-practices.md` §1.

## Supported versions

| Version | Supported |
|---|---|
| 1.0.x | ✅ |

## Dependency policy

- Backend deps are pinned in `backend/requirements.txt`; frontend in
  `frontend/package-lock.json`.
- Review upgrade PRs carefully; CI runs Bandit + npm audit automatically.
