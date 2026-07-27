# VeriUnlearn — Complete Demonstration Package

## 1. Demo Overview

VeriUnlearn is a verifiable machine unlearning platform that provides cryptographic proof that data has been removed from trained models. This demonstration package enables judges, evaluators, and stakeholders to explore the full platform workflow — from submitting a deletion request to verifying the cryptographic certificate — without running the heavy ML pipeline.

**Demo credentials:** `demo@veriunlearn.ai` / `DemoPassword123!`

**Core value proposition:** Organizations can cryptographically *prove* deleted data no longer influences their models, satisfying GDPR Article 17, CCPA, and emerging AI regulations.

---

## 2. Demo Dataset Description

| Dataset | Classes | Samples | Size | Description |
|---------|---------|---------|------|-------------|
| CIFAR-10 | 10 | 50,000 | 168 MB | 32×32 RGB images (airplane, automobile, bird, cat, deer, dog, frog, horse, ship, truck) |
| CIFAR-100 | 100 | 50,000 | 169 MB | 32×32 RGB images (100 fine-grained classes grouped into 20 superclasses) |
| Tiny ImageNet | 200 | 100,000 | 237 MB | 64×64 RGB images (subset of ImageNet with 200 classes, 500 train + 50 val per class) |

**Pre-trained models (LoRA adapters):**

| Model | Parameters | Adapter | Description |
|-------|-----------|---------|-------------|
| ResNet-18 | 11.2 M | LoRA-r8 | Lightweight, fast inference |
| ResNet-50 | 25.6 M | LoRA-r16 | Balanced accuracy/speed |
| ViT-B/16 | 86.6 M | LoRA-r16 | Vision Transformer, highest accuracy |

**Unlearning algorithms:**

| Algorithm | Type | Best for |
|-----------|------|----------|
| SISA | Sharded | High utility retention (0.95) |
| Influence | Influence-based | Precision removal |
| Certified | Differential privacy | Formal guarantees (MIA ~0.08) |
| Hybrid | Adaptive controller | Automatic algorithm selection |

---

## 3. Sample Deletion Request Scenarios

Five pre-configured scenarios demonstrate the lifecycle:

### Scenario A: SISA — Completed (`del-req-bfe74a1b98f3`)
- **Dataset:** CIFAR-10, **Algorithm:** SISA
- **Target:** 5 records (IDs 3164, 9886, 21222, 25875, 42659)
- **Status:** `completed` → certificate available (`cert-sisa-cifar10`)
- **GDPR context:** Art. 17 erasure — standard deletion with high utility preservation

### Scenario B: Influence — Verified (`del-req-9456bdfa12ea`)
- **Dataset:** CIFAR-100, **Algorithm:** Influence
- **Target:** 5 records (IDs 4747, 6168, 23965, 35119, 38193)
- **Status:** `verified` (certificate issued and verified)
- **Use case:** Precision-focused removal where data influence must be nullified

### Scenario C: Certified — In Progress (`del-req-a697f8b99a46`)
- **Dataset:** Tiny ImageNet, **Algorithm:** Certified
- **Target:** 5 records (IDs 2457, 3801, 5632, 14070, 33255)
- **Status:** `in_progress` (demonstrates real-time job tracking)
- **Use case:** Formal differential privacy guarantees

### Scenario D: Hybrid — Completed (`del-req-bc0e142195cb`)
- **Dataset:** CIFAR-10, **Algorithm:** Hybrid Controller
- **Target:** 5 records (IDs 4578, 5944, 15772, 27405, 28419)
- **Status:** `completed` → certificate available (`cert-influence-cifar10`)
- **Use case:** Adaptive algorithm selection by the hybrid controller

### Scenario E: SISA — Verified (`del-req-d9c2b1bc8ab6`)
- **Dataset:** CIFAR-100, **Algorithm:** SISA
- **Target:** 5 records (IDs 3873, 8113, 27821, 36113, 37057)
- **Status:** `verified` (fully verified with certificate chain)
- **Use case:** SISA with cross-dataset verification

---

## 4. Verification Certificate Walkthrough

Each certificate contains a cryptographic proof chain with 7 steps:

```
Step 0: Initialize unlearning request      → hash
Step 1: Load model checkpoint              → hash
Step 2: Apply unlearning algorithm          → hash
Step 3: Verify parameter delta              → hash
Step 4: Compute inclusion test              → hash
Step 5: Generate zero-knowledge proof        → hash
Step 6: Submit to certificate chain          → hash
                                               ↓
                                        Merkle Root (SHA-256)
                                               ↓
                                        Ed25519 Digital Signature
```

