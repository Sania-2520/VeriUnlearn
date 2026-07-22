# Demo Video Outline — VeriUnlearn (6–8 minutes)

A scene-by-scene script for the launch / judged-competition demo video.
Approximate durations and on-screen text are provided. Pair with the live
walkthrough in [DEMO_WALKTHROUGH.md](DEMO_WALKTHROUGH.md) and the static
assets in `demo/`.

---

## Scene 1 — Title (0:00–0:20)

- **On-screen:** VeriUnlearn logo + tagline
  *"Verifiable Machine Unlearning with Cryptographic Proofs."*
- **Voiceover:** One-line value proposition — organizations can prove deleted
  data no longer influences their models.

## Scene 2 — Problem Statement (0:20–1:00)

- **On-screen:** GDPR/CCPA "right to be forgotten" → model still remembers?
- **Voiceover:** Regulation demands forgetting; standard ML has no receipt.
  Deleting a row from training data doesn't remove its influence.
- **Stat callout:** MIA (membership inference) success rates on undeleted
  models.

## Scene 3 — Architecture (1:00–1:30)

- **On-screen:** Architecture diagram (Next.js → Nginx → FastAPI → ML Engine;
  PostgreSQL, Redis, Qdrant, MinIO; Celery; Prometheus/Grafana/Loki).
- **Voiceover:** 30-second tour of the stack — API, async jobs, vector store,
  object storage, and observability.

## Scene 4 — Live Deletion Request (1:30–3:00)

- **On-screen:** Frontend login (`demo@veriunlearn.ai` / `DemoPassword123!`) →
  Unlearning → New Request → submit.
- **Voiceover:** Walk through selecting a record, picking an algorithm
  (Hybrid Controller), and submitting. Show the job ID.

## Scene 5 — Verification Certificate Crypto Explainer (3:00–4:30)

- **On-screen:** Job progress → Verification Certificate; zoom on Merkle root
  (SHA-256), Ed25519 signature, proof chain.
- **Voiceover:** Explain how a Merkle tree over the verification set plus an
  Ed25519 signature produces a tamper-evident, independently verifiable
  certificate that the data was removed. Mention zk-SNARK privacy option.

## Scene 6 — Benchmark Comparison (4:30–5:30)

- **On-screen:** Benchmarks page chart — Utility Retained / MIA Accuracy /
  Latency across SISA, Influence, Certified, Hybrid; CSV export.
- **Voiceover:** Show the trade-offs: Certified Removal hits MIA ~0.08 with
  lowest latency; SISA retains 0.95 utility.

## Scene 7 — Explainability (5:30–6:15)

- **On-screen:** SHAP/LIME/Integrated Gradients attributions, PCA/UMAP
  embeddings, privacy heatmap.
- **Voiceover:** Trust through explainability — see why the model decides.

## Scene 8 — Audit & Compliance (6:15–7:15)

- **On-screen:** Audit Log hash chain; filter by deletion request ID;
  compliance webhooks (GDPR/CCPA/DPDP).
- **Voiceover:** Immutable, blockchain-anchored audit trail = audit-ready
  evidence.

## Scene 9 — Closing (7:15–8:00)

- **On-screen:** One-liner value prop + GitHub/repo CTA + license (Apache 2.0).
- **Voiceover:** VeriUnlearn — mathematical proof that privacy promises are
  kept. Call to action: star the repo, read the docs.

---

## Production Notes

- Keep Scene 4–5 as the emotional/core peak (the "receipt" moment).
- Use `demo/*.png` as B-roll when live env is unstable.
- Captions for all VO; export 1080p, 16:9.
- End card: repo URL, `demo@veriunlearn.ai` credentials teaser, Apache 2.0 license.
