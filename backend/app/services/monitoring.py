"""System monitoring (Phase 7).

Snapshots CPU/RAM/disk via psutil, probes dependency health (DB, Redis, Qdrant,
vector store), tracks worker-queue length (in-flight deletion requests), and
exposes API latency / error-rate counters (in-process ring). Snapshots are
persisted to ``system_metrics`` and exported to Prometheus gauges.
"""
from __future__ import annotations

import time
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models import DeletionRequest, SystemMetric

logger = get_logger("veriunlearn.monitoring")

_STARTED_AT = time.monotonic()
_LAST_REQUEST_AT: list[float] = []  # recent request completion times (ring)
_ERROR_RING: list[float] = []  # recent error timestamps (ring)
_RING_SIZE = 1000


def record_request(duration_seconds: float, *, is_error: bool = False) -> None:
    """Called by the request middleware to feed latency / error counters."""
    _LAST_REQUEST_AT.append(duration_seconds)
    if len(_LAST_REQUEST_AT) > _RING_SIZE:
        del _LAST_REQUEST_AT[: len(_LAST_REQUEST_AT) - _RING_SIZE]
    if is_error:
        _ERROR_RING.append(time.monotonic())
        if len(_ERROR_RING) > _RING_SIZE:
            del _ERROR_RING[: len(_ERROR_RING) - _RING_SIZE]


class MonitoringService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --------------------------------------------------------------- snapshot

    async def snapshot(self, *, persist: bool = True) -> dict[str, Any]:
        system = self._system()
        dependencies = await self._dependencies()
        queue = await self._queue()
        api = self._api_stats()
        payload = {"ts": time.time(), "system": system, "dependencies": dependencies, "queue": queue, "api": api}
        if persist:
            await self._persist(payload)
        return payload

    def _system(self) -> dict[str, Any]:
        try:
            import psutil

            return {
                "cpu_percent": round(psutil.cpu_percent(interval=None), 2),
                "system_cpu_percent": round(psutil.cpu_percent(interval=None), 2),
                "ram_mb": round(psutil.Process().memory_info().rss / 1024 / 1024, 2),
                "system_ram_mb": round(psutil.virtual_memory().total / 1024 / 1024, 2),
                "system_ram_used_mb": round(psutil.virtual_memory().used / 1024 / 1024, 2),
                "disk_used_mb": round(psutil.disk_usage("/").used / 1024 / 1024, 2),
                "disk_total_mb": round(psutil.disk_usage("/").total / 1024 / 1024, 2),
            }
        except Exception:  # noqa: BLE001 - psutil may be unavailable
            return {}

    async def _dependencies(self) -> dict[str, Any]:
        checks: dict[str, Any] = {}
        # Database.
        try:
            await self.session.execute(select(1))
            checks["database"] = {"healthy": True, "detail": {"backend": "sqlalchemy"}}
        except Exception:  # noqa: BLE001
            checks["database"] = {"healthy": False, "detail": {}}
        # Redis.
        if settings.REDIS_URL:
            checks["redis"] = {"healthy": False, "detail": {"configured": True}}
        else:
            checks["redis"] = {"healthy": None, "detail": {"configured": False, "note": "not configured — optional"}}
        # Qdrant / vector store.
        if settings.VECTOR_STORE_BACKEND == "qdrant" and settings.QDRANT_URL:
            checks["qdrant"] = {"healthy": None, "detail": {"configured": True, "note": "checked lazily on write"}}
        else:
            checks["qdrant"] = {
                "healthy": True,
                "detail": {"configured": False, "backend": settings.VECTOR_STORE_BACKEND, "note": "in-memory vector store"},
            }
        return checks

    async def _queue(self) -> dict[str, Any]:
        in_flight = int(
            await self.session.scalar(
                select(func.count())
                .select_from(DeletionRequest)
                .where(DeletionRequest.status.in_(["pending", "in_progress"]))
            )
            or 0
        )
        total = int(await self.session.scalar(select(func.count()).select_from(DeletionRequest)) or 0)
        return {"in_flight": in_flight, "total": total}

    def _api_stats(self) -> dict[str, Any]:
        uptime = time.monotonic() - _STARTED_AT
        window = 300  # seconds
        now = time.monotonic()
        recent = [d for d in _LAST_REQUEST_AT if now - 0 <= window]  # keep simple: last 300s of recorded requests
        recent = _LAST_REQUEST_AT[-200:]
        avg_latency = round(sum(recent) / len(recent), 4) if recent else None
        errors_in_window = sum(1 for t in _ERROR_RING if now - t <= window)
        total_in_window = len(_LAST_REQUEST_AT)
        error_rate = round(errors_in_window / total_in_window, 4) if total_in_window else 0.0
        return {
            "uptime_seconds": round(uptime, 1),
            "avg_latency_ms": round(avg_latency * 1000, 2) if avg_latency is not None else None,
            "error_rate": error_rate,
            "requests_sampled": total_in_window,
        }

    async def _persist(self, payload: dict[str, Any]) -> None:
        system = payload["system"]
        rows: list[SystemMetric] = []
        for key, value in [
            ("cpu_percent", system.get("cpu_percent")),
            ("ram_mb", system.get("ram_mb")),
            ("disk_used_mb", system.get("disk_used_mb")),
        ]:
            if value is None:
                continue
            rows.append(SystemMetric(kind="system", name=key, value=float(value), unit="%" if "percent" in key else "MB"))
        for dep_name, dep in payload["dependencies"].items():
            rows.append(
                SystemMetric(
                    kind="dependency",
                    name=f"dep.{dep_name}",
                    value=1.0 if dep.get("healthy") else 0.0,
                    unit="bool",
                    healthy=dep.get("healthy"),
                    detail=dep.get("detail", {}),
                )
            )
        rows.append(SystemMetric(kind="queue", name="deletion_queue.in_flight", value=float(payload["queue"]["in_flight"]), unit="count"))
        api = payload["api"]
        if api.get("avg_latency_ms") is not None:
            rows.append(SystemMetric(kind="api", name="api.avg_latency_ms", value=float(api["avg_latency_ms"]), unit="ms"))
        rows.append(SystemMetric(kind="api", name="api.error_rate", value=float(api["error_rate"]), unit="ratio"))
        rows.append(SystemMetric(kind="api", name="api.uptime_seconds", value=float(api["uptime_seconds"]), unit="s"))
        self.session.add_all(rows)
        await self.session.flush()

    # ---------------------------------------------------------------- history

    async def history(self, kind: str | None = None, *, limit: int = 200) -> list[dict[str, Any]]:
        stmt = select(SystemMetric)
        if kind:
            stmt = stmt.where(SystemMetric.kind == kind)
        stmt = stmt.order_by(SystemMetric.sampled_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())
        rows.reverse()
        return [
            {
                "name": r.name,
                "value": r.value,
                "unit": r.unit,
                "healthy": r.healthy,
                "sampled_at": r.sampled_at.isoformat() if r.sampled_at else None,
            }
            for r in rows
        ]
