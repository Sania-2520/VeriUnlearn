"""Model Registry API.

Proxies model-version registry operations to the ML engine. The dashboard's
"Models" page calls these under ``/api/v1/models``; the canonical backend
forwards them to the engine's ``/registry/versions`` surface.
"""
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, default_rate_limiter, require_permission
from app.core.logging import get_logger
from app.core.rbac import Permission
from app.infrastructure.external.ml_engine import MLEngineClientError, ml_engine_client

logger = get_logger(__name__)

router = APIRouter(
    prefix="/models",
    tags=["Model Registry"],
    dependencies=[Depends(default_rate_limiter), Depends(require_permission(Permission.TRAINING_WRITE))],
)


def _proxy_error(e: Exception) -> HTTPException:
    logger.error("Model registry proxy failed: %s", str(e))
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"ML engine unavailable: {e}")


@router.get("/versions")
async def list_model_versions(
    model_name: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    current_user: CurrentUser = None,
) -> Any:
    try:
        params = {"limit": limit}
        if model_name:
            params["model_name"] = model_name
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{ml_engine_client._base_url}/registry/versions",
                params=params,
                headers=ml_engine_client._headers,
            )
            resp.raise_for_status()
            return resp.json()
    except MLEngineClientError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _proxy_error(e)


@router.get("/{model_name}/versions/{version_id}")
async def get_model_version(
    model_name: str,
    version_id: str,
    current_user: CurrentUser = None,
) -> Any:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{ml_engine_client._base_url}/registry/versions/{model_name}/{version_id}",
                headers=ml_engine_client._headers,
            )
            resp.raise_for_status()
            return resp.json()
    except MLEngineClientError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _proxy_error(e)


@router.post("/{model_name}/versions/{version_id}/rollback")
async def rollback_model_version(
    model_name: str,
    version_id: str,
    current_user: CurrentUser = None,
) -> Any:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{ml_engine_client._base_url}/registry/versions/{model_name}/{version_id}/rollback",
                headers=ml_engine_client._headers,
            )
            resp.raise_for_status()
            return resp.json()
    except MLEngineClientError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _proxy_error(e)


@router.post("/{model_name}/versions/{version_id}/verify")
async def verify_model_version(
    model_name: str,
    version_id: str,
    current_user: CurrentUser = None,
) -> Any:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{ml_engine_client._base_url}/registry/versions/{model_name}/{version_id}/verify",
                headers=ml_engine_client._headers,
            )
            resp.raise_for_status()
            return resp.json()
    except MLEngineClientError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _proxy_error(e)
