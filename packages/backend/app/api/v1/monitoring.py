"""System monitoring endpoints.

Thin read-only aggregation layer that surfaces ML-engine and adapter health,
registry statistics, and inference metrics to the dashboard's monitoring page.
All data is proxied from the ML engine; the backend itself adds only aggregate
availability flags.
"""
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUser, default_rate_limiter, require_permission
from app.core.logging import get_logger
from app.core.rbac import Permission
from app.infrastructure.external.ml_engine import MLEngineClientError, ml_engine_client

logger = get_logger(__name__)

router = APIRouter(
    prefix="/monitoring",
    tags=["Monitoring"],
    dependencies=[Depends(default_rate_limiter), Depends(require_permission(Permission.MONITORING_READ))],
)


async def _proxy_json(path: str, timeout: int = 15) -> dict[str, Any]:
    """Proxy a GET to the ML engine and return JSON, mapping failures to 502."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(
                f"{ml_engine_client._base_url}{path}",
                headers=ml_engine_client._headers,
            )
            resp.raise_for_status()
            return resp.json()
    except MLEngineClientError as e:
        raise _proxy_error(e)
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.RequestError as e:
        raise _proxy_error(e)


def _proxy_error(e: Exception) -> HTTPException:
    logger.error("Monitoring proxy failed: %s", str(e))
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"ML engine unavailable: {e}")


@router.get("/health")
async def system_health(current_user: CurrentUser = None) -> dict[str, Any]:
    try:
        ml = await ml_engine_client.health()
    except (MLEngineClientError, httpx.HTTPError) as e:
        ml = {"status": "unavailable", "detail": str(e)}
    return {
        "backend": "healthy",
        "ml_engine": ml,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/inference")
async def inference_metrics(current_user: CurrentUser = None) -> dict[str, Any]:
    return await _proxy_json("/inference/metrics")


@router.get("/controller")
async def controller_health(current_user: CurrentUser = None) -> dict[str, Any]:
    try:
        return await ml_engine_client.get_controller_health()
    except (MLEngineClientError, httpx.HTTPError) as e:
        raise _proxy_error(e)


@router.get("/registry")
async def registry_stats(current_user: CurrentUser = None) -> dict[str, Any]:
    try:
        return await ml_engine_client.get_registry_stats()
    except (MLEngineClientError, httpx.HTTPError) as e:
        raise _proxy_error(e)
