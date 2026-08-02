from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel

from app.api.deps import CurrentUser, DatabaseSession, default_rate_limiter, require_permission
from app.core.logging import get_logger
from app.core.rbac import Permission
from app.infrastructure.external.ml_engine import MLEngineClientError, ml_engine_client

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(default_rate_limiter), Depends(require_permission(Permission.BENCHMARKS_READ))])

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=30,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=20),
        )
    return _client


class RunBenchmarkRequest(BaseModel):
    dataset: str = "synthetic_linear"
    data_sizes: list[int] = [100, 500, 1000]
    deletion_fractions: list[float] = [0.01, 0.05, 0.1]
    algorithms: list[str] = ["sisa", "influence", "certified_removal", "hybrid"]
    num_trials: int = 3


@router.post("/run", status_code=status.HTTP_200_OK)
async def run_benchmarks(
    request: RunBenchmarkRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
    _: None = Depends(require_permission(Permission.BENCHMARKS_WRITE)),
):
    try:
        result = await ml_engine_client.run_benchmarks(config=request.model_dump())
        return result
    except MLEngineClientError as e:
        logger.error("Run benchmarks failed for user %s: %s", current_user["user_id"], str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/summary", status_code=status.HTTP_200_OK)
async def get_benchmark_summary(
    current_user: CurrentUser,
    session: DatabaseSession,
    _: None = Depends(require_permission(Permission.BENCHMARKS_READ)),
):
    try:
        return await ml_engine_client.get_benchmark_summary()
    except MLEngineClientError as e:
        logger.error("Get benchmark summary failed: %s", str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/results", status_code=status.HTTP_200_OK)
async def list_benchmark_results(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    algorithm: Optional[str] = Query(None),
    dataset: Optional[str] = Query(None),
    _: None = Depends(require_permission(Permission.BENCHMARKS_READ)),
):
    try:
        params = {"limit": limit, "offset": offset}
        if algorithm:
            params["algorithm"] = algorithm
        if dataset:
            params["dataset"] = dataset
        resp = await _get_client().get(
            f"{ml_engine_client._base_url}/benchmarks/results",
            params=params,
            headers=ml_engine_client._headers,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error("List benchmark results failed: %s", str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/leaderboard", status_code=status.HTTP_200_OK)
async def get_leaderboard(
    metric: str = Query("utility_retained"),
    limit: int = Query(10, le=50),
    _: None = Depends(require_permission(Permission.BENCHMARKS_READ)),
):
    try:
        resp = await _get_client().get(
            f"{ml_engine_client._base_url}/benchmarks/leaderboard",
            params={"metric": metric, "limit": limit},
            headers=ml_engine_client._headers,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error("Get leaderboard failed: %s", str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/export/{format}", status_code=status.HTTP_200_OK)
async def export_benchmarks(
    format: str,
    _: None = Depends(require_permission(Permission.BENCHMARKS_READ)),
):
    if format not in ("csv", "json"):
        raise HTTPException(status_code=400, detail="Format must be 'csv' or 'json'")
    try:
        resp = await _get_client().get(
            f"{ml_engine_client._base_url}/benchmarks/export/{format}",
            headers=ml_engine_client._headers,
        )
        resp.raise_for_status()
        if format == "csv":
            return Response(content=resp.text, media_type="text/csv")
        return resp.json()
    except Exception as e:
        logger.error("Export benchmarks failed: %s", str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))



