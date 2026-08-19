# VeriUnlearn — Glossary

Terminology used across the project, documentation, and the IEEE paper.

---

| Term | Definition |
|---|---|
| **Audit trail** | Append-only, hash-chained log of audited events; tampering breaks the chain and is detected. |
| **Certificate** | RSA-signed artefact binding a deletion's pre/post Merkle roots, hashes, method, and bound. |
| **Certified removal** | Newton-step weight update with a provable bound on prediction drift after deletion. |
| **Compliance snapshot** | Persisted point-in-time GDPR/DPDP score report (trendable, exportable). |
| **Deletion request** | A user-initiated unlearning job (scope: records/chat/dataset/identity; method: retrain/certified/influence). |
| **Embedding** | Vector representation of a record/chunk in the vector store; removed on deletion. |
| **GDPR Art. 17** | EU right to erasure — the legal basis VeriUnlearn operationalizes. |
| **DPDP Act 2023** | Indian Digital Personal Data Protection Act — consent + erasure obligations. |
| **Footprint** | Full memory profile of an identity: record ids, embeddings, clusters, affected neurons, influence stats. |
| **Identity key** | Stable identifier (name, email, phone, Aadhaar/PAN, record/chat id) used for privacy search. |
| **Impact analysis** | Pre-deletion estimate: affected shards, embeddings, vectors, est. retrain time. |
| **Influence function** | First-order measure of each record's contribution to the model. |
| **Merkle root** | Root hash of a tree whose leaves are record hashes; a deterministic change after deletion is the deletion proof. |
| **MIA** | Membership-inference attack — does an adversary learn whether a record was in training? |
| **Model inversion** | Attack reconstructing a prototypical training input from model outputs. |
| **Poisoning** | Training-time manipulation (backdoor/label-flip/gradient) that unlearning should remove. |
| **RBAC** | Role-based access control — five roles × scoped permissions. |
| **SISA** | Sharded, Isolated, Sliced, Aggregated training: shard-level retraining bounds deletion cost. |
| **Shard** | One partition of a dataset trained into an independent sub-model. |
| **Tombstone** | Marker that a record is deleted but kept (hashed) so Merkle roots stay recomputable. |
| **Unlearning** | Removing a record's influence from a trained model without full retraining. |
| **Vector store** | Store for embeddings (in-memory in dev, Qdrant in production). |
| **Verification** | The 8-check engine proving a deletion happened and is consistent. |
| **ZK-style commitment** | Commitment scheme providing deletion evidence without revealing deleted content. |
