import json
import logging
import os
import threading
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class AuditEntry:
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    action: str = ""
    resource: str = ""
    status: str = "success"
    actor: str = "system"
    details: dict = field(default_factory=dict)
    duration_ms: float = 0.0


class AuditLogger:
    def __init__(self, max_entries: int = 10000, persist_path: str = "./audit_log") -> None:
        self._max_entries = max_entries
        self._persist_path = persist_path
        self._entries: deque[AuditEntry] = deque(maxlen=max_entries)
        self._lock = threading.RLock()
        os.makedirs(persist_path, exist_ok=True)

    def record(
        self,
        action: str,
        resource: str,
        status: str = "success",
        actor: str = "system",
        details: Optional[dict] = None,
        duration_ms: float = 0.0,
    ) -> None:
        with self._lock:
            entry = AuditEntry(
                action=action,
                resource=resource,
                status=status,
                actor=actor,
                details=details or {},
                duration_ms=round(duration_ms, 2),
            )
            self._entries.append(entry)
            if len(self._entries) % 100 == 0:
                self._persist()

    def get_recent(self, n: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return [asdict(e) for e in list(self._entries)[-n:]]

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            status_counts: dict[str, int] = {}
            action_counts: dict[str, int] = {}
            for e in self._entries:
                status_counts[e.status] = status_counts.get(e.status, 0) + 1
                action_counts[e.action] = action_counts.get(e.action, 0) + 1
            return {
                "total_entries": len(self._entries),
                "status_counts": status_counts,
                "action_counts": action_counts,
                "most_common_action": max(action_counts, key=action_counts.get) if action_counts else None,
            }

    def _persist(self) -> None:
        try:
            path = os.path.join(self._persist_path, "audit_log.json")
            with open(path, "w") as f:
                json.dump([asdict(e) for e in self._entries], f, indent=2, default=str)
        except Exception:
            logger.exception("Failed to persist audit log")

    def filter(self, action: Optional[str] = None, status: Optional[str] = None, n: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            filtered = list(self._entries)
            if action:
                filtered = [e for e in filtered if e.action == action]
            if status:
                filtered = [e for e in filtered if e.status == status]
            return [asdict(e) for e in filtered[-n:]]
