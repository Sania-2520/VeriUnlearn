# Compliance Guide

VeriUnlearn helps organizations meet data-protection obligations with evidence, not promises.
This guide maps platform capabilities to common regulations and to the compliance API.

---

## Regulations Covered

| Regulation | Key articles | VeriUnlearn capability |
|------------|--------------|------------------------|
| **GDPR** (EU) | Art. 17 (erasure), Art. 16 (rectification), Art. 32 (security) | Unlearning requests tagged `gdpr_article`, deletion certificates, audit chain |
| **CCPA/CPRA** (California) | Right to delete, right to know | Consent withdrawal → auto-deletion, lineage export |
| **DPDP Act 2023** (India) | Sec. 8 (consent), Sec. 9 (withdrawal) | Consent lifecycle, withdrawal cascade to unlearning |
| **EU AI Act** | Risk management, record-keeping | RiskAssessment, GovernanceScore, immutable audit |

Configure contacts for regulator notifications:

```bash
COMPLIANCE_GDPR_CONTACT=      # DPO email
COMPLIANCE_AI_ACT_CONTACT=    # AI Act representative
```

---

## Compliance API

```http
GET  /api/v1/compliance/settings
POST /api/v1/compliance/settings        # GDPR/CCPA/DPDP toggles, retention windows

POST /api/v1/compliance/webhooks        # register outbound webhook (HMAC-SHA256)
POST /api/v1/compliance/webhooks/{id}/test
GET  /api/v1/compliance/webhooks/{id}/logs
POST /api/v1/compliance/webhooks/{id}/pause
```

- Webhooks are signed with **HMAC-SHA256** and auto-disabled after repeated delivery
  failures (Celery `retry_failed_webhooks`, beat every 5 min).
- `ComplianceWorkflow` / `ComplianceReport` model the reporting lifecycle
  (`draft → generated → reviewed → published`).

### GDPR endpoints

```http
POST /api/v1/gdpr/export          # data portability export
DELETE /api/v1/gdpr/account       # account + derived-data erasure
```

---

## Webhook Payload Example

```json
{
  "event": "unlearning.completed",
  "request_id": "c1d2e3f4-5678-90ab-cdef-1234567890ab",
  "certificate_hash": "3b5d...",
  "merkle_root": "9f86d0...",
  "timestamp": "2026-07-17T09:25:44Z",
  "signature": "hmac-sha256=..."
}
```

Verify the signature on your side with the shared secret configured in the webhook.

---

## Audit Trail & Evidence

Every compliance-relevant action is appended to the hash-chained `audit_events` table
(SHA-256 `previous_event_hash` → `event_hash`, unique). The chain head is periodically
anchored (blockchain) via `POST /audit/chain/anchor`. This gives auditors tamper-evident
evidence that a deletion was requested, executed, verified, and certified.

---

## Retention Policies

`RetentionPolicy` + `RetentionService` enforce data retention windows and auto-purge expired
records (`retention.enforced`, `data.purged` events). Set windows per data class in
compliance settings.

---

## Reporting

Generate a compliance report for a period:

```http
POST /api/v1/compliance/reports
{ "report_type": "gdpr", "report_period_start": "2026-01-01", "report_period_end": "2026-06-30" }
```

Reports include `overall_score`, `findings`, `recommendations`, and `risk_score`, and can be
exported (CSV/JSON/PDF) via `ExportService`.

---

## Limitations & Caveats

- VeriUnlearn proves model-level erasure of the *forget set*; it cannot retroactively purge
  data already exfiltrated or in third-party caches. Combine with access controls.
- Blockchain anchoring is simulated by default (see [ADR-012](adr/0012-zero-knowledge-proofs.md)).
- Compliance workflows are advisory unless enforcement is enabled; legal sign-off remains
  the organization's responsibility.
- Certificates are Ed25519 (not post-quantum).
