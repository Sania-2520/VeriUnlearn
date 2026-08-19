# VeriUnlearn — Viva Preparation Guide

Interview/defence questions with concise, correct answers. Backed by the codebase —
verify any claim against `docs/` before the viva.

---

## Conceptual

**Q1. What is machine unlearning?**
Removing a training record's *influence* on a trained model without full retraining — the
operationalisation of GDPR Art. 17 / DPDP right-to-erasure for ML systems.

**Q2. Why is full retraining insufficient?**
Correct but O(D) per request — cost scales with dataset size × request volume. Worse, it
produces no *evidence*; "we retrained" is a claim, not a checkable artefact.

**Q3. What is SISA and why does it help?**
Sharded, Isolated, Sliced, Aggregated training: split D into k shards, train each
independently, aggregate by soft voting. Deleting records only retrains the affected
shards — deletion cost is O(affected shards), not O(D).

**Q4. What is certified removal?**
A closed-form Newton update `w′ = w − H⁻¹∇L_D(w)` with regularised Hessian
`H = XᵀDX/n + λI`. For convex losses the result equals full retraining up to the
regularisation, with a provable bound `‖w′−w‖₂ · max_x ‖x‖₂` on prediction drift.

**Q5. What is an influence function?**
A first-order estimate (via inverse-Hessian gradients) of how much each training record
contributed to the model — used for footprint scoring and the influence-scrub baseline.

**Q6. How do you *prove* deletion?**
Deterministic tombstones as Merkle leaves → pre/post roots differ by construction and are
recomputable by anyone; RSA signature binds the certificate; a hash-chained audit trail
detects tampering; ZK-style commitment gives evidence without revealing content; optional
blockchain anchoring adds external timestamping.

**Q7. What does the verification engine check?**
Eight checks: records tombstoned, embeddings removed, vectors removed, model versions
bumped, Merkle roots consistent, certificate signature valid, audit chain intact, and
overall consistency of recomputed vs. stored roots.

**Q8. What is membership inference (MIA) and why is AUC ≈ 0.5 good?**
MIA tries to guess whether a record was in training from model confidence. AUC ≈ 0.5 =
chance = deleted records are indistinguishable from never-seen ones → deletion worked.

## Architecture

**Q9. Describe the layers.** Data (ingestion/vector store) → ML (SISA trainer) → Privacy
(PII detection, search, footprint) → Unlearning (deletion engine) → Proof & Verification
(Merkle/certificate/8-check engine) → Platform (RBAC, compliance, monitoring,
notifications, API keys, CI/CD).

**Q10. Why FastAPI + SQLAlchemy async?** Async I/O for concurrent deletion/verification
jobs; typed OpenAPI for free; mature ecosystem.

**Q11. Why Next.js?** App Router + static/dynamic hybrid; TanStack Query caching; rapid
dashboards; standalone Docker output.

**Q12. How is RBAC enforced?** Server-side `require_permission("resource:action")` against
a 5-role matrix; API keys inherit their owner's role; UI guards are defense-in-depth.

**Q13. How do API keys work?** Raw `vk_…` key returned once; SHA-256 hash stored;
sliding-window per-minute quota; per-request usage log; revoke = instant 401.

**Q14. How is rate limiting done?** slowapi (`RATE_LIMIT_DEFAULT`) at the API + nginx
`limit_req` at the edge + per-key quotas.

**Q15. What does the audit trail guarantee?** Append-only hash chain — each event hashes
the previous event's hash; recomputation detects any modification (returns the broken
event id).

## Research

**Q16. What are the four research contributions?**
1. Verifiable LoRA-adapter unlearning; 2. Merkle-tree audit verification; 3.
Blockchain-backed compliance certificates; 4. Poisoning-resistant unlearning.
(Details: `docs/research-contributions.md`.)

**Q17. How is the benchmark reproducible?** Fixed seeds (default 42) drive delete/holdout
splits; derived seeds for MIA probes; experiments snapshot parameters + environment;
all rows persisted; CSV/JSON/Excel + LaTeX export.

**Q18. What are the headline results?** Certified removal = full-retrain utility
(0.777 acc / 0.362 F1) in 0.32 s with bound 1.5e3 on Adult Census (8,000 records, 4
shards, 40 deleted); MIA AUC 0.48 post-deletion; SISA 0.44 s; influence scrub 0.13 s
(0.760 acc).

**Q19. What are the limitations?** Certified method exact only for convex models; MIA is
confidence-based (no shadow models); recovery rate fixed at 0.0; in-memory benchmark
memory-bound at scale; no GPU metrics; optional backends (LoRA/blockchain) untested in CI.

**Q20. What is next (Phase 8)?** GPU deep-model unlearning, shadow-model auditing,
embedding-extraction harness, distributed training + multi-node Merkle, SSO/OIDC,
alerting, multi-tenancy, compliance evidence bundles, frontend tests, formal load tests.

## Practical

**Q21. How do I run the tests?** `cd backend && python -m pytest tests -q` (65 tests,
~78% coverage); `cd frontend && npm run build`.

**Q22. How do I deploy?** `docker compose -f docker-compose.prod.yml --env-file .env.prod
up -d --build` — nginx + backend + frontend + postgres + redis + qdrant + prometheus +
grafana; migrations auto-run on backend start.

**Q23. What must be backed up?** The DB and the RSA keypair in `keys/` — certificate
verification depends on the public key; a lost keypair invalidates old certificates.

**Q24. Where are the deliverables?** `docs/` — guides, IEEE paper (`ieee-paper.md`),
project report, presentation outline, diagrams, testing/performance reports, release
notes, completion summary.
