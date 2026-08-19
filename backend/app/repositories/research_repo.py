from __future__ import annotations

from sqlalchemy import select

from app.db.models import (
    AttackResult,
    BenchmarkResult,
    Experiment,
    ExperimentHistory,
    PerformanceMetric,
    PrivacyScore,
)
from app.repositories.base import BaseRepository


class ExperimentRepository(BaseRepository[Experiment]):
    model = Experiment

    async def create(self, experiment: Experiment) -> Experiment:
        return await self.add(experiment)

    async def history(self, experiment_id: str) -> list[ExperimentHistory]:
        result = await self.session.execute(
            select(ExperimentHistory)
            .where(ExperimentHistory.experiment_id == experiment_id)
            .order_by(ExperimentHistory.version.asc())
        )
        return list(result.scalars().all())


class BenchmarkRepository(BaseRepository[BenchmarkResult]):
    model = BenchmarkResult

    async def create(self, row: BenchmarkResult) -> BenchmarkResult:
        return await self.add(row)

    async def by_method(self, method: str, limit: int = 50) -> list[BenchmarkResult]:
        result = await self.session.execute(
            select(BenchmarkResult)
            .where(BenchmarkResult.method == method)
            .order_by(BenchmarkResult.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def by_experiment(self, experiment_id: str) -> list[BenchmarkResult]:
        result = await self.session.execute(
            select(BenchmarkResult)
            .where(BenchmarkResult.experiment_id == experiment_id)
            .order_by(BenchmarkResult.method.asc())
        )
        return list(result.scalars().all())


class AttackResultRepository(BaseRepository[AttackResult]):
    model = AttackResult

    async def create(self, row: AttackResult) -> AttackResult:
        return await self.add(row)

    async def by_model(self, model_id: str, limit: int = 100) -> list[AttackResult]:
        result = await self.session.execute(
            select(AttackResult)
            .where(AttackResult.model_id == model_id)
            .order_by(AttackResult.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class PerformanceMetricRepository(BaseRepository[PerformanceMetric]):
    model = PerformanceMetric

    async def by_kind(self, kind: str, limit: int = 200) -> list[PerformanceMetric]:
        result = await self.session.execute(
            select(PerformanceMetric)
            .where(PerformanceMetric.kind == kind)
            .order_by(PerformanceMetric.sampled_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class PrivacyScoreRepository(BaseRepository[PrivacyScore]):
    model = PrivacyScore

    async def create(self, row: PrivacyScore) -> PrivacyScore:
        return await self.add(row)

    async def by_method(self, method: str) -> list[PrivacyScore]:
        result = await self.session.execute(
            select(PrivacyScore)
            .where(PrivacyScore.method == method)
            .order_by(PrivacyScore.created_at.desc())
        )
        return list(result.scalars().all())
