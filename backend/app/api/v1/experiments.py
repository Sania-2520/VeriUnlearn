from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.dependencies import CurrentUser
from app.services.ab_test_service import ab_test_service, Experiment

router = APIRouter(prefix="/experiments", tags=["A/B Testing"])


class ExperimentCreate(BaseModel):
    id: str
    name: str
    description: str = ""
    variants: list[dict]
    traffic_percentage: float = 1.0


class EventTrack(BaseModel):
    user_id: str
    event: str
    value: float = 0.0


@router.get("/")
async def list_experiments(user: CurrentUser):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return [e.model_dump() for e in ab_test_service.list_experiments()]


@router.post("/", status_code=201)
async def create_experiment(body: ExperimentCreate, user: CurrentUser):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    experiment = Experiment(**body.model_dump())
    return ab_test_service.create_experiment(experiment).model_dump()


@router.get("/{experiment_id}")
async def get_experiment(experiment_id: str, user: CurrentUser):
    experiment = ab_test_service.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment.model_dump()


@router.get("/{experiment_id}/assign")
async def assign_variant(experiment_id: str, user: CurrentUser):
    variant = ab_test_service.assign_variant(experiment_id, str(user.id))
    return {"variant": variant}


@router.post("/{experiment_id}/track")
async def track_event(experiment_id: str, body: EventTrack, user: CurrentUser):
    ab_test_service.track_event(experiment_id, body.user_id, body.event, body.value)
    return {"status": "tracked"}


@router.get("/{experiment_id}/results")
async def get_results(experiment_id: str, user: CurrentUser):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return ab_test_service.get_results(experiment_id)
