"""Phase 6 — Security Evaluation, Benchmarking & Research Suite tests."""
from __future__ import annotations

import numpy as np
import pytest

from app.db.models import DeletionRequest, MLModel
from app.repositories.deletion_repo import DeletionRepository
from app.repositories.model_repo import ModelRepository
from app.repositories.research_repo import BenchmarkRepository
from app.services.attacks import AttackService
from app.services.benchmark_engine import BenchmarkEngine
from app.services.experiments import ExperimentService
from app.services.ingestion import IngestionService
from app.services.profiler import PerformanceProfiler
from app.services.research_metrics import ResearchMetricsCalculator
from app.services.sisa import SISAEngine
from app.services.unlearning import UnlearningService


def make_csv(n: int = 300) -> bytes:
    rng = np.random.default_rng(11)
    rows = []
    for i in range(n):
        cls = i % 2
        rows.append(f"{rng.normal(cls * 2.0, 0.8):.4f},{rng.normal(cls * -2.0, 0.8):.4f},{'high' if cls else 'low'}")
    return ("a,b,income\n" + "\n".join(rows)).encode()


async def build_model(session_factory) -> tuple[str, str]:
    """Dataset + trained model → (dataset_id, model_id)."""
    async with session_factory() as session:
        dataset = await IngestionService(session).ingest_csv_bytes(
            make_csv(), name="p6-data", label_column="income", shard_count=4
        )
        await session.commit()
        ds_id = dataset.id
    async with session_factory() as session:
        model = MLModel(name="p6-model", model_type="linear", dataset_id=ds_id, shard_count=4)
        model = await ModelRepository(session).add(model)
        from app.db.models import Dataset

        await SISAEngine(session).train_model(model, await session.get(Dataset, ds_id))
        await session.commit()
        return ds_id, model.id


# ---------------------------------------------------------------- benchmark


@pytest.mark.asyncio
async def test_benchmark_engine_all_methods(session_factory):
    ds_id, model_id = await build_model(session_factory)
    async with session_factory() as session:

        model = await session.get(MLModel, model_id)
        engine = BenchmarkEngine(session)
        rows = await engine.run(dataset_id=ds_id, model=model, n_delete=30, eval_size=100, seed=7)
        await session.commit()
        methods = {r["method"] for r in rows}
        assert methods == {"original", "full_retrain", "sisa", "influence", "certified", "veriunlearn"}
        orig = next(r for r in rows if r["method"] == "original")
        assert 0.0 <= orig["accuracy"] <= 1.0
        assert "deletion_seconds" in orig
        # Persisted rows exist.
        persisted = await BenchmarkRepository(session).list(limit=50)
        assert len(persisted) == 6
        # Production model untouched (metrics hash unchanged).
        model2 = await session.get(MLModel, model_id)
        assert model2.weights_hash == model.weights_hash


@pytest.mark.asyncio
async def test_benchmark_non_destructive(session_factory):
    ds_id, model_id = await build_model(session_factory)
    async with session_factory() as session:
        model = await session.get(MLModel, model_id)
        before_hash = model.weights_hash
        await BenchmarkEngine(session).run(dataset_id=ds_id, model=model, n_delete=20, eval_size=80, seed=3)
        await session.commit()
        model2 = await session.get(MLModel, model_id)
        assert model2.weights_hash == before_hash
        # Shard weights files unchanged.
        from app.services.sisa import SISAEngine

        shards = await ModelRepository(session).get_shards(model_id)
        loaded = await SISAEngine(session).load_shard_models(model2)
        assert len(loaded) == len(shards)


# ------------------------------------------------------------------- attacks


@pytest.mark.asyncio
async def test_mia_full_report(session_factory):
    ds_id, model_id = await build_model(session_factory)
    async with session_factory() as session:
        report = await AttackService(session).mia_full_report(model_id, sample_size=100)
        assert report["attack"] == "membership_inference"
        assert "original" in report["stages"]
        orig = report["stages"]["original"]
        for k in ("auc", "accuracy", "precision", "recall", "f1", "privacy_leakage", "membership_confidence"):
            assert k in orig


@pytest.mark.asyncio
async def test_mia_after_unlearning(session_factory):
    ds_id, model_id = await build_model(session_factory)
    # Perform a real deletion to have tombstones.
    async with session_factory() as session:
        from sqlalchemy import select

        from app.db.models import DatasetRecord

        chosen = (
            await session.execute(
                select(DatasetRecord).where(DatasetRecord.dataset_id == ds_id).limit(10)
            )
        ).scalars().all()
        request = DeletionRequest(
            identity_key=chosen[0].identity_key,
            subject_label="x",
            deletion_type="records",
            method="retrain",
            scope={"scope": "records"},
            record_ids=[r.id for r in chosen],
            requested_by="tester",
        )
        request = await DeletionRepository(session).create(request)
        await UnlearningService(session).execute(request.id)
        await session.commit()
        deleted_ids = [r.id for r in chosen]

    async with session_factory() as session:
        out = await AttackService(session).membership_after_unlearning(model_id, deleted_ids)
        assert "auc" in out
        assert out["deleted_probed"] >= 1


@pytest.mark.asyncio
async def test_data_extraction(session_factory):
    ds_id, model_id = await build_model(session_factory)
    async with session_factory() as session:
        from sqlalchemy import select

        from app.db.models import DatasetRecord

        chosen = (
            await session.execute(
                select(DatasetRecord).where(DatasetRecord.dataset_id == ds_id).limit(5)
            )
        ).scalars().all()
        request = DeletionRequest(
            identity_key=chosen[0].identity_key,
            subject_label="x",
            deletion_type="records",
            method="retrain",
            scope={"scope": "records"},
            record_ids=[r.id for r in chosen],
            requested_by="tester",
        )
        request = await DeletionRepository(session).create(request)
        await UnlearningService(session).execute(request.id)
        await session.commit()
        deleted_ids = [r.id for r in chosen]

    async with session_factory() as session:
        result = await AttackService(session).data_extraction(model_id, deleted_ids)
        assert result["attack"] == "data_extraction"
        assert result["deleted_checked"] == 5
        assert "extraction_success_rate" in result
        assert result["channels"]["text"] == 0  # tombstones carry no text


