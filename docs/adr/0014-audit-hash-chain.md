# ADR-0014: Tamper-evident SHA-256 audit hash chain + blockchain anchoring

- **Status:** Accepted (2026-06)

## Context

Compliance evidence is only credible if the audit log cannot be silently edited after the
fact. Regulators may also want an external, time-stamped anchor.

## Decision

Every `audit_events` row stores `previous_event_hash` and a computed `event_hash`
(SHA-256 over the event payload + previous hash). `audit_chain_heads` tracks the latest hash
and Merkle root. `BlockchainAnchoringService.anchor_chain()` periodically anchors the Merkle
root via `SimulatedBlockchain`; a Celery beat task (`audit.anchor_chains`) runs every 6h.
Endpoint: `POST /audit/chain/anchor`.

## Consequences

- ✅ Any edit to a historical event breaks the chain (detectable on re-validation).
- ✅ External anchoring provides non-repudiation timestamp.
- ❌ `SimulatedBlockchain` is a stand-in; real chains (Ethereum/Polygon/Hyperledger) require
  `app.future.blockchain.providers` + gas/cost management.
- ❌ Append-only log grows unbounded; retention policy must archive, not delete, evidence.

## Alternatives considered

- Plain append-only log without hashing (rejected: detectable but not cryptographically).
- Always-on public chain writes (rejected: gas cost + latency for high-frequency events).
