# VeriUnlearn — Presentation Outline (PowerPoint)

18 slides with speaker notes. Target length: 15 minutes + Q&A (adjust by trimming slides 9, 14, 16).

---

## Slide 1 — Title
**VeriUnlearn** — A Verifiable Machine Unlearning Framework for GDPR Right-to-Be-Forgotten Compliance
*Subtitle:* Efficient, provable, auditable deletion of personal data from ML models
*Presenter, Institution, Date*

> **Speaker notes:** "Good morning. Today I present VeriUnlearn — a framework that not only *removes* personal data from trained ML models, but *proves* it removed, in a way regulators can check. This is a full-stack system: research-grade unlearning science plus a production-ready compliance platform."

---

## Slide 2 — Problem
- GDPR Art. 17 / DPDP Act 2023: users may demand erasure — *including model influence*
- Full retraining: expensive, slow, and **unverifiable**
- Today: "we deleted it" is a promise, not a proof

> **Speaker notes:** "The legal obligation is real and growing. But compliance teams can't answer the question that matters: *how do you prove a model no longer knows a person?* Retraining is the only correct baseline and it's too expensive per request."

## Slide 3 — Motivation
- Legal deadlines + fines for non-compliance
- Retraining cost scales with dataset size × request volume
- Trust: regulators/data subjects need **checkable evidence**
- Research: no reproducible, integrated benchmark existed

> **Speaker notes:** "Three drivers — law, economics, trust. And a fourth: the research community studies unlearning in isolation; nobody ships the whole loop integrated. That's the gap we close."

## Slide 4 — Research Gap
- Efficiency work (SISA, certified removal) ≠ verifiability work (proof systems)
- No integrated system with training + deletion + proof + benchmark + attacks
- No production-ready reference implementation

> **Speaker notes:** "SISA makes deletion cheap. Certified removal adds a mathematical bound. Proof-of-unlearning systems add cryptography. VeriUnlearn is the first system we know of that combines all of it — plus the tooling to evaluate it — in one deployable codebase."

## Slide 5 — Objectives
1. Efficient surgical unlearning (3 methods)
2. Cryptographic, verifiable deletion evidence
3. Measurable privacy guarantees
4. Reproducible research tooling
5. Production deployment readiness

> **Speaker notes:** "Five objectives. The first three are the science; the last two make it a *platform* rather than a prototype."

## Slide 6 — Architecture (High Level)
- 6 layers: Data → ML → Privacy → Unlearning → Proof & Verification → Platform
- FastAPI + SQLAlchemy (async) backend; Next.js frontend
- Docker Compose, NGINX, Prometheus, Grafana

> **Speaker notes:** "Six clean layers. The top three are the compliance pipeline; the bottom ones are enterprise concerns — RBAC, dashboards, monitoring. Each layer is independently testable."

## Slide 7 — Workflow (The Compliance Loop)
Ingest → Shard & Train → Search Identity → Impact Analysis → Surgical Delete → Merkle Roots → Signed Certificate → Audit Trail → Verify

> **Speaker notes:** "Walk the loop: data comes in, gets sharded and trained. A user request arrives; we find the identity's footprint, run impact analysis, delete surgically. Crucially, deletion recomputes Merkle roots — so before/after is *provably* different. Then we sign a certificate and append to the tamper-evident audit chain."

## Slide 8 — Technology Stack
| Layer | Tech |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, NumPy/Scikit-learn, cryptography, Alembic |
| Frontend | Next.js 15, TanStack Query, Tailwind, Recharts |
| Storage | SQLite (dev) / PostgreSQL, Qdrant vectors, Redis |
| Ops | Docker Compose, NGINX, Prometheus, Grafana, GitHub Actions |

> **Speaker notes:** "Boring, standard, production-proven choices — the innovation is in the unlearning and proof machinery, not the plumbing."

## Slide 9 — System Design (Key Components)
- SISA trainer + soft-vote aggregation
- Deletion engine (tombstoning + shard scrub)
- Merkle engine, certificate service, ZK commitments, optional blockchain
- Verification engine (8 checks)
- RBAC, compliance, monitoring, notifications, API keys

