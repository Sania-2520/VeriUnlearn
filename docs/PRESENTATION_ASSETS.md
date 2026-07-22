# Presentation Assets — VeriUnlearn Pitch

Assets to prepare for the competition pitch / launch presentation. Reuse the
shipped stack facts (FastAPI, Next.js, Celery, PostgreSQL, Redis, Qdrant,
MinIO, Kubernetes/Helm, Prometheus/Grafana/Loki). Screenshots should be
captured from the live demo or the `demo/` reference folder.

---

## 1. Architecture Diagram

Describe the following boxes (render as a clean vector / draw.io / Excalidraw
diagram):

- **Client tier:** Next.js 15 frontend (React 19, Tailwind, shadcn/ui,
  Recharts) → Nginx reverse proxy (security headers, TLS).
- **API tier:** FastAPI backend (`:8000`) — 28 REST routers (auth, unlearning,
  verify, governance…), RBAC (5 roles), MFA (TOTP), rate limiting.
- **Async tier:** Celery workers + Redis broker — unlearning jobs, benchmarks.
- **ML tier:** ML Engine (PyTorch 2.12 + PEFT/LoRA, `:8001`) — 4 unlearning
  algorithms + adaptive Hybrid Controller, verification (Merkle/Ed25519/
  zk-SNARK), explainability (SHAP/LIME/IG).
- **Data tier:** PostgreSQL 16 (primary), Redis 7 (cache/broker), Qdrant
  (vector store), MinIO (model/document/proof object storage).
- **Observability:** Prometheus (metrics), Grafana (dashboards), Loki (logs),
  Alertmanager (Slack/PagerDuty).
- **Infra:** Docker Compose (14 services), Helm chart (EKS), Terraform (AWS).

## 2. Key Metrics Slide

| Metric | Headline Number |
|--------|-----------------|
| Forget rate (successful removals) | ~100% verified via Merkle proof |
| MIA success rate (post-unlearning) | **0.08** (Certified) – **0.15** (Influence) |
| Utility retained | **0.95** (SISA) – **0.91** (Certified) |
| Inference/unlearning latency | 180 ms (Certified) – 1250 ms (SISA) |
| Test coverage | **88%** overall (backend + ML engine) |
| Algorithms supported | 4 + adaptive Hybrid Controller |

Pull exact figures from `README.md` benchmark table; regenerate with
`make benchmark && make graphs`.

## 3. Comparison Table vs Baselines

| Capability | VeriUnlearn | Naïve Retrain | Retrain-from-scratch | Black-box API |
|------------|-------------|---------------|----------------------|---------------|
| Cryptographic proof (Merkle+Ed25519) | ✅ | ❌ | ❌ | ❌ |
| Per-request unlearning | ✅ | ⚠️ full retrain | ❌ | ❌ |
| Latency (targeted) | Low (180–1250 ms) | High | Very high | N/A |
| Explainability (SHAP/LIME/IG) | ✅ | ❌ | ❌ | Partial |
| Immutable audit hash chain | ✅ | ❌ | ❌ | ❌ |
| Multi-tenant RBAC + MFA | ✅ | ❌ | ❌ | Varies |
| Open source (Apache 2.0) | ✅ | — | — | ❌ |

## 4. Screenshot Checklist (Dashboard Pages)

- [ ] Login screen (demo credentials)
- [ ] Dashboard overview
- [ ] Unlearning → New Request form
- [ ] Unlearning → Job progress (Celery)
- [ ] Verification Certificate (Merkle root + Ed25519 + proof chain)
- [ ] Benchmarks page (chart + Export button)
- [ ] Explainability (attributions + embeddings + heatmap)
- [ ] Audit Log (hash chain view)
- [ ] Grafana monitoring dashboards
- [ ] Architecture / system diagram

All reference stills live in `demo/`.

## 5. One-Liner Value Proposition

> **VeriUnlearn turns "we deleted your data" into a mathematically verifiable,
> cryptographically signed receipt — so compliance is provable, not promised.**

---

## Reusable Slide Skeleton (Markdown)

```markdown
# <Slide Title>

**One-line takeaway:** <the single idea this slide proves>

## Key points
- <point 1>
- <point 2>
- <point 3>

## Evidence
| Metric | Value |
|--------|-------|
| ...    | ...   |

> Callout / quote: <supporting statement>

---
*VeriUnlearn — Verifiable Machine Unlearning · Apache 2.0 License*
```

Use this skeleton for: Problem, Architecture, Live Demo, Verification Crypto,
Benchmarks, Explainability, Audit/Compliance, Closing/CTA.
