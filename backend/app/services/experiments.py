"""Experiment Manager (Phase 6).

Creates versioned, reproducible experiments: captures parameters, seed,
environment (platform, Python, key dependency versions), dataset/model
versions, and an append-only version history. Every benchmark / attack run can
be attached to an experiment id so results are grouped and comparable.
"""
from __future__ import annotations

import platform
import sys
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationFailedError
from app.db.models import Experiment, ExperimentHistory
from app.repositories.research_repo import ExperimentRepository


class ExperimentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ExperimentRepository(session)

    # ------------------------------------------------------------ environment

    @staticmethod
    def capture_environment() -> dict[str, Any]:
        """Reproducibility metadata: platform + runtime + key dependency versions."""
        deps: dict[str, str] = {}
        for mod in ("numpy", "sklearn", "pandas", "torch", "transformers", "peft"):
            try:
                module = __import__(mod)
                deps[mod] = getattr(module, "__version__", "unknown")
            except ImportError:
                deps[mod] = "not-installed"
        return {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "dependencies": deps,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------ CRUD

    async def create(
        self,
        *,
        name: str,
        description: str | None = None,
        seed: int = 42,
        parameters: dict[str, Any] | None = None,
        dataset_id: str | None = None,
        model_id: str | None = None,
        created_by: str = "system",
    ) -> Experiment:
        if not name or not name.strip():
            raise ValidationFailedError("Experiment name is required")
        experiment = Experiment(
            name=name.strip(),
            description=description,
            version=1,
            seed=seed,
            parameters=parameters or {},
            environment=self.capture_environment(),
            dataset_id=dataset_id,
            model_id=model_id,
            status="draft",
            created_by=created_by,
            history=[],
        )
        experiment = await self.repo.create(experiment)
        self.session.add(
            ExperimentHistory(
                experiment_id=experiment.id,
                version=1,
                snapshot={
                    "name": experiment.name,
                    "seed": seed,
                    "parameters": parameters or {},
                    "dataset_id": dataset_id,
                    "model_id": model_id,
                    "environment": experiment.environment,
                },
            )
        )
        await self.session.flush()
        return experiment

    async def version(
        self,
        experiment_id: str,
        *,
        parameters: dict[str, Any] | None = None,
        name: str | None = None,
    ) -> Experiment:
        """Bump to a new version, snapshotting the previous config in history."""
        experiment = await self.repo.get(experiment_id)
        prev_snapshot = {
            "name": experiment.name,
            "seed": experiment.seed,
            "parameters": experiment.parameters,
            "dataset_id": experiment.dataset_id,
            "model_id": experiment.model_id,
            "environment": experiment.environment,
            "status": experiment.status,
            "result_summary": experiment.result_summary,
        }
        experiment.version += 1
        if name:
            experiment.name = name
        if parameters is not None:
            experiment.parameters = parameters
        experiment.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC
        experiment.history = list(experiment.history or []) + [prev_snapshot]
        self.session.add(
            ExperimentHistory(
                experiment_id=experiment.id,
                version=experiment.version,
                snapshot={**prev_snapshot, "bumped_to": experiment.version},
            )
        )
        await self.session.flush()
        return experiment

    async def mark_running(self, experiment_id: str) -> Experiment:
        experiment = await self.repo.get(experiment_id)
        experiment.status = "running"
        await self.session.flush()
        return experiment

    async def complete(self, experiment_id: str, summary: dict[str, Any]) -> Experiment:
        experiment = await self.repo.get(experiment_id)
        experiment.status = "completed"
        experiment.result_summary = summary
        await self.session.flush()
        return experiment

    async def list(self, limit: int = 100) -> list[Experiment]:
        return await self.repo.list(limit=limit)

    async def get(self, experiment_id: str) -> Experiment:
        return await self.repo.get(experiment_id)

    async def compare(self, experiment_ids: list[str]) -> dict[str, Any]:
        """Side-by-side comparison of experiments (summary fields)."""
        if len(experiment_ids) < 2:
            raise ValidationFailedError("Provide at least two experiment ids to compare")
        experiments = [await self.repo.get(eid) for eid in experiment_ids]
        return {
            "count": len(experiments),
            "experiments": [
                {
                    "id": e.id,
                    "name": e.name,
                    "version": e.version,
                    "seed": e.seed,
                    "parameters": e.parameters,
                    "status": e.status,
                    "result_summary": e.result_summary,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in experiments
            ],
        }

    async def history(self, experiment_id: str) -> list[dict[str, Any]]:
        rows = await self.repo.history(experiment_id)
        return [
            {
                "id": r.id,
                "version": r.version,
                "snapshot": r.snapshot,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