### Certificate Fields

| Field | Description | Example |
|-------|-------------|---------|
| `certificate_id` | Unique identifier | `cert-sisa-cifar10` |
| `root_hash` | SHA-256 hash of all proof steps | `2aff72baedd...` |
| `merkle_root` | Merkle tree root (verification set) | `1a7146f0fbaf...` |
| `proof_steps` | Array of 7 hashed steps | See above |
| `inclusion_test_passed` | Data inclusion verification | `true` |
| `exclusion_verified` | Data exclusion confirmed | `true` |
| `signer` | Signing authority | `veriunlearn-verifier` |
| `issued_at` / `expires_at` | Validity window | 1-year validity |

### Verifying a Certificate

```bash
# Step 1: Verify certificate signature (Ed25519)
curl -X POST http://localhost:8000/api/v1/certificates/verify \
  -H "Content-Type: application/json" \
  -d '{"certificate_id": "cert-sisa-cifar10"}'

# Step 2: Inspect the proof chain
curl http://localhost:8000/api/v1/certificates/cert-sisa-cifar10

# Step 3: Confirm the Merkle inclusion
curl http://localhost:8000/api/v1/certificates/cert-sisa-cifar10/inclusion-proof
```

### Available Certificates (in `demo/verification-certificates/`)

| Certificate | Algorithm | Dataset | Status |
|-------------|-----------|---------|--------|
| `cert-sisa-cifar10` | SISA | CIFAR-10 | Valid |
| `cert-influence-cifar10` | Influence | CIFAR-10 | Valid |
| `cert-certified-cifar10` | Certified | CIFAR-10 | Valid |
| `cert-hybrid-cifar10` | Hybrid | CIFAR-10 | Valid |

---

## 5. Dashboard Tour

### Page 1: Login Screen
- Demo credentials pre-filled
- SSO options (Google, GitHub) shown but disabled in demo
- Session token issued upon login

### Page 2: Dashboard
- Summary cards: Total requests, Completed, Verified, In Progress
- Recent activity feed
- System health indicators (green/amber/red)
- Quick-action buttons: New Request, View Certificates

### Page 3: Unlearning → New Request
- Dataset selector (CIFAR-10, CIFAR-100, Tiny ImageNet)
- Algorithm selector (SISA, Influence, Certified, Hybrid)
- Target record input (by index or upload CSV)
- Submit button → triggers async job

### Page 4: Unlearning → Jobs
- Real-time job progress: `queued → running → verified`
- Celery worker status indicator
- Job details panel (request ID, algorithm, status, timestamps)
- Action buttons: View Certificate, Download Report

### Page 5: Verification Certificate
- Certificate summary (status, algorithm, dataset)
- Merkle root and root hash display
- Proof chain expandable/collapsible
- Ed25519 signature verification badge
- Certificate download (JSON)

### Page 6: Benchmarks
- Comparison chart: Utility Retained vs MIA Accuracy vs Latency
- Algorithm trade-off visualization
- Export: CSV / JSON download
- Leaderboard table with sortable columns

### Page 7: Explainability
- SHAP / LIME / Integrated Gradients feature attributions
- PCA / UMAP embedding visualizations
- Privacy heatmap (data influence map)
- Drift detection panel

### Page 8: Audit Log
- Hash chain view (each entry cryptographically linked)
- Filter by deletion request ID
- Compliance webhook status (GDPR, CCPA, DPDP)
- Immutable ledger with blockchain anchor

### Page 9: Monitoring (Grafana)
- Prometheus metrics at `/metrics`
- Pre-provisioned dashboards:
  - Request rate (RPS) by endpoint
  - Latency percentiles (p50, p95, p99)
  - Unlearning job throughput
  - GPU utilization
  - Error rate by status code
  - Queue depth (Celery)

---

## 6. Presentation Slides Outline (10–15 Slides)

### Slide 1: Title Slide
- VeriUnlearn logo + tagline
- "Verifiable Machine Unlearning with Cryptographic Proofs"
- Presenter name / event

### Slide 2: The Problem
- GDPR Article 17 / CCPA "Right to be Forgotten"
- Standard ML: deleting data ≠ forgetting influence
- MIA success rates on undeleted models (85%+)
- Regulatory fines: up to 4% of global revenue

