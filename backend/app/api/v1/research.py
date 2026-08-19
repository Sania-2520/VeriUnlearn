from __future__ import annotations

from fastapi import APIRouter, Query, Response

from app.api.deps import CurrentUser, DbSession
from app.core.exceptions import NotFoundError
from app.db.models import AttackResult, PrivacyScore
from app.repositories.model_repo import ModelRepository
from app.repositories.research_repo import (
    AttackResultRepository,
    BenchmarkRepository,
    ExperimentRepository,
    PerformanceMetricRepository,
    PrivacyScoreRepository,
)
from app.schemas.research import (
    BenchmarkRunRequest,
    ExperimentCompareRequest,
    ExperimentCreateRequest,
    ExperimentVersionRequest,
    ExtractionRequest,
    InversionRequest,
    MIARequest,
    PoisoningRequest,
)
from app.services.attacks import AttackService
from app.services.audit import AuditService
from app.services.benchmark_engine import BenchmarkEngine
from app.services.experiments import ExperimentService
from app.services.profiler import PerformanceProfiler
from app.services.reporting import ResearchReportGenerator
from app.services.research_metrics import ResearchMetricsCalculator

router = APIRouter(tags=["research"])


# ================================================================== benchmark


@router.post("/benchmark/run")
async def run_benchmark(payload: BenchmarkRunRequest, db: DbSession, user: CurrentUser) -> dict:
    """Run the full 6-method benchmark (non-destructive, reproducible)."""
    model = await ModelRepository(db).get_active_for_dataset(payload.dataset_id)
    if model is None:
        raise NotFoundError("Train a model on this dataset first")

    experiment_id = payload.experiment_id
    if experiment_id:
        await ExperimentService(db).mark_running(experiment_id)

    engine = BenchmarkEngine(db, experiment_id=experiment_id)
    rows = await engine.run(
        dataset_id=payload.dataset_id,
        model=model,
        n_delete=payload.n_delete,
        eval_size=payload.eval_size,
        seed=payload.seed,
    )
    if experiment_id:
        await ExperimentService(db).complete(
            experiment_id,
            {"benchmark": {r["method"]: {"accuracy": r.get("accuracy"), "deletion_seconds": r.get("deletion_seconds")} for r in rows}},
        )
    await AuditService(db).log(
        event_type="benchmark.completed",
        actor=user["sub"],
        subject=payload.dataset_id,
        payload={"methods": len(rows), "deleted": payload.n_delete, "experiment_id": experiment_id},
    )
    return {
        "experiment_id": experiment_id,
        "dataset_id": payload.dataset_id,
        "model_id": model.id,
        "deleted_records": payload.n_delete,
        "seed": payload.seed,
        "results": rows,
    }


