from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, DatabaseSession, default_rate_limiter, require_permission
from app.core.logging import get_logger
from app.core.rbac import Permission
from app.infrastructure.external.ml_engine import ml_engine_client, MLEngineClientError

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(default_rate_limiter), Depends(require_permission(Permission.TRAINING_WRITE))])


class LoRATrainRequest(BaseModel):
    conversations: list[dict] = []
    model_name: str = "Qwen/Qwen2.5-0.5B-Instruct"
    lora_r: int = 16
    lora_alpha: int = 32
    num_epochs: int = 3
    batch_size: int = 4
    learning_rate: float = 2e-4
    remove_data_ids: list[str] = []


class DistillationRequest(BaseModel):
    teacher_model_name: str
    student_model_name: str = ""
    temperature: float = 4.0
    alpha: float = 0.5
    num_epochs: int = 5
    dataset_name: str = "synthetic"


class TrainingJobRequest(BaseModel):
    job_type: str = "lora_training"
    model_name: str = ""
    dataset_name: str = ""
    priority: str = "medium"
    config: dict = {}
    total_epochs: int = 3


class CheckpointRequest(BaseModel):
    checkpoint_id: str
    export_path: Optional[str] = None


class ModelRegistryRequest(BaseModel):
    model_name: str
    checkpoint_path: str
    algorithm: str = "hybrid"
    parent_version_id: Optional[str] = None
    config: dict = {}
    metrics: dict = {}


@router.post("/lora", status_code=status.HTTP_200_OK)
async def train_lora(
    request: LoRATrainRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        result = await ml_engine_client.train_lora(
            conversations=request.conversations,
            model_name=request.model_name,
            lora_r=request.lora_r,
            lora_alpha=request.lora_alpha,
            num_epochs=request.num_epochs,
            batch_size=request.batch_size,
            learning_rate=request.learning_rate,
            remove_data_ids=request.remove_data_ids,
        )
        return result
    except MLEngineClientError as e:
        logger.error("LoRA training failed for user %s: %s", current_user["user_id"], str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/distill", status_code=status.HTTP_200_OK)
async def run_distillation(
    request: DistillationRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        async with httpx.AsyncClient(timeout=600) as client:
            resp = await client.post(
                f"{ml_engine_client._base_url}/train/distill",
                json=request.model_dump(),
                headers=ml_engine_client._headers,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("Distillation failed: %s", str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/start", status_code=status.HTTP_201_CREATED)
async def start_training(
    request: TrainingJobRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    """Alias for generic training-job submission used by the dashboard."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{ml_engine_client._base_url}/train/submit",
                json=request.model_dump(),
                headers=ml_engine_client._headers,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("Start training failed: %s", str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/submit", status_code=status.HTTP_201_CREATED)
async def submit_training_job(
    request: TrainingJobRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{ml_engine_client._base_url}/train/submit",
                json=request.model_dump(),
                headers=ml_engine_client._headers,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("Submit training job failed: %s", str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/jobs", status_code=status.HTTP_200_OK)
async def list_training_jobs(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, le=200),
    current_user: CurrentUser = None,
    session: DatabaseSession = None,
):
    try:
        params = {}
        if status_filter:
            params["status"] = status_filter
        if limit:
            params["limit"] = limit
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{ml_engine_client._base_url}/train/jobs",
                params=params,
                headers=ml_engine_client._headers,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("List training jobs failed: %s", str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/jobs/{job_id}", status_code=status.HTTP_200_OK)
async def get_training_job(
    job_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{ml_engine_client._base_url}/train/jobs/{job_id}",
                headers=ml_engine_client._headers,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("Get training job %s failed: %s", job_id, str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/jobs/{job_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_training_job(
    job_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{ml_engine_client._base_url}/train/jobs/{job_id}/cancel",
                headers=ml_engine_client._headers,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("Cancel training job %s failed: %s", job_id, str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/checkpoints", status_code=status.HTTP_200_OK)
async def list_checkpoints(
    limit: int = Query(20, le=100),
    current_user: CurrentUser = None,
    session: DatabaseSession = None,
):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{ml_engine_client._base_url}/train/checkpoints?limit={limit}",
                headers=ml_engine_client._headers,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("List checkpoints failed: %s", str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/checkpoints/export", status_code=status.HTTP_200_OK)
async def export_checkpoint(
    request: CheckpointRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{ml_engine_client._base_url}/train/checkpoints/export",
                json=request.model_dump(),
                headers=ml_engine_client._headers,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("Export checkpoint failed: %s", str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/gpu", status_code=status.HTTP_200_OK)
async def get_gpu_status(
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{ml_engine_client._base_url}/train/gpu",
                headers=ml_engine_client._headers,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("Get GPU status failed: %s", str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/queue/stats", status_code=status.HTTP_200_OK)
async def get_queue_stats(
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{ml_engine_client._base_url}/train/queue/stats",
                headers=ml_engine_client._headers,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("Get queue stats failed: %s", str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/model/register", status_code=status.HTTP_201_CREATED)
async def register_model_version(
    request: ModelRegistryRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{ml_engine_client._base_url}/model/register",
                json=request.model_dump(),
                headers=ml_engine_client._headers,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("Register model version failed: %s", str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/model/versions", status_code=status.HTTP_200_OK)
async def list_model_versions(
    model_name: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    current_user: CurrentUser = None,
    session: DatabaseSession = None,
):
    try:
        params = {"limit": limit}
        if model_name:
            params["model_name"] = model_name
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{ml_engine_client._base_url}/model/versions",
                params=params,
                headers=ml_engine_client._headers,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("List model versions failed: %s", str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


import httpx  # noqa: E402
