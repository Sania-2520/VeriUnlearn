from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, DatabaseSession, default_rate_limiter, require_permission
from app.core.logging import get_logger
from app.core.rbac import Permission
from app.infrastructure.external.ml_engine import MLEngineClientError, ml_engine_client

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(default_rate_limiter), Depends(require_permission(Permission.CONTINUAL_LEARNING_WRITE))])


class ContinualSampleRequest(BaseModel):
    input_data: list[float]
    target: Any = None
    task_id: str = "default"
    importance: float = 0.5
    confidence: float = 0.0
    loss: float = 0.0
    metadata: Optional[dict] = None


class DriftCheckRequest(BaseModel):
    metric_name: str = "confidence"
    value: float = 0.0


class EWCRequest(BaseModel):
    task_id: str
    num_samples: int = 200


class AddTaskRequest(BaseModel):
    task_id: str
    metadata: Optional[dict] = None


@router.get("/stats", status_code=status.HTTP_200_OK)
async def get_continual_stats(
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        return await ml_engine_client.get_continual_stats()
    except MLEngineClientError as e:
        logger.error("Get continual stats failed: %s", str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/samples", status_code=status.HTTP_200_OK)
async def record_sample(
    request: ContinualSampleRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        return await ml_engine_client.record_continual_sample(
            {
                "input_data": request.input_data,
                "target": request.target,
                "task_id": request.task_id,
                "importance": request.importance,
                "confidence": request.confidence,
                "loss": request.loss,
                "metadata": request.metadata,
            }
        )
    except MLEngineClientError as e:
        logger.error("Record sample failed: %s", str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/drift/alerts", status_code=status.HTTP_200_OK)
async def get_drift_alerts(
    n: int = Query(10, le=100),
    current_user: CurrentUser = None,
    session: DatabaseSession = None,
):
    try:
        return await ml_engine_client.get_continual_drift_alerts(n=n)
    except MLEngineClientError as e:
        logger.error("Get drift alerts failed: %s", str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/drift/check", status_code=status.HTTP_200_OK)
async def check_drift(
    request: DriftCheckRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{ml_engine_client._base_url}/continual/drift/check",
                json=request.model_dump(),
                headers=ml_engine_client._headers,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("Check drift failed: %s", str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/ewc/estimate", status_code=status.HTTP_200_OK)
async def estimate_ewc(
    request: EWCRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{ml_engine_client._base_url}/continual/ewc/estimate",
                json=request.model_dump(),
                headers=ml_engine_client._headers,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("EWC estimation failed: %s", str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/tasks", status_code=status.HTTP_201_CREATED)
async def add_task(
    request: AddTaskRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{ml_engine_client._base_url}/continual/tasks",
                json=request.model_dump(),
                headers=ml_engine_client._headers,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("Add task failed: %s", str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/tasks", status_code=status.HTTP_200_OK)
async def list_tasks(
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{ml_engine_client._base_url}/continual/tasks",
                headers=ml_engine_client._headers,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("List tasks failed: %s", str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/tasks/{task_id}", status_code=status.HTTP_200_OK)
async def get_task(
    task_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{ml_engine_client._base_url}/continual/tasks/{task_id}",
                headers=ml_engine_client._headers,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("Get task %s failed: %s", task_id, str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


import httpx  # noqa: E402
