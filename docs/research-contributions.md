# Research Contributions

## 1. Verifiable LoRA Adapter Unlearning

Per-identity LoRA adapters (PEFT) are trained independently on top of a frozen base model
(Llama/Mistral/Phi/TinyLlama/Qwen — see `app/services/models/llm_lora.py`). Unlearning a user means:

1. `unload()` / `delete_adapter(identity)` — the adapter is removed *independently*; every other
   adapter and the base weights are untouched; the removal is recorded in the audit trail.
2. Optional negative-gradient scrub on the base model for residual influence.

Because each identity owns a *separate, removable artifact*, deletion is surgical and its cost is
proportional to one adapter, not the model. The runnable slice uses the linear backend; the LoRA
backend activates when the optional deps (`transformers`, `peft`) are installed.

## 2. Merkle-tree Audit Verification

Every dataset is covered by a SHA-256 Merkle tree over canonical record leaves. On deletion,
affected leaves are replaced by **deterministic tombstone leaves**
`SHA256(record_id ‖ content_hash ‖ "deleted")`. Consequences:

- **Pre/post roots differ** iff the data was actually removed (soundness of the proof).
- **Post roots are recomputable** from live DB state, so a verifier can independently confirm that
  every hash claimed in a certificate is still tombstoned — without trusting the issuer.
- The certificate binds pre-root, post-root, model weights hash, and method under one RSA signature.

## 3. Blockchain-backed Compliance Certificates

Certificate content hashes are registered to `contracts/DeletionRegistry.sol`
(`register(bytes32)`), giving each deletion a public, timestamped, third-party-verifiable anchor.
The service (`app/services/blockchain.py`) submits via `web3` when configured; otherwise it falls
back to a local immutable ledger — the interface is identical, so the deployment is a config change.

## 4. Poisoning-resistant Unlearning

The Attack Lab's backdoor test poisons a shard (trigger feature + flipped labels), verifies the
trigger fires, then unlearns the poisoned rows and measures whether the trigger still fires.
SISA shard retraining removes poisoned influence outright; the ratio
`trigger_after / trigger_before` quantifies persistence. Membership inference and model inversion
complete the residual-leakage evaluation.

---

### Method math (linear backend)

**Influence.** For parameters `w`, averaged regularised logistic loss with Hessian
`H = XᵀDX/n + λI` (D = diag(p(1−p))), the influence of point `z` on the model is
`I(z) = −H⁻¹ ∇ℓ(z)`.

**Certified removal (Guo et al., ICML 2020).** Removing `{z_i}` updates weights by the Newton step
`w′ = w − H⁻¹ (Σ ∇ℓ(z_i))/n` — an exact step toward the retrained optimum for convex losses — and
the certificate stores the certified bound `|f_{w′}(x) − f_w(x)| ≤ ‖w′−w‖₂‖x‖₂` for all inputs `x`.
Empirically (Adult Census, 40 records, 300 eval): certified removal preserves holdout accuracy
exactly (0.7767 = retrained) in ~0.3 s with a finite bound, versus ~0.44 s for shard retraining.

**Approximate scrub (influence baseline).** First-order correction `w′ = w − η·Σ∇ℓ(z_i)` with
`η = (n_removed/n_shard)·‖w‖/‖Σ∇ℓ‖` — fastest, slightly reduced utility (0.76), no certificate bound.
