"""Continual learning endpoints (EWC, replay buffer, drift detection)."""

import uuid

from fastapi import APIRouter, HTTPException

from api import deps

router = APIRouter()


@router.get("/continual/stats")
async def continual_learning_stats():
    cl = deps.get_continual_learning()
    return cl.get_stats()


@router.post("/continual/tasks")
async def add_continual_task(request: dict):
    cl = deps.get_continual_learning()
    task = cl.add_task(request.get("task_id", str(uuid.uuid4())), request.get("metadata"))
    return task


@router.get("/continual/tasks")
async def list_continual_tasks():
    cl = deps.get_continual_learning()
    return {"tasks": [cl.get_task(tid) for tid in cl.get_stats().get("tasks", [])]}


@router.get("/continual/tasks/{task_id}")
async def get_continual_task(task_id: str):
    cl = deps.get_continual_learning()
    task = cl.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


@router.post("/continual/samples")
async def record_continual_sample(request: dict):
    cl = deps.get_continual_learning()
    cl.record_sample(
        input_data=request.get("input_data", []),
        target=request.get("target"),
        task_id=request.get("task_id", "default"),
        importance=request.get("importance", 0.5),
        confidence=request.get("confidence", 0.0),
        loss=request.get("loss", 0.0),
        metadata=request.get("metadata"),
    )
    return {"success": True}


@router.post("/continual/ewc/estimate")
async def estimate_ewc(request: dict):
    cl = deps.get_continual_learning()
    dataset = request.get("dataset", [])
    task_id = request.get("task_id", "default")
    num_samples = request.get("num_samples", min(len(dataset), 200))
    result = cl.estimate_ewc(task_id, dataset, num_samples=num_samples)
    return result


@router.get("/continual/ewc/state")
async def ewc_state():
    cl = deps.get_continual_learning()
    stats = cl.get_stats()
    return stats.get("ewc", {})


@router.post("/continual/replay/sample")
async def sample_replay(request: dict):
    cl = deps.get_continual_learning()
    samples = cl.sample_replay(
        n=request.get("n", 32),
        task_id=request.get("task_id"),
    )
    return {"samples": samples, "count": len(samples)}


@router.get("/continual/replay/stats")
async def replay_stats():
    cl = deps.get_continual_learning()
    stats = cl.get_stats()
    return stats.get("replay_buffer", {})


@router.post("/continual/drift/record")
async def record_drift(request: dict):
    cl = deps.get_continual_learning()
    result = cl.detect_drift(
        metric_name=request.get("metric_name", "confidence"),
        value=request.get("value", 0.0),
    )
    return result


@router.get("/continual/drift/alerts")
async def drift_alerts(n: int = 10):
    cl = deps.get_continual_learning()
    return {"alerts": cl.get_drift_alerts(n)}


@router.get("/continual/drift/state")
async def drift_state(metric: str = "confidence"):
    cl = deps.get_continual_learning()
    return cl.get_drift_state(metric)


@router.get("/continual/drift/stats")
async def drift_stats():
    cl = deps.get_continual_learning()
    stats = cl.get_stats()
    return stats.get("drift_detector", {})