@pytest.mark.asyncio
async def test_poisoning_suite(session_factory):
    ds_id, model_id = await build_model(session_factory)
    async with session_factory() as session:
        for attack_type in ("backdoor", "label_flip", "gradient"):
            result = await AttackService(session).poisoning_suite(
                model_id, poison_fraction=0.2, attack_type=attack_type
            )
            assert result["attack"] == "poisoning"
            assert result["attack_type"] == attack_type
            assert "detection_rate" in result
            assert "removal_success" in result
            assert "persistence_ratio" in result


@pytest.mark.asyncio
async def test_inversion_with_after(session_factory):
    ds_id, model_id = await build_model(session_factory)
    async with session_factory() as session:
        result = await AttackService(session).model_inversion(model_id, steps=50)
        assert "reconstruction_error" in result
        assert "similarity_score" in result
        assert "information_leakage" in result


# ------------------------------------------------------------- metrics + exp


@pytest.mark.asyncio
async def test_research_metrics_calculator(session_factory):
    async with session_factory() as session:
        calc = ResearchMetricsCalculator(session)
        assert calc.forget_quality(0.6) == pytest.approx(0.4)
        assert calc.privacy_gain(0.75, 0.55) == pytest.approx(0.2)
        assert calc.knowledge_retention(0.8, 1.0) == pytest.approx(0.8)
        assert calc.utility_loss(1.0, 0.9) == pytest.approx(0.1)
        assert calc.deletion_efficiency(100, 5.0) == pytest.approx(20.0)
        matrix = await calc.comparison_matrix(["original"])
        assert matrix["metrics"] and isinstance(matrix["rows"], list)


@pytest.mark.asyncio
async def test_experiment_lifecycle(session_factory):
    async with session_factory() as session:
        svc = ExperimentService(session)
        exp = await svc.create(name="bench-1", seed=42, parameters={"n_delete": 50})
        assert exp.version == 1
        assert "python" in exp.environment
        exp2 = await svc.version(exp.id, parameters={"n_delete": 100})
        assert exp2.version == 2
        hist = await svc.history(exp.id)
        assert len(hist) >= 2
        comparison = await svc.compare([exp.id, exp2.id])
        assert comparison["count"] == 2


@pytest.mark.asyncio
async def test_profiler_records(session_factory):
    async with session_factory() as session:
        profiler = PerformanceProfiler(session)
        with profiler.timed("hash_generation", unit="ms"):
            import time

            time.sleep(0.01)
        await profiler.snapshot(kind="system")
        await session.commit()
        rows = await profiler.latest("hash_generation")
        assert rows and rows[0].value > 0


# ---------------------------------------------------------------------- API


@pytest.mark.asyncio
async def test_research_api(session_factory, client, auth_headers):
    ds_id, model_id = await build_model(session_factory)

    # create experiment
    r = await client.post(
        "/api/v1/experiments",
        json={"name": "exp-1", "seed": 7, "parameters": {"n_delete": 20}},
        headers=auth_headers,
    )
    assert r.status_code == 200
    exp_id = r.json()["id"]

    # run benchmark bound to experiment
    r = await client.post(
        "/api/v1/benchmark/run",
        json={"dataset_id": ds_id, "n_delete": 20, "eval_size": 80, "seed": 7, "experiment_id": exp_id},
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["results"]) == 6
    assert body["experiment_id"] == exp_id

    # results + history
    r = await client.get("/api/v1/benchmark/results", headers=auth_headers)
    assert r.status_code == 200 and len(r.json()["results"]) >= 6
    r = await client.get("/api/v1/benchmark/history", headers=auth_headers)
    assert r.status_code == 200

    # experiments detail
    r = await client.get(f"/api/v1/experiments/{exp_id}", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()["benchmarks"]) == 6

    # attacks
    r = await client.post(
        "/api/v1/attack/mia",
        json={"model_id": model_id, "sample_size": 100},
        headers=auth_headers,
    )
    assert r.status_code == 200 and "stages" in r.json()
    r = await client.post(
        "/api/v1/attack/inversion",
        json={"model_id": model_id, "steps": 50},
        headers=auth_headers,
    )
    assert r.status_code == 200 and "reconstruction_error" in r.json()
    r = await client.post(
        "/api/v1/attack/poisoning",
        json={"model_id": model_id, "poison_fraction": 0.2, "attack_type": "backdoor"},
        headers=auth_headers,
    )
    assert r.status_code == 200 and "removal_success" in r.json()

    # metrics
    r = await client.get("/api/v1/metrics/system", headers=auth_headers)
    assert r.status_code == 200 and "live" in r.json()
    r = await client.get("/api/v1/metrics/privacy", headers=auth_headers)
    assert r.status_code == 200 and "matrix" in r.json()
    r = await client.get("/api/v1/metrics/security", headers=auth_headers)
    assert r.status_code == 200

    # export
    r = await client.get("/api/v1/benchmark/export?format=csv", headers=auth_headers)
    assert r.status_code == 200 and b"method" in r.content
    r = await client.get("/api/v1/benchmark/export?format=json", headers=auth_headers)
    assert r.status_code == 200
    r = await client.get("/api/v1/benchmark/export?format=xlsx", headers=auth_headers)
    assert r.status_code == 200 and len(r.content) > 0
