# VeriUnlearn — Best Practices

Operational, development, and research practices that keep a VeriUnlearn deployment
secure, reliable, and publication-grade.

---

## 1. Security

- **Secrets** — never commit `.env*`; generate `SECRET_KEY` with `secrets.token_hex(32)`;
  rotate on personnel change or suspected leak. Use a secret manager in production.
- **Least privilege** — assign the narrowest role that does the job; `viewer` for read-only
  consumers; issue per-consumer API keys with tight quotas; revoke promptly.
- **TLS everywhere** — terminate at nginx/load balancer; force HTTPS redirects.
- **Metrics** — always set `METRICS_TOKEN` in production.
- **CORS/CSRF** — keep `CORS_ORIGINS` exact; the origin-check middleware rejects
  cross-origin state-changing requests.
- **Dependencies** — rely on CI (`security.yml`: Bandit + npm audit, weekly) and review
  upgrades before applying.
- **Audit** — treat the audit trail as evidence: back it up with the DB, never edit rows.

## 2. Data & privacy

- **Test with synthetic data** — the Adult Census dataset with synthesized PII is the
  reference; never point the platform at real personal data without a data-processing
  agreement.
- **Back up the keypair** — certificate verification depends on `keys/`; a lost keypair
  invalidates historical certificates.
- **Export evidence early** — download certificates + compliance snapshots regularly;
  don't rely on a live system being available during a regulator request.

## 3. Operations

- **Use PostgreSQL + Redis in production** — SQLite is single-process; rate limiting and
  quotas need shared state.
- **Monitor** — watch `/monitoring` error rate, dependency health, and queue depth; alert
  via Grafana on error-rate spikes and dependency-down.
- **Graceful upgrades** — read `CHANGELOG.md`, back up the DB + keys, deploy the new tag,
  then smoke-test `/health` and a small unlearning flow before announcing.
- **Restart policy** — prod compose uses `restart: unless-stopped` + healthchecks; keep
  logs bounded (json-file, max-size 10m, max-file 3).

## 4. Development

- **Follow the layering** — `api → services → repositories`; routers stay thin.
- **Validate at the edge** — Pydantic bounds for every request; fail fast on invalid input.
- **Audit mutations** — log `admin.*`, `api_key.*`, `privacy.scan.*` events.
- **Test per phase** — one `test_phaseN.py` per deliverable; run the full suite before push
  (65 tests, ~78% coverage). Keep ruff clean (`F`, `E9`).
- **Migrations are additive** — never edit an applied migration; add a new one.
- **Keep docs in sync** — every endpoint/table/service should be referenced in `docs/`
  (see `api.md`, `architecture.md`, the phase deliverables).

## 5. Research & benchmarking

- **Pin seeds** — experiments default to `seed=42`; derived seeds for MIA probes keep
  results reproducible.
- **Use versioned experiments** — capture environment snapshots and parameters so results
  can be reproduced and compared.
- **Document limitations** — MIA is confidence-based (no shadow models); recovery rate is
  currently fixed at 0.0. State these when writing results.
- **Non-destructive benchmarking** — the 6-method benchmark operates on in-memory clones;
  it is safe to run against a live deployment.

## 6. Delivery

- **Evidence bundles** — assemble certificate + verification report + audit excerpt +
  compliance snapshot for each data-subject request.
- **Release hygiene** — tag releases (`v*`), update `CHANGELOG.md`, record deployments
  in the admin portal, and keep the compatibility matrix in `release-1.0.0.md` current.
