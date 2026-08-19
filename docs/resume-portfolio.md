# VeriUnlearn — Resume & Portfolio Material

Copy-paste-ready content for applications and portfolios.

---

## 1. ATS-friendly project description (one paragraph)

**VeriUnlearn — Verifiable Machine Unlearning Framework (Python · FastAPI · Next.js)**
End-to-end platform that deletes personal data from trained ML models with cryptographically
verifiable evidence, built for GDPR Art. 17 / DPDP Act 2023 compliance. Implements SISA
sharded training, certified Newton-step removal with provable drift bounds, and influence
functions; generates Merkle-root deletion proofs, RSA-signed certificates, and a
tamper-evident hash-chained audit trail; ships an 8-check verification engine, a
reproducible 6-method benchmark, a 4-family attack suite (membership inference, inversion,
extraction, poisoning), five-role RBAC, compliance dashboards, Prometheus/Grafana
monitoring, API-key management, and Docker/CI-CD deployment. 65 passing tests at 78%
coverage; certified removal matched full-retrain utility (0.777 accuracy) in 0.32 s with
post-deletion membership-inference AUC at chance level (0.48). Open source (MIT).

## 2. Resume bullet points

**VeriUnlearn — Verifiable Machine Unlearning Framework** *(major project)*
- Designed a 6-layer FastAPI + Next.js platform that removes personal data from ML models
  and issues cryptographically verifiable deletion evidence (Merkle roots, RSA certificates,
  hash-chained audit trail, optional blockchain anchoring).
- Implemented SISA sharded training, certified Newton-step removal with mathematical drift
  bounds, and influence-function scoring; certified removal matched full-retrain accuracy
  (0.777) at 0.32 s — ~30% faster than shard retraining — on the Adult Census benchmark.
- Built an 8-check verification engine and a reproducible 6-method benchmark with a 4-family
  attack suite (MIA AUC 0.48 post-deletion ≈ chance), versioned experiments, and CSV/JSON/
  Excel/LaTeX exports.
- Shipped enterprise features: five-role RBAC enforced server-side, admin portal, GDPR/DPDP
  compliance dashboards with persisted snapshots, Prometheus/Grafana monitoring, SMTP + in-app
  notifications, API keys with quotas and usage logs, analytics, and CSV/JSON export endpoints.
- Hardened the service: security headers, CSRF origin checks, rate limiting, hashed API keys,
  audit-logged mutations; CI with pytest, Bandit, and npm audit.
- Authored 25+ documentation deliverables: IEEE-format paper, academic report, developer/user/
  administrator guides, troubleshooting, diagrams (Mermaid), testing & performance reports,
  demo scripts, and viva guide.

## 3. LinkedIn project summary

**VeriUnlearn** — Building compliance-grade ML: I designed and built an end-to-end
framework for verifiable machine unlearning — deleting a person's data from trained models
while producing cryptographic proof (Merkle-root deletion proofs, RSA-signed certificates,
tamper-evident audit trail) that regulators can independently check. It combines research
(SISA, certified removal, influence functions), evaluation (reproducible benchmark + attack
suite), and production engineering (RBAC, compliance dashboards, monitoring, API keys,
Docker, CI/CD) in one MIT-licensed codebase. Key result: certified removal matches
full-retraining utility at a fraction of the cost, with membership-inference leakage at
chance level after deletion. Open to privacy-engineering, ML, and full-stack roles.

## 4. GitHub repository description

**VeriUnlearn** — A production-grade verifiable machine unlearning framework for GDPR
right-to-be-forgotten compliance: efficient SISA/certified/influence deletion, Merkle-deletion
proofs, RSA certificates, 8-check verification, reproducible benchmark + attack suite,
compliance dashboards, RBAC, monitoring, API keys, Docker + CI/CD. FastAPI + Next.js. MIT.

## 5. Portfolio case study

**Problem.** A data subject asks to be forgotten; the operator must remove their data's
influence on trained models *and prove it*. Retraining is expensive and unverifiable.

**Approach.** Six-layer platform: sharded training (SISA) → privacy audit → surgical
deletion (certified/influence/SISA) → cryptographic proof (Merkle + RSA + audit chain) →
verification (8 checks) → enterprise compliance layer (RBAC, dashboards, monitoring, keys).

**What I built.** 30+ backend services and 60+ API routes (FastAPI/SQLAlchemy async), 20+
frontend pages (Next.js 15/TanStack Query), 8 additive migrations, Docker Compose prod stack
with Prometheus/Grafana, GitHub Actions CI/CD, and 25+ docs (IEEE paper, academic report,
guides, diagrams).

**Results.** Certified removal = full-retrain utility (0.777 acc) in 0.32 s with a provable
bound; MIA AUC 0.48 (chance) post-deletion; 65 tests at 78% coverage; end-to-end verifiable
evidence pipeline (certificate → verification report → audit excerpt → compliance snapshot).

**Takeaways.** Efficiency and verifiability are complementary, not competing; evidence-first
design (proofs, audit, exports) makes compliance engineering credible; reproducible research
tooling (seeds, versions, exports) turns results into publications.

## 6. One-page executive summary

**VeriUnlearn: verifiable machine unlearning for GDPR compliance.**
- **Problem** — erasure law requires removing data *and its model influence*; retraining is
  costly and unprovable.
- **Solution** — SISA/certified/influence deletion plus Merkle-RSA-audit evidence, verified
  by an 8-check engine, wrapped in a production platform (RBAC, compliance dashboards,
  monitoring, API keys, CI/CD).
- **Evidence** — certified removal matches full-retrain utility at 0.32 s; MIA leakage at
  chance post-deletion; reproducible 6-method benchmark; 65 tests / 78% coverage.
- **Impact** — a reference implementation for GDPR Art. 17 / DPDP compliance engineering and
  a benchmark substrate for unlearning research; MIT-licensed, Docker-deployable, fully
  documented (25+ docs including an IEEE-format paper).
