# VeriUnlearn — Risk Identification & Mitigation

## Risk Matrix

| ID | Risk | Likelihood | Impact | Severity | Mitigation |
|---|---|---|---|---|---|
| R-001 | **False unlearning**: system reports deletion without actual model change | Low | Critical | Critical | SISA retraining produces new model hash; verification pipeline measures weight distance, gradient distance, cosine similarity; MIA must confirm reduced attack efficacy |
| R-002 | **Utility collapse**: unlearning destroys model quality | Medium | High | High | Utility evaluator tracks accuracy/precision/recall/F1; configurable retention threshold; adaptive controller selects least-disruptive algorithm |
| R-003 | **Private key compromise**: signing key leaked | Low | Critical | Critical | Key stored with 0600 permissions; environment isolation; future support for HSM integration; key rotation procedure documented |
| R-004 | **MIA false confidence**: attack metrics don't reflect actual privacy leakage | Medium | High | High | Multiple MIA variants; shadow model methodology; confidence calibration; future differential privacy integration |
| R-005 | **SISA shard imbalance**: uneven data distribution across shards | Medium | Medium | Medium | Random assignment with periodic rebalancing; configurable shard count; monitoring for shard size variance |
| R-006 | **Algorithm selection failure**: adaptive controller chooses suboptimal algorithm | Medium | Medium | Medium | Fallback to SISA as default; cost estimation validation; manual override option |
| R-007 | **GPU memory exhaustion**: model too large for available VRAM | Medium | High | High | 4-bit quantization; gradient checkpointing; configurable device map; CPU fallback |
| R-008 | **Database migration conflicts**: schema changes break production data | Low | High | High | Alembic migrations with version control; staging environment testing; rollback scripts |
| R-009 | **Token bucket overflow**: JWT or API token leakage | Medium | Medium | Medium | Short access token expiry (30 min); refresh token rotation; rate limiting |
| R-010 | **Certificate verification failure**: external verifier cannot validate proof | Low | High | High | Certificates are self-contained JSON documents; include public key; verification instructions documented |
| R-011 | **Embedding-data dissociation**: deleted user's embeddings remain in vector store | Medium | High | High | Embeddings tagged with user_id; Qdrant payload filtering; deletion cascades to vector store |
| R-012 | **Concurrent unlearning requests**: race conditions in model state | Low | Medium | Medium | Single-threaded Celery worker for unlearning; optimistic locking on model version; queue serialization |
| R-013 | **Insufficient test coverage for ML paths**: model training/unlearning untested | Medium | High | High | Integration tests for full pipeline; ML validation fixtures; CI with GPU runners |
| R-014 | **Base model license changes**: open-weight model license prohibits deployment | Low | Medium | Medium | Abstracted model interface; multiple supported model families (Qwen, Phi, Llama, Mistral) |
| R-015 | **Regulatory requirements evolve**: new deletion standards emerge | Medium | Medium | Medium | Modular algorithm interface; extensible verification pipeline; policy-driven configuration |

## Detailed Risk Analysis

### R-001: False Unlearning

**Context**: The most critical risk. If the system claims data has been unlearned but the model is unaffected, the entire platform loses credibility.

**Detection**:
- Before/after model hash comparison must show difference
- Weight distance > 0.0 after unlearning
- MIA accuracy must decrease post-deletion
- All metrics logged to `UnlearningResult`

**Mitigation**:
- SISA physically retrains the shard with deleted samples removed
- New adapter is saved, producing a new SHA-256 hash
- Merkle tree includes model hashes and MIA results
- Certificate encodes all verification data

### R-002: Utility Collapse

**Context**: Retraining on reduced data may degrade model quality below acceptable thresholds.

**Detection**:
- Before/after accuracy, precision, recall, F1 comparison
- Utility retention percentage computed

**Mitigation**:
- Configurable retention threshold (default: 80%)
- Adaptive controller selects algorithm with least expected impact
- Small deletions use certified removal (no retraining needed)
- Fallback: abort unlearning if utility drops below threshold

### R-003: Private Key Compromise

**Context**: Ed25519 signing key used for certificate signatures. If compromised, certificates can be forged.

**Detection**:
- Unexpected certificate signatures
- Audit log anomalies

**Mitigation**:
- Key file permissions: 0600 (owner read/write only)
- Key stored outside web root
- Environment-specific keys (dev/staging/prod separate)
- Future: HSM integration, key rotation API

### R-004: MIA False Confidence

**Context**: Membership Inference Attacks may give misleading results if:
- The attack model is poorly calibrated
- The shadow model doesn't match the target
- Dataset distribution shifts after deletion

**Detection**:
- Cross-validation of MIA across multiple attack models
- Confidence score monitoring
- Periodic calibration checks

**Mitigation**:
- Multiple MIA variants (loss-based, confidence-based)
- Shadow model trained on held-out data
- Attack results include confidence intervals
- Future: differential privacy integration for formal guarantees

## Monitoring & Alerting

Critical risks monitored via:
- Prometheus metrics for MIA accuracy, utility retention, unlearning latency
- Grafana dashboards for trend analysis
- Structured logging of every unlearning operation with correlation IDs
- Health check alerts for service degradation
- Anomaly detection on weight distance and cosine similarity distributions

## Incident Response

| Severity | Response | SLA |
|---|---|---|
| Critical (R-001, R-002, R-003) | Immediate halt of unlearning pipeline; root cause analysis; full audit | 1 hour |
| High (R-007, R-010, R-011) | Engineering review; hotfix deployment | 4 hours |
| Medium (R-005, R-006, R-012) | Scheduled fix in next sprint | 1 week |
| Low (R-014, R-015) | Documented in roadmap | Next release |

## Assumptions

1. The base model (Qwen2.5-1.5B-Instruct) remains frozen and its license permits commercial deployment.
2. GPU resources are available for training and inference (NVIDIA CUDA-capable).
3. PostgreSQL, Redis, Qdrant, and MinIO services are available with the specified configurations.
4. The signing key is generated once per deployment and manually backed up.
5. The platform is deployed in a trusted network environment with appropriate firewall rules.
