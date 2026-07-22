# Judge Walkthrough — VeriUnlearn (≤10 minutes)

A guided tour a judge can follow end-to-end without prior setup. If the live
environment is unavailable, use the offline reference assets in `demo/` (see
the *Offline Reference* notes). All numbers/ports reflect the shipped stack:
FastAPI `:8000`, ML Engine `:8001`, Next.js frontend `:3000`/`:80`.

---

## 0. Start the Environment (2 min)

**Option A — Make (recommended):**
```bash
make setup
# or: cp .env.example .env && ./scripts/setup.sh --seed
```

**Option B — Docker Compose:**
```bash
docker compose up --build
```

**Verify health:**
```bash
curl http://localhost:8000/health      # backend
curl http://localhost:8001/health      # ML engine
```
Frontend: open **http://localhost:3000** (or **http://localhost** if nginx is
the entrypoint).

> Offline Reference: `demo/architecture.png`, `demo/login.png`.

---

## 1. Log In (30 s)

- Open the frontend URL.
- Use the **demo credentials**:
  - **Email:** `demo@veriunlearn.ai`
  - **Password:** `DemoPassword123!`
- You land on the Dashboard.

> Offline Reference: `demo/dashboard.png`.

---

## 2. Submit a Deletion Request (1.5 min)

1. Navigate to **Unlearning → New Request** (or `POST /api/v1/unlearning/requests`).
2. Select a tenant / dataset and the record(s) to forget.
3. Choose an algorithm — **SISA**, **Influence Functions**, **Certified
   Removal**, or let the **Hybrid Controller** decide.
4. Click **Submit**. Note the request ID.

> Offline Reference: `demo/unlearning-request.png`.

---

## 3. Watch the Unlearning Job (1.5 min)

1. Go to **Unlearning → Jobs**.
2. Watch the Celery-backed job progress: shard retrain (SISA) / influence
   computation / certified removal.
3. Status moves `queued → running → verified`. (ML Engine `:8001` does the work.)

> Offline Reference: `demo/job-progress.png`.

---

## 4. View the Verification Certificate (2 min)

1. Open the completed job → **Verification Certificate**.
2. Inspect the **Merkle root** (SHA-256) over the verification dataset.
3. Confirm the **Ed25519 signature** — proves certificate authenticity.
4. Expand the **proof chain** (Merkle inclusion proofs; zk-SNARK option in
   prototype) showing the record is no longer influential.
5. Note the **trust score** / verification summary.

> Offline Reference: `demo/verification-certificate.png`, `demo/merkle.png`.

---

## 5. Benchmarks Page (1 min)

1. Go to **Benchmarks**.
2. View the comparison **chart** (Utility Retained, MIA Accuracy, Latency)
   across SISA / Influence / Certified / Hybrid.
3. Click **Export** (CSV/JSON) to download leaderboard results.

> Offline Reference: `demo/benchmarks.png`.

---

## 6. Explainability (1 min)

1. Open **Explainability**.
2. Inspect **SHAP / LIME / Integrated Gradients** attributions.
3. View **embedding visualizations** (PCA/UMAP) and the **privacy heatmap** /
   drift detection panel.

> Offline Reference: `demo/explainability.png`.

---

## 7. Audit Log (1 min)

1. Go to **Audit Log** (Governance).
2. Confirm the **hash chain** — each entry cryptographically links to the
   previous (immutable, blockchain-anchored ledger).
3. Filter by the deletion request ID from Step 2 to see the full compliance
   trail.

> Offline Reference: `demo/audit-log.png`.

---

## 8. Monitoring (if profile enabled) (30 s)

1. If the monitoring profile is enabled, open **Grafana** (`http://localhost:3001`,
   default `admin:admin` — change in `.env`).
2. View the pre-provisioned dashboards: request rate, latency, unlearning-job
   throughput, GPU utilization (Prometheus + Loki logs).

> Offline Reference: `demo/grafana.png`.

---

## Done — What the Judge Has Seen

- A real deletion request flowed through FastAPI → Celery → ML Engine.
- Cryptographic proof (Merkle + Ed25519) that data was unlearned.
- Benchmarks, explainability, and an immutable audit hash chain.
- Production-grade monitoring and observability.

**Total time:** ~10 minutes. Use `demo/` screenshots as the offline fallback.
