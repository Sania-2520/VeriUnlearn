# VeriUnlearn — User Manual

A walkthrough of the platform from an end user's perspective: searching for personal data,
running unlearning requests, verifying deletion, and using the research tools.

> Demo logins (created by the seed): `admin@veriunlearn.dev / admin12345` (admin),
> plus operator/researcher/auditor/viewer accounts. Your administrator can create accounts.

---

## 1. Signing in

1. Open the app (default `http://localhost:3000`).
2. Click **Sign in** and enter your email + password.
3. The left sidebar shows only the pages your **role** can access
   (admin → everything; viewer → read-only dashboards).

## 2. Dashboard

The dashboard summarizes the whole platform: compliance score, deletion-request volume,
average deletion time, verification success rate, certificate count, privacy risk, system
health, and storage/GPU usage. Numbers refresh automatically.

## 3. Privacy Auditor — find personal data

1. Open **Privacy Auditor**.
2. Type a name, email, phone, Aadhaar/PAN number, or record/chat id (e.g. `maya`).
   Optionally use structured filters (dataset, identity key).
3. **Search** — every dataset/shard is scanned; results show where the identity appears,
   with confidence and sensitivity.
4. Click a record to open its **viewer** (text, metadata, file, dataset, chunk/embedding/hash),
   or open the **footprint** to see clusters, neurons, embeddings, influence scores and
   deletion eligibility.
5. **Scan** runs a full privacy report (PII categories + severity) persisted in history.
6. **Export** downloads the search result as JSON.

## 4. Surgical Unlearning — delete data

1. Open **Surgical Unlearning**.
2. Choose scope: **records** (by id), **chat** (conversation), **dataset**, or an identity.
3. Run **Impact analysis** first — it estimates affected shards, embeddings and retrain time.
4. Pick a method:
   - **SISA retrain** — retrain only the affected shards (gold standard).
   - **Certified removal** — provable Newton-step removal with a mathematical bound.
   - **Influence scrub** — first-order gradient scrub (baseline).
5. **Execute** — watch the pipeline: tombstoning → shard scrub → Merkle roots → certificate.
6. The **before/after** comparison shows what changed; the deletion report is saved to history.

## 5. Verification & Certificates

- **Verification** runs the 8-check deletion verification (records, embeddings, vectors,
  versions, Merkle, signature, audit chain, consistency) and produces a persisted report.
- **Certificates** lists signed deletion certificates. Download **JSON** or **PDF**.
- **Verify** independently checks a certificate's hash, signature, roots and audit chain.

## 6. Compliance

Shows live **GDPR Article 17** and **DPDP Act 2023** posture: scores, open/completed
requests, average response time, risk level, certificate integrity.
**Generate snapshot** persists a compliance report; **CSV / JSON** download the history.

## 7. Audit Trail

Hash-chained event log of every audited action (searches, deletions, role changes, scans).
**Verify chain** recomputes the hashes and confirms the log hasn't been tampered with.

## 8. Attack Lab & Benchmark (research users)

- **Attack Lab** — membership inference (MIA), model inversion, data extraction, and
  poisoning/backdoor probes against a trained model, before/after unlearning.
- **Benchmark** — run the non-destructive 6-method comparison (original, full retrain,
  SISA, influence, certified, VeriUnlearn) and export CSV/JSON/Excel.

## 9. Research Hub (researchers)

Experiments (versioned, with environment snapshots), the research dashboard (forget quality,
privacy gain, retention, verification overhead, compliance readiness), attack suite results,
and a live performance monitor.

## 10. Notifications

The bell in the header shows unread events (deletion completed, verification completed,
certificate ready, experiment finished, system errors). Open **Notifications** to mark items
read; email copies are delivered if your administrator enabled SMTP.

## 11. Developer Portal (API access)

Issue an **API key** (name + quota), copy it once, then call the API:

```bash
curl -H "X-API-Key: vk_…" http://localhost:8000/api/v1/notifications
```

Track usage and revoke keys from the same page.

## 12. Getting help

- See [`troubleshooting.md`](troubleshooting.md) for common problems.
- Ask your administrator for role changes or API access.
- Report issues to the project repository (see [`CONTRIBUTING.md`](../CONTRIBUTING.md)).
