# VeriUnlearn — FAQ

Frequently asked questions about the platform, the science, and the project.

---

## Platform

**What is VeriUnlearn?**
A production-grade framework for **verifiable machine unlearning** — deleting personal data
(and its influence on trained ML models) with cryptographic evidence, built for GDPR
Article 17 / DPDP Act 2023 compliance. It makes unlearning *efficient* (SISA sharding,
influence functions, certified removal) and *provable* (Merkle deletion proofs, RSA-signed
certificates, hash-chained audit trail, optional blockchain anchoring).

**Which roles exist?**
`admin`, `researcher`, `auditor`, `operator`, `viewer`. Permissions are scoped
`resource:action` strings enforced server-side; the UI hides what a role can't use.

**How do I get an API key?**
Admin/researcher/operator/auditor users can issue keys from the **Developer portal**.
Keys are shown once, have per-minute quotas, and inherit their owner's role.

**What data does the platform store?**
Datasets (uploads), trained models + shards, tombstones of deleted records, Merkle roots,
certificates, audit events, compliance snapshots, system metrics, API keys, notifications,
and user accounts. See the ER diagram in [`diagrams.md`](diagrams.md).

**Can I export compliance evidence?**
Yes — compliance snapshots (CSV/JSON), analytics (CSV/JSON), benchmark results
(CSV/JSON/Excel), certificates (JSON/PDF), and verification reports (JSON/PDF).

## Science & methodology

**What is SISA?**
Sharded, Isolated, Sliced, Aggregated training: the dataset is split into shards trained
independently and aggregated by soft voting. Deleting a record only retrains the shard(s)
containing it — far cheaper than full retraining.

**What is certified removal?**
A Newton-step weight update (`w′ = w − H⁻¹ ∇L_D(w)` with `H = XᵀDX/n + λI`) that provably
bounds the change in predictions after removing a set of records. VeriUnlearn reports the
mathematical bound alongside the result.

**What is an influence function?**
A first-order estimate of how much each training record contributed to the model, used to
score records and guide scrubbing.

**How does verification prove deletion?**
Eight checks: records tombstoned, embeddings/vectors removed, versions bumped, Merkle roots
changed deterministically, certificate signature valid, audit chain intact, consistency of
recomputed vs. stored roots. The pre/post Merkle roots are recomputable by anyone holding
the leaves + proof.

**Are the attack results real?**
The attack lab (MIA, inversion, extraction, poisoning) runs against synthetic/local data
(e.g. Adult Census with synthesized PII). Results are reproducible via fixed seeds and
persisted rows.

## Operations

**Why use PostgreSQL in production?**
SQLite is fine for dev, but per-process rate limiting and sliding-window quotas need a
shared backend (Redis/Postgres) for multi-instance correctness.

**I lost `backend/keys/` — what happens?**
Old certificates can no longer be verified (signature check fails). The keypair must be
backed up; a new keypair only signs new certificates.

**How do notifications reach users?**
In-app always; email when `EMAIL_PROVIDER=smtp` is configured (null provider = no-op).

**How do I update the platform?**
Pull the new release, check `CHANGELOG.md`, restart the prod compose stack (migrations run
automatically on backend start), and smoke-test `/health` + one unlearning flow.

## Project

**Who is this for?**
Researchers (benchmarking unlearning), privacy engineers (compliance pipelines), and
students (major-project / publication material). See `docs/research-contributions.md`.

**What are the four research contributions?**
1. Verifiable LoRA-adapter unlearning, 2. Merkle-tree audit verification, 3.
blockchain-backed compliance certificates, 4. poisoning-resistant unlearning —
all detailed in `docs/research-contributions.md`.

**License?**
MIT — see [`LICENSE`](../LICENSE).
