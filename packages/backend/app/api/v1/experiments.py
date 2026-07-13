from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, DatabaseSession, default_rate_limiter, require_permission
from app.core.logging import get_logger
from app.core.rbac import Permission
from app.infrastructure.database.models import ExperimentModel, ExperimentRunModel

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(default_rate_limiter), Depends(require_permission(Permission.BENCHMARKS_WRITE))])


class CreateExperimentRequest(BaseModel):
    name: str
    description: Optional[str] = None
    experiment_type: str = "benchmark"
    config: dict = {}
    tags: list[str] = []
    algorithm: Optional[str] = None
    num_trials: int = 1


class UpdateExperimentRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    config: Optional[dict] = None
    tags: Optional[list[str]] = None
    metrics: Optional[dict] = None
    algorithm: Optional[str] = None
    num_trials: Optional[int] = None


class CreateExperimentRunRequest(BaseModel):
    algorithm: str
    dataset_name: Optional[str] = None
    data_size: Optional[int] = None
    deletion_fraction: Optional[float] = None


class UpdateExperimentRunRequest(BaseModel):
    status: Optional[str] = None
    metrics: Optional[dict] = None
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_experiment(
    request: CreateExperimentRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    now = datetime.now(timezone.utc)
    experiment = ExperimentModel(
        id=str(uuid4()),
        tenant_id=current_user["tenant_id"],
        name=request.name,
        description=request.description,
        experiment_type=request.experiment_type,
        status="draft",
        config=request.config,
        tags=request.tags,
        algorithm=request.algorithm,
        num_trials=request.num_trials,
        created_by=current_user["user_id"],
        created_at=now,
        updated_at=now,
    )
    session.add(experiment)
    await session.commit()
    await session.refresh(experiment)
    return {
        "id": experiment.id,
        "name": experiment.name,
        "status": experiment.status,
        "experiment_type": experiment.experiment_type,
        "created_at": experiment.created_at.isoformat(),
    }


@router.get("")
async def list_experiments(
    current_user: CurrentUser,
    session: DatabaseSession,
    status_filter: Optional[str] = Query(None, alias="status"),
    experiment_type: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    from sqlalchemy import select, desc

    query = select(ExperimentModel).where(
        ExperimentModel.tenant_id == current_user["tenant_id"],
    )
    if status_filter:
        query = query.where(ExperimentModel.status == status_filter)
    if experiment_type:
        query = query.where(ExperimentModel.experiment_type == experiment_type)
    query = query.order_by(desc(ExperimentModel.created_at)).offset(offset).limit(limit)

    result = await session.execute(query)
    experiments = result.scalars().all()
    return [
        {
            "id": e.id,
            "name": e.name,
            "experiment_type": e.experiment_type,
            "status": e.status,
            "algorithm": e.algorithm,
            "num_trials": e.num_trials,
            "config": e.config,
            "tags": e.tags,
            "metrics": e.metrics,
            "created_at": e.created_at.isoformat(),
            "updated_at": e.updated_at.isoformat(),
        }
        for e in experiments
    ]


@router.get("/{experiment_id}")
async def get_experiment(
    experiment_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    from sqlalchemy import select

    query = select(ExperimentModel).where(
        ExperimentModel.id == experiment_id,
        ExperimentModel.tenant_id == current_user["tenant_id"],
    )
    result = await session.execute(query)
    experiment = result.scalar_one_or_none()
    if not experiment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    runs_query = select(ExperimentRunModel).where(
        ExperimentRunModel.experiment_id == experiment_id,
    ).order_by(ExperimentRunModel.run_index)
    runs_result = await session.execute(runs_query)
    runs = runs_result.scalars().all()

    return {
        "id": experiment.id,
        "name": experiment.name,
        "description": experiment.description,
        "experiment_type": experiment.experiment_type,
        "status": experiment.status,
        "config": experiment.config,
        "tags": experiment.tags,
        "metrics": experiment.metrics,
        "algorithm": experiment.algorithm,
        "num_trials": experiment.num_trials,
        "dataset_ids": experiment.dataset_ids,
        "model_version_ids": experiment.model_version_ids,
        "created_by": experiment.created_by,
        "started_at": experiment.started_at.isoformat() if experiment.started_at else None,
        "completed_at": experiment.completed_at.isoformat() if experiment.completed_at else None,
        "created_at": experiment.created_at.isoformat(),
        "updated_at": experiment.updated_at.isoformat(),
        "runs": [
            {
                "id": r.id,
                "run_index": r.run_index,
                "algorithm": r.algorithm,
                "dataset_name": r.dataset_name,
                "data_size": r.data_size,
                "deletion_fraction": r.deletion_fraction,
                "status": r.status,
                "metrics": r.metrics,
                "processing_time_ms": r.processing_time_ms,
                "error_message": r.error_message,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in runs
        ],
    }


@router.put("/{experiment_id}")
async def update_experiment(
    experiment_id: str,
    request: UpdateExperimentRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    from sqlalchemy import select

    query = select(ExperimentModel).where(
        ExperimentModel.id == experiment_id,
        ExperimentModel.tenant_id == current_user["tenant_id"],
    )
    result = await session.execute(query)
    experiment = result.scalar_one_or_none()
    if not experiment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(experiment, field, value)
    experiment.updated_at = datetime.now(timezone.utc)

    if request.status == "running" and experiment.started_at is None:
        experiment.started_at = datetime.now(timezone.utc)
    if request.status == "completed" and experiment.completed_at is None:
        experiment.completed_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(experiment)
    return {"status": "updated", "id": experiment.id}


@router.delete("/{experiment_id}")
async def delete_experiment(
    experiment_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    from sqlalchemy import select

    query = select(ExperimentModel).where(
        ExperimentModel.id == experiment_id,
        ExperimentModel.tenant_id == current_user["tenant_id"],
    )
    result = await session.execute(query)
    experiment = result.scalar_one_or_none()
    if not experiment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    await session.delete(experiment)
    await session.commit()
    return {"status": "deleted", "id": experiment_id}


@router.post("/{experiment_id}/runs", status_code=status.HTTP_201_CREATED)
async def create_experiment_run(
    experiment_id: str,
    request: CreateExperimentRunRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    from sqlalchemy import select, func

    query = select(ExperimentModel).where(
        ExperimentModel.id == experiment_id,
        ExperimentModel.tenant_id == current_user["tenant_id"],
    )
    result = await session.execute(query)
    experiment = result.scalar_one_or_none()
    if not experiment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    count_query = select(func.count()).select_from(ExperimentRunModel).where(
        ExperimentRunModel.experiment_id == experiment_id,
    )
    count_result = await session.execute(count_query)
    run_index = count_result.scalar() or 0

    run = ExperimentRunModel(
        id=str(uuid4()),
        experiment_id=experiment_id,
        run_index=run_index,
        algorithm=request.algorithm,
        dataset_name=request.dataset_name,
        data_size=request.data_size,
        deletion_fraction=request.deletion_fraction,
        status="pending",
        created_at=datetime.now(timezone.utc),
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return {
        "id": run.id,
        "run_index": run.run_index,
        "status": run.status,
    }


@router.put("/{experiment_id}/runs/{run_id}")
async def update_experiment_run(
    experiment_id: str,
    run_id: str,
    request: UpdateExperimentRunRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    from sqlalchemy import select

    query = select(ExperimentRunModel).where(
        ExperimentRunModel.id == run_id,
        ExperimentRunModel.experiment_id == experiment_id,
    )
    result = await session.execute(query)
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment run not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(run, field, value)

    if request.status == "running" and run.started_at is None:
        run.started_at = datetime.now(timezone.utc)
    if request.status in ("completed", "failed") and run.completed_at is None:
        run.completed_at = datetime.now(timezone.utc)

    await session.commit()
    return {"status": "updated", "id": run.id}
