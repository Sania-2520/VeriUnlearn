# Security Hardening Report

**VeriUnlearn v1.0 Release Candidate** — 2026-08-08

## Status: HARDENED — no critical findings remain

This report summarizes the security hardening applied for v1.0. It covers both
the changes made in this release block and the hardening completed in the
preceding audit block (verified here), which together close every audit
finding.

## Changes in this release block

### RAG upload hardening
- **MIME allowlist** — uploads are rejected unless the declared content type is
  in an explicit allowlist (PDF, TXT, CSV, JSON, HTML, MD, DOCX, XLSX, images).
- **Size cap** — files larger than `settings.max_upload_size_bytes` are
  rejected before any write.
- **Path traversal prevention** — files persist under
  `rag_storage_dir/<uuid4>/<basename>`; the directory is a server-generated
  random UUID and the filename is `os.path.basename`-sanitized, so client
  filenames can never escape the storage root.
- **Content hash** — every upload is sha256-hashed; stored on the DB row for
  duplicate detection and integrity.

### Fail-closed behaviour verified
- Celery RAG retries are **transient-only** (`is_transient`): permanent 4xx
  failures are never retried, preventing retry storms on permanent errors.
- Missing OCR dependencies raise clear permanent errors rather than crashing
  workers with confusing exceptions.

## Standing hardening (prior block, verified in this pass)

- **JWT:** migrated from unmaintained python-jose to maintained PyJWT with
  signature/audience/issuer/expiry verification pinned and `require=["exp","iat"]`.
- **API keys:** fail-closed scope enforcement — only explicit `"*"` grants
  unrestricted access; empty scope lists grant nothing; expiry enforced; denied
  scope use is audited. Key creation now requires at least one scope.
- **Rate limiting:** denied requests no longer consume quota (fixed phantom
  member bug in the Redis sliding window).
- **Secrets:** placeholder/weak defaults rejected at startup outside
  development; 32+ char minimums enforced.
- **CORS:** wildcard origin rejected when credentials are allowed.
- **SSRF guard:** provider probes restricted to public address space, with
  credentials sent only to allowlisted provider hostnames.
- **Headers:** CSP, nosniff, frame-ancestors, referrer-policy,
  permissions-policy, HSTS in production; API responses no-store.
- **Input validation:** strict-mode `InputValidator` covers user inputs
  (verified present and tested in the ml-engine).

## Validation

- `bandit -r app` — no findings beyond acknowledged `nosec` comments
  (dev-default secrets that are rejected at startup in production).
- `mypy` clean; `ruff` clean on both packages.
- Backend suite: 262 tests pass, including new security-relevant tests
  (MLEngineClientError classification, upload persistence/size/type handling).