> **Speaker notes:** "Zoom in on the heart: SISA shards make deletion cheap; the proof stack makes it verifiable; the verification engine checks eight independent conditions and emits a report."

## Slide 10 — Demo Workflow
1. Log in (admin) → Dashboard
2. Privacy Auditor: search an identity → footprint
3. Impact analysis → choose method → delete
4. Watch pipeline: tombstone → scrub → roots → certificate
5. Verify certificate (signature + hash + root + audit chain)
6. Compliance snapshot + export CSV/JSON

> **Speaker notes:** "Live demo. Start with a search, open the footprint, run a certified deletion, then verify the certificate — and show the compliance snapshot updating. Every step is persisted and audited."

## Slide 11 — Algorithms
- **SISA**: sharded, isolated, sliced, aggregated — retrain only affected shards
- **Certified removal**: Newton step `w′ = w − H⁻¹∇L_D(w)` with bound `‖Δw‖·max‖x‖`
- **Influence functions**: per-record contribution scores
- **Merkle proof**: canonical tombstones → recomputable roots, O(log n) membership proofs

> **Speaker notes:** "Three deletion methods with a clear trade-off axis: SISA is the gold standard, certified removal adds a provable bound at convex scale, influence scrub is the fast baseline. Merkle leaves are deterministic tombstones, so anyone can recompute the post-deletion root and check it differs."

## Slide 12 — Security
- RBAC (5 roles) enforced server-side + UI guards
- API keys: hashed storage, quotas, usage logs, owner-role inheritance
- Security headers, CSRF origin check, rate limiting
- Audit trail: hash-chained, tamper detection
- Bandit + npm audit in CI

> **Speaker notes:** "Security is layered: identity (JWT or API keys), authorization (RBAC), transport/CSRF hardening, and an immutable audit trail that makes tampering detectable."

## Slide 13 — Verification
- 8 checks: records, embeddings, vectors, versions, Merkle, signature, audit chain, consistency
- RSA-signed certificates + downloadable JSON/PDF
- Independent re-verification endpoint + blockchain anchoring (optional)

> **Speaker notes:** "The 8-check engine is the compliance answer: it doesn't just assert deletion, it recomputes and cross-checks. Certificates are signed and downloadable — a data subject gets a PDF they can verify independently."

## Slide 14 — Benchmark Results
- Adult Census: 8,000 records, 4 shards, 40 deleted
- Certified removal = full-retrain utility (0.777 acc) in 0.32 s with bound 1.5e3
- MIA AUC 0.48 post-deletion (chance level)
- 6-method reproducible benchmark, CSV/JSON/Excel + LaTeX export

> **Speaker notes:** "Numbers on the board: exact utility preservation with certified removal, sub-second cost, and membership inference at chance. All reproducible — fixed seeds, versioned experiments, environment snapshots."

## Slide 15 — Research Contributions
1. Verifiable LoRA-adapter unlearning
2. Merkle-tree audit verification
3. Blockchain-backed compliance certificates
4. Poisoning-resistant unlearning

> **Speaker notes:** "Four contributions beyond the integration itself — details in the paper's research-contributions document."

## Slide 16 — Advantages & Future Scope
- **Advantages**: efficient + provable; auditable; reproducible; deployable; open source (MIT)
- **Future**: deep-model/GPU unlearning, shadow-model auditing, SSO, multi-tenancy, alerting, evidence bundles

> **Speaker notes:** "What we deliver today vs. where it goes. The extension points are documented in the codebase — the schema and metric slots are pre-wired."

## Slide 17 — Conclusion
- Efficient unlearning **and** verifiable deletion are complementary
- Certified removal: exact utility, provable bound, sub-second cost
- Integrated, production-ready, reproducible reference implementation

> **Speaker notes:** "The takeaway: you don't have to choose between cheap unlearning and provable compliance. VeriUnlearn delivers both, in one auditable pipeline, with the tooling to prove it."

## Slide 18 — Questions
- Thank you — questions welcome
- Contact + repository links

> **Speaker notes:** "I'm happy to take questions — expect depth on the Merkle proof scheme, the certified bound, and how RBAC/audit enforce compliance."
