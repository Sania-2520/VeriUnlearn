# Frequently Asked Questions

---

## General

### What is VeriUnlearn?

VeriUnlearn is an end-to-end framework for **verifiable machine unlearning**. It enables
organisations to delete (unlearn) specific user data from trained ML models and then
**prove cryptographically** that the deletion actually happened — with Merkle tree proofs,
Ed25519-signed certificates, and zk-SNARK verification.

### How does it differ from simply retraining a model?

Retraining from scratch is a valid unlearning approach but is expensive. VeriUnlearn
provides **four unlearning algorithms** (SISA, Influence Functions, SCRUB, Fine-Tune
Forgetting) alongside a Retrain baseline, plus cryptographic proof infrastructure.
The evaluation framework lets you **measure and compare** the trade-off between
unlearning speed, model utility, privacy resistance, and proof verifiability.

### Is VeriUnlearn a production system or a research prototype?

Both. The core unlearning + verification pipeline is production-ready (FastAPI backend,
Docker/K8s deployment, RBAC, audit trail). The evaluation framework and zk-SNARK proof
service are research-quality. See [docs/FUTURE_ROADMAP.md](FUTURE_ROADMAP.md) for the
phased roadmap.

---

## Unlearning Algorithms

### What algorithms are supported?

| Algorithm | Type | Guarantee |
|-----------|------|-----------|
| **Retrain** | Baseline | Gold-standard (full retraining) |
| **SISA** | Exact | Shard-based exact removal |
| **SCRUB** | Approximate | Soft-target distillation |
| **Influence Functions** | Approximate | Gradient-based estimation |
| **Fine-Tune Forgetting** | Approximate | Gradient ascent + fine-tune |
| **Certified Removal** | Exact | ε-differential privacy |
| **Hybrid Controller** | Adaptive | Automatic algorithm selection |

The evaluation framework benchmarks the first five. The production ML Engine also
includes Certified Removal and Hybrid Controller.

### How long does unlearning take?

Depends on the algorithm and dataset size. From our benchmarks:

| Algorithm | MNIST (10% forget) | Notes |
|-----------|---------------------|-------|
| Retrain | ~0.3 s | Full retraining from scratch |
| SISA | ~0.1 s | Shard deletion only |
| Influence Functions | ~0.6 s | Gradient computation |
| Fine-Tune Forgetting | ~0.9 s | Gradient ascent + fine-tune |
| SCRUB | ~13.8 s | Iterative distillation |

### What happens if unlearning fails?

The system supports **rollback**: if an unlearning operation fails or produces
degraded results, the previous model checkpoint is restored. The `UnlearningService`
validates forget quality and utility retention before committing the update. See
[machine-unlearning-guide.md](machine-unlearning-guide.md) for details.

### How is forget quality measured?

Two primary signals:
1. **Forget accuracy drop** — accuracy on the forget set before vs. after unlearning
   (higher drop = better forgetting)
2. **Memorization score** — difference between member and non-member loss distributions
   (should decrease after unlearning)

---

## Verification & Cryptographic Proofs

### How do I verify a certificate offline?

Deletion certificates are self-contained JSON objects signed with Ed25519. You can verify
them with the public key:

```bash
# Via the API
POST /api/v1/verify/proofs/verify
{ "certificate_id": "<id>" }

# Or verify the Ed25519 signature directly using the verification key
# embedded in the certificate
```

See [verification-guide.md](verification-guide.md) for the full Merkle → Ed25519 → zk-SNARK
verification flow.

### What cryptographic primitives are used?

| Primitive | Algorithm | Library | Purpose |
|-----------|-----------|---------|---------|
| Digital signatures | Ed25519 | PyNaCl | Certificate authenticity |
| Hashing | SHA-256 | `hashlib` | Artifact fingerprinting |
| Merkle trees | SHA-256 | Custom | Batch inclusion proofs |
| API-key hashing | SHA-384 | `hashlib` | Secure key storage |
| zk-SNARKs | Groth16-style | Custom | Zero-knowledge inclusion proof |

### What is a trust score?

A weighted composite of four normalised components:
- Forget quality (30%)
- Utility retention (35%)
- Privacy reduction (25%)
- Efficiency (10%)

Computed by `MetricsComputer` in the evaluation framework and by `VerificationService`
in the production pipeline.

---

## Setup & Requirements

### What are the system requirements?

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Python | 3.12+ | 3.12+ |
| RAM | 4 GB | 8 GB+ |
| Disk | 2 GB | 10 GB (with datasets) |
| GPU | Not required | CUDA-capable (accelerates training) |
| OS | Linux, macOS, Windows | Linux |

### Docker vs local development?

- **Docker** (`./scripts/setup.sh`): One-command setup with all 14 services. Best for
  getting started quickly and production deployment.
- **Local dev** (`make install` + `docker compose up -d postgres redis qdrant minio`):
  Faster iteration, better debugging. Requires manually starting services.

### Do I need a GPU?

**No.** The evaluation framework runs entirely on CPU (scikit-learn models). GPU
acceleration is needed for:
- LoRA fine-tuning of transformer models via the ML Engine
- Large-scale training on CIFAR-10 and beyond
- zk-SNARK proof generation (prototype)

---

## API

### How do I authenticate?

```bash
# Register
POST /api/v1/auth/register
{ "email": "user@example.com", "password": "..." }

# Login → returns access_token (15 min) + refresh_token (7 days)
POST /api/v1/auth/login
{ "email": "user@example.com", "password": "..." }

# Use in subsequent requests
Authorization: Bearer <access_token>
```

