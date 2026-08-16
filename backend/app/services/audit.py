"""Append-only, hash-chained audit trail.

Every event is linked to the previous event hash. Tampering with any stored
event breaks every subsequent link, which ``verify_chain`` detects by
recomputing the chain from the earliest event. The chain link is a pure
function of *stored* data (previous hash, event type, payload, creation
timestamp) so verification never depends on transient state.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditEvent
from app.repositories.audit_repo import AuditRepository
from app.services.crypto import hash_chain_link


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AuditRepository(session)

    async def log(
        self,
        *,
        event_type: str,
        actor: str,
        subject: str | None = None,
        certificate_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> AuditEvent:
        prev_hash = await self.repo.latest_hash()
        # Naive UTC: SQLite round-trips naive datetimes unchanged, so the chain
        # can be recomputed identically from stored data during verification.
        created_at = datetime.now(timezone.utc).replace(tzinfo=None)
        event_hash = hash_chain_link(
            prev_hash, event_type, payload or {}, created_at.isoformat()
        )
        event = AuditEvent(
            event_type=event_type,
            actor=actor,
            subject=subject,
            certificate_id=certificate_id,
            prev_hash=prev_hash,
            event_hash=event_hash,
            payload=payload or {},
            created_at=created_at,
        )
        return await self.repo.add(event)

    async def verify_chain(self) -> dict[str, Any]:
        """Recompute the chain; return integrity verdict + first broken link."""
        events = await self.repo.ordered_events()
        prev: str | None = None
        broken_at: str | None = None
        for event in events:
            recomputed = hash_chain_link(
                event.prev_hash, event.event_type, event.payload, event.created_at.isoformat()
            )
            if event.prev_hash != prev or recomputed != event.event_hash:
                broken_at = event.id
                break
            prev = event.event_hash
        return {
            "verified": broken_at is None,
            "event_count": len(events),
            "broken_event_id": broken_at,
            "head_hash": prev,
        }
