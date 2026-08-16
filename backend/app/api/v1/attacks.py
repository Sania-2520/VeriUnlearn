from __future__ import annotations

from fastapi import APIRouter, Body

from app.api.deps import CurrentUser, DbSession
from app.services.attacks import AttackService

router = APIRouter(prefix="/attacks", tags=["attacks"])


@router.post("/membership/{model_id}")
async def membership_inference(model_id: str, db: DbSession, user: CurrentUser) -> dict:
    return await AttackService(db).membership_inference(model_id)


@router.post("/membership/after-unlearning")
async def membership_after_unlearning(
    db: DbSession,
    user: CurrentUser,
    payload: dict = Body(..., example={"model_id": "...", "deleted_record_ids": ["..."]}),
) -> dict:
    return await AttackService(db).membership_after_unlearning(
        payload["model_id"], payload.get("deleted_record_ids", [])
    )


@router.post("/backdoor/{model_id}")
async def backdoor_persistence(
    model_id: str, db: DbSession, user: CurrentUser, poison_fraction: float = 0.1
) -> dict:
    return await AttackService(db).backdoor_persistence(model_id, poison_fraction=poison_fraction)


@router.post("/inversion/{model_id}")
async def model_inversion(
    model_id: str, db: DbSession, user: CurrentUser, target_label: int = 1
) -> dict:
    return await AttackService(db).model_inversion(model_id, target_label=target_label)