### Slide 3: What Is Machine Unlearning?
- Definition: removing specific training data's influence from a trained model
- Naive approach: full retrain (expensive, impractical)
- Efficient algorithms: SISA, Influence Functions, Certified Removal
- Challenge: how to *prove* unlearning was done correctly

### Slide 4: VeriUnlearn Architecture
- High-level diagram (Next.js → Nginx → FastAPI → ML Engine)
- Data layer: PostgreSQL, Redis, Qdrant, MinIO
- Async jobs: Celery + Redis broker
- Verification: Merkle tree + Ed25519 signature + zk-SNARK
- Observability: Prometheus, Grafana, Loki

### Slide 5: Deletion Request Flow
- User submits request via API or UI
- Request enters Celery queue
- ML Engine processes: shard retrain / influence compute / certified removal
- Parameter delta computed and verified
- Certificate generated with Merkle proof chain

### Slide 6: Verification Certificate Deep Dive
- 7-step proof chain
- Merkle root (SHA-256) over verification set
- Ed25519 digital signature
- zk-SNARK privacy option
- Certificate fields explained

### Slide 7: Demo — Live Deletion Request
- Login as `demo@veriunlearn.ai`
- Select dataset + algorithm
- Submit deletion request
- Watch job progress
- (If offline: show screenshots)

### Slide 8: Demo — Verification Certificate
- Open completed job
- Inspect proof chain
- Verify Merkle root
- Confirm Ed25519 signature
- Download certificate

### Slide 9: Benchmark Comparison
- Utility Retained: SISA (0.95) > Hybrid (0.92) > Influence (0.88) > Certified (0.82)
- MIA Accuracy: Certified (0.08) < Hybrid (0.12) < Influence (0.15) < SISA (0.18)
- Latency: Certified (fastest) → SISA (medium) → Influence (slow)
- Hybrid Controller: automatic best-algorithm selection

### Slide 10: Explainability & Transparency
- SHAP / LIME / Integrated Gradients attributions
- PCA / UMAP embedding drift visualization
- Privacy heatmap
- Drift detection across model versions

### Slide 11: Audit & Compliance
- Immutable hash chain audit log
- Blockchain-anchored compliance trail
- GDPR / CCPA / DPDP compliance webhooks
- Regulatory-ready evidence package

### Slide 12: Production Deployment
- Docker Compose (development)
- Kubernetes / Helm (production)
- Monitoring: Prometheus + Grafana + Loki
- Alerting: Alertmanager (Slack, PagerDuty)
- Terraform: AWS EKS provisioning

### Slide 13: Security
- TLS/SSL termination (nginx / Traefik)
- JWT authentication + refresh tokens
- API key for ML Engine
- Rate limiting on auth endpoints
- Secrets management (environment variables)
- Container security (non-root, read-only FS)

### Slide 14: Roadmap
- zk-SNARK production integration
- Multi-party verification
- Federated unlearning
- Additional algorithm support
- Regulatory framework partnerships

### Slide 15: Closing
- Value proposition: cryptographic proof of forgetting
- Call to action: Star on GitHub, read docs, try demo
- Contact: `demo@veriunlearn.ai`
- License: Apache 2.0

---

## 7. Presentation Script with Speaker Notes

### Slide 1: Title (30s)
**Speaker:** "Hello everyone. Today I'm excited to present VeriUnlearn — a platform that provides verifiable, cryptographic proof that machine learning models have truly forgotten the data you ask them to forget."

### Slide 2: The Problem (1 min)
**Speaker:** "Privacy regulations around the world — GDPR in Europe, CCPA in California, and emerging AI acts — grant individuals the 'right to be forgotten.' But here's the problem: deleting a row from your training database doesn't remove its influence from your trained model. Membership inference attacks can still determine if a record was used for training, with success rates above 85%. This isn't just a privacy issue — it's a compliance liability."

### Slide 3: What Is Machine Unlearning (1 min)
**Speaker:** "Machine unlearning is the process of removing specific training data's influence from an already-trained model. The naive approach is full retraining, but that's expensive and slow. Efficient algorithms like SISA, Influence Functions, and Certified Removal exist — but the real challenge is proving that unlearning actually happened. Without proof, you're making a claim you can't substantiate."

