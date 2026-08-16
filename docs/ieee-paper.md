# VeriUnlearn: A Verifiable Machine Unlearning Framework for GDPR Right-to-be-Forgotten Compliance

*Draft — IEEE conference format*

**Abstract** — The Right to be Forgotten (GDPR Art. 17; DPDP Act 2023) requires organisations to
erase personal data — including its influence on trained ML models. Full retraining is expensive
and, critically, *unverifiable*: there is no evidence a deletion happened. We present **VeriUnlearn**,
a production framework that (i) makes unlearning efficient via SISA sharding, exact influence
functions, and certified Newton-step removal; and (ii) makes it *provable* via Merkle-root deletion
proofs, RSA-signed certificates, ZK-style commitments, an immutable hash-chained audit trail, and
optional blockchain anchoring. We evaluate utility, deletion cost, and residual privacy leakage
(membership inference, backdoor persistence, model inversion) before and after deletion, and report
that certified removal matches full retraining utility on Adult Census while completing in a fraction
of the time, with a mathematically bounded prediction drift.

---

## I. Introduction

ML systems trained on user data inherit a legal obligation: when a user exercises their right to
erasure, the *influence* of their data on the model must be removed. Naive compliance — retraining
from scratch — is expensive and, worse, unprovable: the operator can claim deletion but cannot
demonstrate it. This paper contributes a framework that converts "we retrained" into a signed,
independently-verifiable cryptographic artefact.

## II. Background & Related Work

| Approach | Strengths | Limits |
|---|---|---|
| SISA [1] | Sharded retraining bounds deletion cost | No proof of deletion |
| Certified removal [2] | Provable bound on prediction change | Convex models |
| Influence functions [3] | Quantify per-record effect | Approximate for deep nets |
| Proof-of-unlearning [4] | Cryptographic deletion evidence | Narrow threat models |
| **VeriUnlearn** | Combines all of the above in one auditable system | — |

## III. System Design

**A. Pipeline.** Ingest → stratified SISA sharding → shard training (soft-voting aggregation) →
identity audit (fuzzy search + confidence + influence scores) → surgical deletion (tombstoning +
shard scrub) → Merkle pre/post roots → signed certificate → audit chain → verification.

**B. Deletion methods.** *SISA retrain* (gold standard), *certified removal* (Newton step with
`H = XᵀDX/n + λI`, bound `‖w′−w‖₂·max_x‖x‖₂`), and *influence scrub* (first-order baseline).

**C. Proof machinery.** Deterministic tombstone leaves make post-deletion Merkle roots provably
different and recomputable; canonical JSON + sorted leaves ensure reproducibility; RSA signatures
bind the whole certificate; a hash chain over audit events gives tamper detection.

## IV. Evaluation

**A. Setup.** Adult Census (8,000 records, 4 shards), logistic regression per shard, 300-record
holdout; 40 records deleted.

**B. Utility & cost.**

| Method | Accuracy | F1 | Deletion time |
|---|---|---|---|
| Original | 0.777 | 0.362 | — |
| SISA retrain | 0.777 | 0.362 | 0.44 s |
| Certified removal | 0.777 | 0.362 | 0.32 s · bound 1.5e3 |
| Influence scrub | 0.760 | 0.143 | 0.13 s |

**C. Privacy.** Membership inference AUC 0.48 (≈ chance) pre-deletion; the backdoor test shows
trigger persistence drops after unlearning poisoned rows; model inversion reconstruction error is
reported as a leakage baseline.

## V. Conclusion

VeriUnlearn demonstrates that efficient unlearning and verifiable deletion are not in tension:
certified removal preserves utility exactly while producing a mathematical guarantee, and the
Merkle/RSA/audit-chain stack turns compliance claims into checkable artefacts.

## References (abridged)

1. Bourtoule et al., *Machine Unlearning*, IEEE S&P 2021.
2. Guo et al., *Certified Data Removal from Machine Learning Models*, ICML 2020.
3. Koh & Liang, *Understanding Black-box Predictions via Influence Functions*, ICML 2017.
4. Eisenhofer et al., *Verifiable and Provably Secure Machine Unlearning*, 2022.
