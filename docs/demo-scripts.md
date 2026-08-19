# VeriUnlearn — Demo Scripts

Three scripts (5 / 10 / 15 minutes) for a live demo. All assume the seeded environment
(`python -m app.seed`) with demo logins `admin@veriunlearn.dev / admin12345`.

---

## Demo 1 — 5 minutes (executive / teaser)

| Time | Action | Lines |
|---|---|---|
| 0:00 | Open dashboard. "This is VeriUnlearn — a platform that deletes personal data from ML models and *proves* it." | Show compliance score + request stats |
| 0:45 | **Privacy Auditor** → search `maya` → open footprint. "Every identity is indexed across shards, embeddings and neurons." | Show clusters/influence scores |
| 1:30 | **Surgical Unlearning** → identity `maya` → Impact analysis → method *certified*. | Show impact report |
| 2:15 | Execute deletion → watch pipeline: tombstone → scrub → roots → certificate. | Narrate each step |
| 3:00 | **Verification** → verify the certificate → download PDF. "Signature + hash + roots + audit chain — independently checkable." | Show 8-check report |
| 4:00 | **Compliance** → Generate snapshot → CSV export. "Compliance evidence, one click." | Show reports row |
| 4:45 | Wrap-up: "Efficient, provable, auditable — production-ready." | — |

## Demo 2 — 10 minutes (technical)

Everything in Demo 1, plus:

| Time | Segment |
|---|---|
| 0:00–1:00 | **Architecture intro**: 6 layers (data → ML → privacy → unlearning → proof → platform). Show `docs/architecture.md` diagram. |
| 1:00–6:00 | Demo 1 flow (search → impact → certified deletion → verify → compliance export). |
| 6:00–7:30 | **Benchmark**: Research Hub → Benchmark → run 6-method comparison → radar chart → CSV export. "Reproducible, seeded, versioned." |
| 7:30–8:30 | **Attack Lab**: MIA on the model before/after → show AUC drop. |
| 8:30–9:30 | **Admin & security**: RBAC matrix, API key issue → `curl -H "X-API-Key: …"`, notifications, monitoring page. |
| 9:30–10:00 | Wrap-up + what's next (Phase 8). |

## Demo 3 — 15 minutes (full viva / defence)

| Time | Segment |
|---|---|
| 0:00–2:00 | **Title + problem + motivation**: GDPR Art. 17 / DPDP; retraining cost; no verifiability today. |
| 2:00–4:00 | **Architecture walkthrough**: layers, stack, repo layout, data model highlights. |
| 4:00–6:00 | **Algorithms**: SISA sharding (draw shards), certified Newton step + bound, Merkle proof (pre/post roots). |
| 6:00–11:00 | **Live demo** (Demo 2 flow: search → impact → delete → verify → benchmark → attacks → admin/API key). |
| 11:00–12:30 | **Results**: benchmark table (0.777 acc, 0.32 s certified, bound 1.5e3), MIA AUC 0.48, backdoor persistence collapse. |
| 12:30–13:30 | **Security & enterprise**: RBAC enforcement, audit trail tamper check, headers/CSRF, CI/CD + monitoring. |
| 13:30–14:30 | **Limitations + future work**: convex-only certified, shadow-model auditing pending, Phase 8 roadmap. |
| 14:30–15:00 | **Conclusion**: efficient + provable + auditable; open source. → Questions. |

## Failure recovery demo (bonus, 60 s)

1. Start a deletion, then **stop the backend** mid-flight (Ctrl+C).
2. Restart (`uvicorn app.main:app`) — migrations/startup are idempotent; the request
   shows `failed` in history (tombstones already applied remain consistent).
3. Re-run the deletion → completes with a certificate.
   *Narrate:* "Deletion is idempotent and crash-safe — tombstones are applied before the
   proof is computed, and verification recomputes roots from the DB, so a restart never
   breaks the chain."

## Expected questions (short answers)

- **Why Merkle?** O(log n) membership proofs + deterministic recomputation; anyone can
  verify without trusting us.
- **Why is certified removal exact?** Newton step on the regularised empirical risk —
  closed form for convex losses; bound `‖Δw‖·max‖x‖` covers prediction drift.
- **Why is MIA AUC 0.48 meaningful?** Below 0.5 ≈ chance — deleted records are
  indistinguishable from never-seen records at confidence level.
- **SQLite vs Postgres?** SQLite for dev; Postgres/Redis in prod for shared rate-limit
  state. (Full answers: `docs/viva-guide.md`.)