### Slide 4: Architecture (1.5 min)
**Speaker:** "VeriUnlearn's architecture is designed for verifiability. The frontend (Next.js) communicates through nginx to our FastAPI backend. The backend orchestrates async unlearning jobs via Celery and Redis, while the ML Engine performs the heavy computation — shard retraining, influence computation, or certified removal. All artifacts are stored in PostgreSQL for metadata, Qdrant for vector embeddings, and MinIO for model checkpoints. The magic happens in the verification pipeline: every unlearning operation produces a cryptographic certificate — a Merkle tree hashing a 7-step proof chain, signed with Ed25519, and optionally wrapped in a zero-knowledge proof for privacy."

### Slide 5: Deletion Request Flow (1 min)
**Speaker:** "When a user submits a deletion request, it enters a Celery queue. The ML Engine picks it up and processes it using the selected algorithm. It computes the parameter delta — the difference between the original and unlearned model. An inclusion test verifies the data is no longer influential. Finally, a certificate is generated with a Merkle proof chain, cryptographically linking every step from initialization to submission. The entire process is asynchronous, trackable, and provable."

### Slide 6: Verification Certificate (1.5 min)
**Speaker:** "The certificate is the heart of VeriUnlearn. It contains a 7-step proof chain — from initializing the request to submitting to the certificate chain. Each step produces a hash. These hashes are combined into a Merkle root, signed with Ed25519. Anyone can independently verify this certificate without trusting us — they just need the public key. For privacy-sensitive applications, we support zk-SNARKs, which let you verify unlearning without revealing which data was deleted."

### Slide 7–8: Live Demo (3 min)
**Speaker:** "Let me show you how this works in practice. [Login, submit request, show progress, inspect certificate] — as you can see, the deletion request flows through the system, and within seconds we have a cryptographic certificate proving the data was unlearned."

### Slide 9: Benchmarks (1 min)
**Speaker:** "Different algorithms offer different trade-offs. Certified Removal provides the strongest privacy guarantee with MIA accuracy as low as 8%, and the lowest latency. SISA retains 95% of utility but has higher MIA success. The Hybrid Controller automatically selects the best algorithm based on your requirements — balancing privacy, utility, and latency."

### Slide 10: Explainability (45s)
**Speaker:** "VeriUnlearn doesn't just prove deletion — it explains it. Our explainability module shows SHAP and LIME attributions, embedding visualizations through PCA and UMAP, and a privacy heatmap. You can see exactly how the unlearning operation affected model behavior."

### Slide 11: Audit (45s)
**Speaker:** "Every action is recorded in an immutable audit log — a hash chain where each entry cryptographically links to the previous. This creates a tamper-evident, blockchain-anchored compliance trail. Regulators can independently verify the entire history of deletion operations."

### Slide 12–13: Deployment & Security (1 min)
**Speaker:** "VeriUnlearn deploys via Docker Compose for development or Kubernetes with Helm for production. We provide Terraform modules for AWS EKS provisioning. Security is built-in: TLS termination, JWT authentication, API keys, rate limiting, and container security best practices. Our monitoring stack includes Prometheus, Grafana, Loki, and Alertmanager."

### Slide 14–15: Roadmap & Closing (30s)
**Speaker:** "We're working on production-grade zk-SNARKs, multi-party verification, and federated unlearning. The vision is a world where privacy compliance is not just a promise — it's a mathematical proof. Thank you. Please check out our GitHub, try the demo, and reach out with questions."

---

## 8. Screenshot Descriptions

| Screenshot | Description | What to highlight |
|------------|-------------|-------------------|
| `architecture.png` | Full system architecture diagram | All services, data flow, verification pipeline |
| `login.png` | Login screen with credentials | Demo credentials, SSO options |
| `dashboard.png` | Main dashboard overview | Summary cards, activity feed, health indicators |
| `unlearning-request.png` | New unlearning request form | Dataset selector, algorithm picker, target input |
| `job-progress.png` | Job progress tracking | Status badges, timestamps, Celery metrics |
| `verification-certificate.png` | Certificate detail view | Merkle root, proof chain, signature badge |
| `merkle.png` | Merkle tree visualization | Hash chain, root computation, verification path |
| `benchmarks.png` | Benchmark comparison chart | Algorithm radar/spider chart, export buttons |
| `explainability.png` | Explainability view | SHAP values, UMAP embedding, privacy heatmap |
| `audit-log.png` | Audit log hash chain | Linked entries, filter controls, compliance status |
| `grafana.png` | Grafana monitoring dashboard | Request rate, latency, GPU metrics |
| `settings.png` | System settings / compliance | Webhook configuration, compliance frameworks |

---

## 9. Short Demo Video Script (3–5 Minutes)