MFA (TOTP) is available for additional security.

### What are the rate limits?

| Scope | Limit |
|-------|-------|
| Auth endpoints | 5 req/s |
| API endpoints | 30 req/s |
| Benchmark endpoints | 5 req/s |

### What error codes should I expect?

| Code | Meaning |
|------|---------|
| 400 | Bad request (validation error) |
| 401 | Unauthenticated (missing/invalid token) |
| 403 | Forbidden (insufficient RBAC role) |
| 404 | Resource not found |
| 409 | Conflict (e.g., duplicate registration) |
| 422 | Unprocessable entity (ML engine validation) |
| 429 | Rate limited |
| 500 | Internal server error |

---

## Compliance

### Does VeriUnlearn support GDPR?

Yes. Key GDPR alignment:
- **Art. 17 (Right to Erasure):** Unlearning requests → model retraining → deletion
  certificate with cryptographic proof
- **Art. 32 (Security):** Audit trail with SHA-256 hash chain, blockchain anchoring
- **Data portability:** `POST /api/v1/gdpr/export`
- **Account erasure:** `DELETE /api/v1/gdpr/account`

### CCPA / CPRA support?

Yes. Consent withdrawal triggers automatic data deletion. Lineage export available for
"right to know" requests. See [compliance-guide.md](compliance-guide.md).

### DPDP Act 2023 (India)?

Yes. Consent lifecycle management with withdrawal cascading to unlearning. Configurable
via `COMPLIANCE_GDPR_CONTACT` and related environment variables.

### How are compliance webhooks configured?

```http
POST /api/v1/compliance/webhooks
{ "url": "https://your-audit-system/webhook", "events": ["unlearning.completed"] }
```

Webhooks are signed with HMAC-SHA256 and auto-disabled after repeated failures.

---

## Security

### How are secrets managed?

- All secrets stored in environment variables (never committed)
- `.env` file is gitignored; `.env.example` has placeholder values only
- Production: GitHub Secrets or AWS Secrets Manager
- Kubernetes: secrets created via Terraform/Kustomize
- The secret validator **rejects placeholder keys** when `APP_ENV=production`

### What is the threat model?

| Threat | Mitigation |
|--------|-----------|
| Unauthorized API access | JWT tokens (15 min TTL) + refresh (7 days) |
| Credential theft | MFA (TOTP), API key scoping |
| Data breach | AES-256 at rest, TLS in transit |
| ML model extraction | Rate limiting, input validation |
| Membership inference | Differential privacy, certified removal |
| Privilege escalation | RBAC with 5 roles |

### What RBAC roles exist?

| Role | Access Level |
|------|-------------|
| `viewer` | Read-only dashboards |
| `member` | Own resources, chat, explainability |
| `unlearning_auditor` | Unlearning requests, proof verification |
| `compliance_officer` | Webhooks, compliance settings, audit logs |
| `admin` | Full access including user management |

See [security-guide.md](security-guide.md) for full details.

---

## Benchmarks & Evaluation

### How do I reproduce published results?

```bash
# Quick verification (30 seconds)
python -m evaluation.test_framework

# Reproduce the reference MNIST results
python -m evaluation.run_all --datasets mnist --num-runs 3 --seed 42

# Full benchmark suite
python -m evaluation.run_all
```

All results include a config fingerprint, hardware snapshot, and seed configuration
for exact reproducibility. See [evaluation/README.md](../evaluation/README.md) for details.

### How do I add a custom dataset?

1. Create a loader in `evaluation/datasets.py` that returns a `DatasetBundle`
   (train/test `Dataset` objects + label lists)
2. Add a `DatasetConfig` entry with the correct `name`, `num_classes`, and `input_shape`
3. Register the name in `load_by_name()` and the CLI choices in `run_all.py`
4. Run the smoke test: `python -m evaluation.test_framework`

### How do I add custom metrics?

Use the `MetricsComputer.full_report()` API or add a new `compute_<name>()` function
in `evaluation/metrics.py`. The `MetricsComputer` orchestrator automatically aggregates
all metrics into a single report dict.

---

## Troubleshooting

### Evaluation framework won't import

```bash
# Ensure you're running from the project root
cd VeriUnlearn
python -m evaluation.test_framework

# Or add to PYTHONPATH
export PYTHONPATH=$(pwd):$PYTHONPATH
```

### CIFAR-10 download fails

The dataset is ~170 MB. On restricted networks:
- Use MNIST only: `python -m evaluation.run_all --datasets mnist`
- Pre-download to `evaluation/data/cifar-10-python.tar.gz`
- Use a proxy: `export HTTPS_PROXY=http://proxy:port`

### SCRUB is too slow

SCRUB runs iterative soft-target distillation which is 10–15× slower than other
algorithms. Options:
- Reduce forget ratio: `--forget-ratios 0.01`
- Reduce epochs in `TrainingConfig`
- Skip SCRUB: `--algorithms retrain sisa influence_functions fine_tune_forgetting`

### Out of memory

- Reduce `max_samples`: `--max-samples 2000`
- Reduce batch size in `TrainingConfig`
- For SISA, reduce `num_shards` in `SISAConfig`

### Figures not generated

Ensure matplotlib and seaborn are installed:

```bash
pip install matplotlib seaborn
```

Or skip figures: `--no-figures`

### Full troubleshooting

See [troubleshooting-guide.md](troubleshooting-guide.md) for backend, ML Engine,
Celery, frontend, Docker, and other infrastructure issues.
