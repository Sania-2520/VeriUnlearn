"""Benchmark and MLflow experiment tracking endpoints."""

import asyncio

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from api import deps

router = APIRouter()


@router.post("/benchmarks/run")
async def run_benchmarks(request: dict):
    from training.benchmarks import BenchmarkConfig

    runner = deps.get_benchmark_runner()
    cfg = BenchmarkConfig(**{k: v for k, v in request.items() if hasattr(BenchmarkConfig, k)})
    runner._config = cfg
    results = await asyncio.to_thread(runner.run_all)
    return {
        "total": len(results),
        "completed": sum(1 for r in results if r.status == "completed"),
        "failed": sum(1 for r in results if r.status == "failed"),
        "results": [
            {
                "dataset": r.dataset,
                "algorithm": r.algorithm,
                "data_size": r.data_size,
                "deletion_fraction": r.deletion_fraction,
                "trial": r.trial,
                "metrics": r.metrics,
                "status": r.status,
            }
            for r in results
        ],
    }


@router.get("/benchmarks/summary")
async def benchmark_summary():
    runner = deps.get_benchmark_runner()
    return runner.get_summary()


@router.get("/benchmarks/results")
async def benchmark_results():
    runner = deps.get_benchmark_runner()
    results = runner.get_results()
    return [
        {
            "benchmark_id": r.benchmark_id,
            "dataset": r.dataset,
            "algorithm": r.algorithm,
            "data_size": r.data_size,
            "deletion_fraction": r.deletion_fraction,
            "trial": r.trial,
            "metrics": r.metrics,
            "status": r.status,
        }
        for r in results
    ]


@router.get("/benchmarks/config")
async def benchmark_config():
    from training.benchmarks import BenchmarkDataset

    runner = deps.get_benchmark_runner()
    return {
        "datasets": [d.value for d in BenchmarkDataset],
        "data_sizes": runner._config.data_sizes,
        "deletion_fractions": runner._config.deletion_fractions,
        "algorithms": runner._config.algorithms,
        "num_trials": runner._config.num_trials,
    }


@router.get("/benchmarks/leaderboard")
async def benchmark_leaderboard(metric: str = "utility_retained", limit: int = 10):
    runner = deps.get_benchmark_runner()
    results = runner.get_results()
    completed = [r for r in results if r.status == "completed" and metric in r.metrics]
    sorted_results = sorted(completed, key=lambda r: r.metrics.get(metric, 0), reverse=True)
    return [
        {
            "rank": i + 1,
            "dataset": r.dataset,
            "algorithm": r.algorithm,
            "data_size": r.data_size,
            "deletion_fraction": r.deletion_fraction,
            metric: r.metrics.get(metric, 0),
        }
        for i, r in enumerate(sorted_results[:limit])
    ]


@router.get("/benchmarks/export/{fmt}")
async def export_benchmarks(fmt: str):
    import csv
    import io

    runner = deps.get_benchmark_runner()
    results = runner.get_results()
    if fmt == "csv":
        output = io.StringIO()
        if results:
            writer = csv.DictWriter(output, fieldnames=list(vars(results[0]).keys()))
            writer.writeheader()
            for r in results:
                row = {k: str(v) if isinstance(v, (dict, list)) else v for k, v in vars(r).items()}
                writer.writerow(row)
        return Response(content=output.getvalue(), media_type="text/csv")
    return [
        {
            "benchmark_id": r.benchmark_id,
            "dataset": r.dataset,
            "algorithm": r.algorithm,
            "data_size": r.data_size,
            "deletion_fraction": r.deletion_fraction,
            "trial": r.trial,
            "metrics": r.metrics,
            "status": r.status,
            "error": r.error,
        }
        for r in results
    ]


@router.get("/mlflow/runs")
async def mlflow_list_runs():
    tracker = deps.get_mlflow_tracker()
    return tracker.list_runs()


@router.get("/mlflow/runs/{run_id}")
async def mlflow_get_run(run_id: str):
    tracker = deps.get_mlflow_tracker()
    run = tracker.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return run


@router.get("/mlflow/runs/{run_id}/curves")
async def mlflow_get_curves(run_id: str):
    tracker = deps.get_mlflow_tracker()
    curves = tracker.get_training_curves(run_id)
    if curves is None:
        raise HTTPException(status_code=404, detail=f"Curves for run {run_id} not found")
    return curves


@router.post("/mlflow/compare")
async def mlflow_compare_runs(request: dict):
    tracker = deps.get_mlflow_tracker()
    run_ids = request.get("run_ids", [])
    result = tracker.compare_runs(run_ids)
    return result
