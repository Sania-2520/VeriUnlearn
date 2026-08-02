from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, DatabaseSession, default_rate_limiter, require_permission
from app.core.logging import get_logger
from app.core.rbac import Permission
from app.infrastructure.external.ml_engine import MLEngineClientError, ml_engine_client

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(default_rate_limiter), Depends(require_permission(Permission.ADAPTERS_WRITE))])


class RegisterAdapterRequest(BaseModel):
    adapter_name: str
    adapter_path: str
    base_model_name: str = ""
    config: dict = {}
    tags: dict = {}


class AdapterVersionActionRequest(BaseModel):
    adapter_name: str
    version_id: str


class CanarySetupRequest(BaseModel):
    adapter_name: str
    stable_version_id: str
    canary_version_id: str
    canary_traffic_pct: Optional[float] = None


class RecordMetricsRequest(BaseModel):
    adapter_name: str
    version_id: str
    latency_ms: float = 0.0
    success: bool = True


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_adapter(
    request: RegisterAdapterRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        result = await ml_engine_client.register_adapter(
            adapter_name=request.adapter_name,
            adapter_path=request.adapter_path,
            base_model_name=request.base_model_name,
            config=request.config,
            tags=request.tags,
        )
        return result
    except MLEngineClientError as e:
        logger.error("Register adapter failed for user %s: %s", current_user["user_id"], str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("", status_code=status.HTTP_200_OK)
async def list_adapters(
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        return await ml_engine_client.list_adapters()
    except MLEngineClientError as e:
        logger.error("List adapters failed: %s", str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/activate", status_code=status.HTTP_200_OK)
async def activate_adapter(
    request: AdapterVersionActionRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        return await ml_engine_client.activate_adapter(
            adapter_name=request.adapter_name,
            version_id=request.version_id,
        )
    except MLEngineClientError as e:
        logger.error("Activate adapter failed: %s", str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/deactivate", status_code=status.HTTP_200_OK)
async def deactivate_adapter(
    request: AdapterVersionActionRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        return await ml_engine_client.deactivate_adapter(
            adapter_name=request.adapter_name,
            version_id=request.version_id,
        )
    except MLEngineClientError as e:
        logger.error("Deactivate adapter failed: %s", str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/rollback", status_code=status.HTTP_200_OK)
async def rollback_adapter(
    adapter_name: str,
    current_user: CurrentUser,
    session: DatabaseSession,
    request: Optional[dict] = None,
) -> Any:
    target_version_id = (request or {}).get("version_id") if request else None
    try:
        return await ml_engine_client.rollback_adapter(
            adapter_name=adapter_name,
            version_id=target_version_id,
        )
    except MLEngineClientError as e:
        logger.error("Rollback adapter failed: %s", str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/controller/health", status_code=status.HTTP_200_OK)
async def get_controller_health(
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        return await ml_engine_client.get_controller_health()
    except MLEngineClientError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/{adapter_name}/versions", status_code=status.HTTP_200_OK)
async def get_versions(
    adapter_name: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        return await ml_engine_client.get_adapter_versions(adapter_name)
    except MLEngineClientError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/{adapter_name}/health", status_code=status.HTTP_200_OK)
async def get_adapter_health(
    adapter_name: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        return await ml_engine_client.get_adapter_health(adapter_name)
    except MLEngineClientError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/{adapter_name}/active", status_code=status.HTTP_200_OK)
async def get_active_adapter(
    adapter_name: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        return await ml_engine_client.get_active_adapter(adapter_name)
    except MLEngineClientError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/{adapter_name}/latency", status_code=status.HTTP_200_OK)
async def get_adapter_latency(
    adapter_name: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        return await ml_engine_client.get_adapter_latency_stats(adapter_name)
    except MLEngineClientError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/canary/setup", status_code=status.HTTP_200_OK)
async def setup_canary(
    request: CanarySetupRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        return await ml_engine_client.setup_canary(
            adapter_name=request.adapter_name,
            stable_version_id=request.stable_version_id,
            canary_version_id=request.canary_version_id,
            canary_traffic_pct=request.canary_traffic_pct,
        )
    except MLEngineClientError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/{adapter_name}/canary/promote", status_code=status.HTTP_200_OK)
async def promote_canary(
    adapter_name: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        return await ml_engine_client.promote_canary(adapter_name)
    except MLEngineClientError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/metrics", status_code=status.HTTP_200_OK)
async def record_adapter_metrics(
    request: RecordMetricsRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        return await ml_engine_client.record_adapter_metrics(
            adapter_name=request.adapter_name,
            version_id=request.version_id,
            latency_ms=request.latency_ms,
            success=request.success,
        )
    except MLEngineClientError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/registry/stats", status_code=status.HTTP_200_OK)
async def get_registry_stats(
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        return await ml_engine_client.get_registry_stats()
    except MLEngineClientError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