### Scene 1 — Opening (0:00–0:30)
**Visual:** VeriUnlearn logo + tagline "Verifiable Machine Unlearning with Cryptographic Proofs"
**Audio:** "VeriUnlearn gives organizations mathematical proof that they've truly forgotten private data. No trust required — just cryptography."

### Scene 2 — The Problem (0:30–1:00)
**Visual:** GDPR/CCPA regulation text → model brain with highlighted data points → MIA attack graph
**Audio:** "Regulations require deletion. But deleting database rows doesn't remove model influence. Membership inference attacks prove it. VeriUnlearn closes this gap with cryptographic verification."

### Scene 3 — Submission (1:00–2:00)
**Visual:** Screen recording: login → New Request → select dataset + algorithm → submit
**Audio:** "Submitting a deletion request is straightforward. Pick your dataset, select an algorithm or let the Hybrid Controller decide, and submit. The system generates a unique request ID and starts async processing."

### Scene 4 — Certificate (2:00–3:00)
**Visual:** Screen recording: open job → View Certificate → expand proof chain → verify signature
**Audio:** "Once complete, the verification certificate shows a 7-step cryptographic proof chain, hashed into a Merkle root and signed with Ed25519. This certificate is independently verifiable — anyone can confirm data was removed without trusting our servers."

### Scene 5 — Benchmarks & Audit (3:00–4:00)
**Visual:** Benchmarks page chart → Audit Log filter → Compliance webhooks
**Audio:** "Compare algorithm trade-offs, export compliance reports, and view the immutable audit trail. Every action is cryptographically linked — regulatory-ready evidence."

### Scene 6 — Closing (4:00–4:30)
**Visual:** Logo + GitHub QR code + "Get Started" button
**Audio:** "VeriUnlearn — cryptographic proof that privacy promises are kept. Try the demo, explore the docs, and join us in building trustworthy AI."

---

## 10. Live Demo Checklist

### Pre-Demo (1 day before)
- [ ] Verify environment is running (`docker compose ps` — all services healthy)
- [ ] Run `./scripts/validate_deployment.sh` — all checks pass
- [ ] Confirm demo data is seeded (`docker compose exec backend alembic upgrade head` + seed script)
- [ ] Test login with demo credentials
- [ ] Submit a test deletion request end-to-end
- [ ] Verify certificate generation and display
- [ ] Check Grafana dashboards are populated
- [ ] Open all demo pages to confirm no errors
- [ ] Prepare offline fallback: `demo/*.png` screenshots ready
- [ ] Test internet connection (for live API docs / external links)
- [ ] Ensure presentation remote / clicker is charged
- [ ] Set screen resolution to 1920×1080 for recording

### Day of Demo
- [ ] Start all services 30 min before: `docker compose --profile monitoring up -d`
- [ ] Run health check: `./scripts/healthcheck.sh`
- [ ] Clear browser cache, open incognito window
- [ ] Pre-load all demo pages in separate tabs
- [ ] Keep terminal open for API demonstrations
- [ ] Close unnecessary applications (notifications, chat)
- [ ] Test microphone / audio if presenting virtually

### During Demo
- [ ] Begin with architecture overview (Slide 4)
- [ ] Login as `demo@veriunlearn.ai`
- [ ] Walk through dashboard summary cards
- [ ] Submit a new deletion request (use Scenario C — `in_progress` to show real-time)
- [ ] Show job progress in Jobs page
- [ ] Open an existing certificate (use Scenario A or D)
- [ ] Expand proof chain — explain each step
- [ ] Verify signature — show independent verification
- [ ] Switch to Benchmarks — compare algorithms
- [ ] Show Explainability view
- [ ] Open Audit Log — filter by request ID
- [ ] Open Grafana — show monitoring dashboards
- [ ] End with summary of what was demonstrated

### Post-Demo
- [ ] Answer Q&A
- [ ] Direct to GitHub for additional resources
- [ ] Share demo credentials for hands-on exploration
- [ ] Collect feedback / questions

### Offline Fallback Plan
- If live environment fails, use screenshot deck (`demo/*.png`)
- Walk through same flow using static images
- Verification certificates available as static JSON
- Architecture diagram and flow charts available

---

*See also: [DEMO_WALKTHROUGH.md](DEMO_WALKTHROUGH.md) (10-min judge walkthrough), [DEMO_VIDEO_OUTLINE.md](DEMO_VIDEO_OUTLINE.md) (video production), `demo/` directory (static assets).*