@router.get("/benchmark/results")
async def benchmark_results(
    db: DbSession,
    user: CurrentUser,
    method: str | None = None,
    limit: int = Query(default=200, ge=1, le=1000),
) -> dict:
    """Persisted benchmark rows (optionally filtered by method)."""
    rows = await BenchmarkRepository(db).list(limit=limit)
    if method:
        rows = [r for r in rows if r.method == method]
    return {
        "results": [
            {
                "id": r.id,
                "experiment_id": r.experiment_id,
                "dataset_id": r.dataset_id,
                "model_id": r.model_id,
                "method": r.method,
                "deleted_records": r.deleted_records,
                "eval_records": r.eval_records,
                "metrics": r.metrics,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@router.get("/benchmark/history")
async def benchmark_history(db: DbSession, user: CurrentUser, limit: int = Query(default=20, ge=1, le=100)) -> dict:
    """Distinct benchmark runs (grouped by dataset + seed + timestamp)."""
    rows = await BenchmarkRepository(db).list(limit=limit)
    runs: dict[tuple, dict] = {}
    for r in rows:
        key = (r.dataset_id, r.experiment_id, r.created_at)
        runs.setdefault(key, {"dataset_id": r.dataset_id, "experiment_id": r.experiment_id, "created_at": r.created_at.isoformat() if r.created_at else None, "methods": []})
        runs[key]["methods"].append(r.method)
    return {"runs": list(runs.values())[:limit]}


# ===================================================================== attacks


@router.post("/attack/mia")
async def attack_mia(payload: MIARequest, db: DbSession, user: CurrentUser) -> dict:
    """Full three-stage membership-inference report."""
    result = await AttackService(db).mia_full_report(
        payload.model_id, deleted_record_ids=payload.deleted_record_ids, sample_size=payload.sample_size
    )
    if payload.experiment_id:
        db.add(
            AttackResult(
                experiment_id=payload.experiment_id,
                model_id=payload.model_id,
                attack_type="mia",
                stage="report",
                metrics=result,
            )
        )
        await db.flush()
    return result


@router.post("/attack/inversion")
async def attack_inversion(payload: InversionRequest, db: DbSession, user: CurrentUser) -> dict:
    result = await AttackService(db).model_inversion(
        payload.model_id,
        target_label=payload.target_label,
        steps=payload.steps,
        lr=payload.lr,
        deleted_record_ids=payload.deleted_record_ids,
    )
    if payload.experiment_id:
        db.add(
            AttackResult(
                experiment_id=payload.experiment_id,
                model_id=payload.model_id,
                attack_type="inversion",
                stage="report",
                metrics=result,
            )
        )
        await db.flush()
    return result


@router.post("/attack/extraction")
async def attack_extraction(payload: ExtractionRequest, db: DbSession, user: CurrentUser) -> dict:
    result = await AttackService(db).data_extraction(payload.model_id, payload.deleted_record_ids)
    if payload.experiment_id:
        db.add(
            AttackResult(
                experiment_id=payload.experiment_id,
                model_id=payload.model_id,
                attack_type="extraction",
                stage="post_unlearning",
                metrics=result,
            )
        )
        await db.flush()
    return result


@router.post("/attack/poisoning")
async def attack_poisoning(payload: PoisoningRequest, db: DbSession, user: CurrentUser) -> dict:
    result = await AttackService(db).poisoning_suite(
        payload.model_id,
        poison_fraction=payload.poison_fraction,
        trigger_value=payload.trigger_value,
        attack_type=payload.attack_type,
    )
    if payload.experiment_id:
        db.add(
            AttackResult(
                experiment_id=payload.experiment_id,
                model_id=payload.model_id,
                attack_type="poisoning",
                stage="report",
                metrics=result,
            )
        )
        await db.flush()
    return result


@router.get("/attack/results")
async def attack_results(db: DbSession, user: CurrentUser, model_id: str | None = None, limit: int = Query(default=100, ge=1, le=500)) -> dict:
    rows = await AttackResultRepository(db).list(limit=limit)
    if model_id:
        rows = [r for r in rows if r.model_id == model_id]
    return {
        "results": [
            {
                "id": r.id,
                "experiment_id": r.experiment_id,
                "model_id": r.model_id,
                "attack_type": r.attack_type,
                "stage": r.stage,
                "metrics": r.metrics,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


# ===================================================================== metrics


@router.get("/metrics/system")
async def system_metrics(db: DbSession, user: CurrentUser) -> dict:
    """Live + persisted system resource metrics (CPU/RAM/disk)."""
    profiler = PerformanceProfiler(db)
    live = profiler.sampler.sample()
    await profiler.snapshot(kind="system")
    rows = await PerformanceMetricRepository(db).by_kind("system", limit=100)
    series: dict[str, list[dict]] = {}
    for r in rows:
        series.setdefault(r.metric, []).append(
            {"value": r.value, "unit": r.unit, "sampled_at": r.sampled_at.isoformat() if r.sampled_at else None}
        )
    return {"live": live, "series": series}


@router.get("/metrics/privacy")
async def privacy_metrics(db: DbSession, user: CurrentUser, method: str | None = None) -> dict:
    """Research metrics: forget quality, privacy gain, retention, etc."""
    calculator = ResearchMetricsCalculator(db)
    matrix = await calculator.comparison_matrix([method] if method else None)
    # Persist a PrivacyScore per available method for the audit trail.
    for row in matrix["rows"]:
        existing = await PrivacyScoreRepository(db).by_method(row["method"])
        if not existing:
            db.add(
                PrivacyScore(
                    experiment_id=None,
                    method=row["method"],
                    scores={k: row[k] for k in matrix["metrics"] if k in row},
                )
            )
    await db.flush()
    return {
        "matrix": matrix,
        "compliance_readiness": matrix["compliance"],
        "latex_table": calculator.to_latex_table(matrix),
    }


@router.get("/metrics/security")
async def security_metrics(db: DbSession, user: CurrentUser) -> dict:
    """Aggregate attack outcomes: MIA leakage, poisoning persistence, extraction."""
    attacks = await AttackResultRepository(db).list(limit=200)
    mia_aucs = [a.metrics.get("auc") for a in attacks if a.attack_type == "mia" and a.metrics.get("auc") is not None]
    poison_persist = [
        a.metrics.get("persistence_ratio")
        for a in attacks
        if a.attack_type == "poisoning" and a.metrics.get("persistence_ratio") is not None
    ]
    extraction_rates = [
        a.metrics.get("extraction_success_rate")
        for a in attacks
        if a.attack_type == "extraction" and a.metrics.get("extraction_success_rate") is not None
    ]
    return {
        "attack_count": len(attacks),
        "summary": {
            "mia_mean_auc": round(sum(mia_aucs) / len(mia_aucs), 4) if mia_aucs else None,
            "mia_max_leakage": round(max(mia_aucs) - 0.5, 4) if mia_aucs else None,
            "poisoning_mean_persistence": round(sum(poison_persist) / len(poison_persist), 4) if poison_persist else None,
            "extraction_mean_rate": round(sum(extraction_rates) / len(extraction_rates), 4) if extraction_rates else None,
        },
        "by_type": {
            t: sum(1 for a in attacks if a.attack_type == t) for t in ("mia", "inversion", "extraction", "poisoning")
        },
    }


# ================================================================= experiments


@router.post("/experiments")
async def create_experiment(payload: ExperimentCreateRequest, db: DbSession, user: CurrentUser) -> dict:
    experiment = await ExperimentService(db).create(
        name=payload.name,
        description=payload.description,
        seed=payload.seed,
        parameters=payload.parameters,
        dataset_id=payload.dataset_id,
        model_id=payload.model_id,
        created_by=user["sub"],
    )
    return {
        "id": experiment.id,
        "name": experiment.name,
        "version": experiment.version,
        "seed": experiment.seed,
        "parameters": experiment.parameters,
        "environment": experiment.environment,
        "dataset_id": experiment.dataset_id,
        "model_id": experiment.model_id,
        "status": experiment.status,
        "created_at": experiment.created_at.isoformat() if experiment.created_at else None,
    }


@router.get("/experiments")
async def list_experiments(db: DbSession, user: CurrentUser, limit: int = Query(default=100, ge=1, le=500)) -> dict:
    experiments = await ExperimentRepository(db).list(limit=limit)
    return {
        "experiments": [
            {
                "id": e.id,
                "name": e.name,
                "description": e.description,
                "version": e.version,
                "seed": e.seed,
                "status": e.status,
                "result_summary": e.result_summary,
                "parameters": e.parameters,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "updated_at": e.updated_at.isoformat() if e.updated_at else None,
            }
            for e in experiments
        ]
    }


@router.get("/experiments/{experiment_id}")
async def get_experiment(experiment_id: str, db: DbSession, user: CurrentUser) -> dict:
    experiment = await ExperimentService(db).get(experiment_id)
    history = await ExperimentService(db).history(experiment_id)
    benchmarks = await BenchmarkRepository(db).by_experiment(experiment_id)
    return {
        "id": experiment.id,
        "name": experiment.name,
        "description": experiment.description,
        "version": experiment.version,
        "seed": experiment.seed,
        "parameters": experiment.parameters,
        "environment": experiment.environment,
        "dataset_id": experiment.dataset_id,
        "model_id": experiment.model_id,
        "status": experiment.status,
        "result_summary": experiment.result_summary,
        "created_at": experiment.created_at.isoformat() if experiment.created_at else None,
        "updated_at": experiment.updated_at.isoformat() if experiment.updated_at else None,
        "history": history,
        "benchmarks": [
            {"method": r.method, "metrics": r.metrics, "deleted_records": r.deleted_records, "created_at": r.created_at.isoformat() if r.created_at else None}
            for r in benchmarks
        ],
    }


@router.post("/experiments/{experiment_id}/version")
async def version_experiment(
    experiment_id: str, payload: ExperimentVersionRequest, db: DbSession, user: CurrentUser
) -> dict:
    experiment = await ExperimentService(db).version(
        experiment_id, parameters=payload.parameters, name=payload.name
    )
    return {"id": experiment.id, "version": experiment.version, "status": experiment.status}


@router.post("/experiments/compare")
async def compare_experiments(payload: ExperimentCompareRequest, db: DbSession, user: CurrentUser) -> dict:
    return await ExperimentService(db).compare(payload.experiment_ids)


# ================================================================== exports


@router.get("/benchmark/export")
async def export_benchmarks(
    db: DbSession,
    user: CurrentUser,
    format: str = Query(default="csv", pattern="^(csv|json|xlsx)$"),
) -> Response:
    """Download benchmark results as CSV / JSON / Excel."""
    rows = await BenchmarkRepository(db).list(limit=1000)
    df = ResearchReportGenerator.benchmark_dataframe(rows)
    if format == "json":
        body = ResearchReportGenerator.to_json(df)
        media = "application/json"
        filename = "benchmark-results.json"
    elif format == "xlsx":
        body = ResearchReportGenerator.to_excel(df)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "benchmark-results.xlsx"
    else:
        body = ResearchReportGenerator.to_csv(df)
        media = "text/csv"
        filename = "benchmark-results.csv"
    return Response(
        content=body,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
