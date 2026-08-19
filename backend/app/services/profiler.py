"""Performance Profiler (Phase 6).

Samples system resources (CPU, RAM, disk) and measures operation timings
(training, retraining, embedding update, DB update, hash / certificate
generation, API latency). Samples are persisted as :class:`PerformanceMetric`
rows so the research suite can correlate resource usage with unlearning method.

psutil is optional: if unavailable (or import fails) the profiler degrades to
timing-only mode instead of crashing the experiment.
"""
from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PerformanceMetric

logger = logging.getLogger("veriunlearn.profiler")

try:  # pragma: no cover - psutil presence is environment-dependent
    import psutil
except ImportError:  # pragma: no cover
    psutil = None  # type: ignore[assignment]


class SystemSampler:
    """Best-effort snapshot of process + system resources."""

    @staticmethod
    def sample() -> dict[str, Any]:
        out: dict[str, Any] = {"ts": time.time()}
        try:
            proc = psutil.Process()  # type: ignore[union-attr]
            out["cpu_percent"] = round(proc.cpu_percent(interval=0.05), 2)
            out["ram_mb"] = round(proc.memory_info().rss / (1024 * 1024), 2)
        except Exception:  # noqa: BLE001 - never fail an experiment on sampling
            out["cpu_percent"] = None
            out["ram_mb"] = None
        try:
            out["system_cpu_percent"] = round(psutil.cpu_percent(interval=0.05), 2)  # type: ignore[union-attr]
            out["system_ram_mb"] = round(psutil.virtual_memory().used / (1024 * 1024), 2)  # type: ignore[union-attr]
            out["disk_used_mb"] = round(psutil.disk_usage(".").used / (1024 * 1024), 2)  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            out["system_cpu_percent"] = None
            out["system_ram_mb"] = None
            out["disk_used_mb"] = None
        return out


class PerformanceProfiler:
    def __init__(self, session: AsyncSession, experiment_id: str | None = None) -> None:
        self.session = session
        self.experiment_id = experiment_id
        self.sampler = SystemSampler()

    # ------------------------------------------------------------- sampling

    async def snapshot(self, *, kind: str = "system") -> dict[str, Any]:
        """Sample + persist one system snapshot."""
        sample = self.sampler.sample()
        for key, value in sample.items():
            if key == "ts" or value is None:
                continue
            self.session.add(
                PerformanceMetric(
                    experiment_id=self.experiment_id,
                    kind=kind,
                    metric=key,
                    value=float(value),
                    unit="%" if "percent" in key else "MB",
                    context={},
                )
            )
        await self.session.flush()
        return sample

    async def record(
        self,
        *,
        metric: str,
        value: float,
        unit: str = "",
        kind: str = "benchmark",
        context: dict[str, Any] | None = None,
    ) -> PerformanceMetric:
        row = PerformanceMetric(
            experiment_id=self.experiment_id,
            kind=kind,
            metric=metric,
            value=round(float(value), 6),
            unit=unit,
            context=context or {},
        )
        self.session.add(row)
        await self.session.flush()
        return row

    # -------------------------------------------------------------- timers

    @contextmanager
    def timed(self, metric: str, *, unit: str = "s", kind: str = "benchmark", context: dict[str, Any] | None = None):
        """Synchronous timing context; records elapsed seconds on exit."""
        start = time.monotonic()
        try:
            yield
        finally:
            elapsed = time.monotonic() - start
            self.session.add(
                PerformanceMetric(
                    experiment_id=self.experiment_id,
                    kind=kind,
                    metric=metric,
                    value=round(elapsed, 6),
                    unit=unit,
                    context=context or {},
                )
            )

    async def atimed(self, metric: str, *, unit: str = "s", kind: str = "benchmark", context: dict[str, Any] | None = None):
        """Async timing context; persists elapsed seconds on exit."""

        @contextmanager
        def _sync():
            start = time.monotonic()
            try:
                yield
            finally:
                elapsed = time.monotonic() - start
                self.session.add(
                    PerformanceMetric(
                        experiment_id=self.experiment_id,
                        kind=kind,
                        metric=metric,
                        value=round(elapsed, 6),
                        unit=unit,
                        context=context or {},
                    )
                )

        return _sync()

    # --------------------------------------------------------------- queries

    async def latest(self, metric: str, limit: int = 1) -> list[PerformanceMetric]:
        from sqlalchemy import select

        result = await self.session.execute(
            select(PerformanceMetric)
            .where(PerformanceMetric.metric == metric)
            .order_by(PerformanceMetric.sampled_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
