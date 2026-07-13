from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, DatabaseSession, default_rate_limiter, require_permission
from app.core.logging import get_logger
from app.core.rbac import Permission
from app.infrastructure.external.ml_engine import ml_engine_client, MLEngineClientError

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(default_rate_limiter), Depends(require_permission(Permission.EXPLAIN_READ))])


class ExplainSamplesRequest(BaseModel):
    samples: list[list[float]]
    feature_names: Optional[list[str]] = None
    method: str = "shap"


class ExplainFeaturesRequest(BaseModel):
    dataset: list[list[float]]
    feature_names: Optional[list[str]] = None
    method: str = "shap"


class ExplainCompareRequest(BaseModel):
    pre_unlearn_samples: list[list[float]]
    post_unlearn_samples: list[list[float]]
    feature_names: Optional[list[str]] = None
    method: str = "shap"


class PrivacyHeatmapRequest(BaseModel):
    samples: list[list[float]]
    privacy_scores: list[float]
    feature_names: Optional[list[str]] = None


class DriftRequest(BaseModel):
    pre_confidences: list[float]
    post_confidences: list[float]
    pre_importances: list[dict[str, float]]
    post_importances: list[dict[str, float]]


@router.post("/samples", status_code=status.HTTP_200_OK)
async def explain_samples(
    request: ExplainSamplesRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        result = await ml_engine_client.explain_samples(
            samples=request.samples,
            feature_names=request.feature_names,
            method=request.method,
        )
        return result
    except MLEngineClientError as e:
        logger.error("Explain samples failed for user %s: %s", current_user["user_id"], str(e))
        return {"error": str(e), "method": request.method, "samples": len(request.samples)}


@router.post("/features", status_code=status.HTTP_200_OK)
async def explain_features(
    request: ExplainFeaturesRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        result = await ml_engine_client.explain_features(
            dataset=request.dataset,
            feature_names=request.feature_names,
            method=request.method,
        )
        return result
    except MLEngineClientError as e:
        logger.error("Explain features failed for user %s: %s", current_user["user_id"], str(e))
        return {"error": str(e), "method": request.method, "samples": len(request.dataset)}


@router.post("/compare", status_code=status.HTTP_200_OK)
async def compare_explanations(
    request: ExplainCompareRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        result = await ml_engine_client.compare_explanations(
            pre_unlearn_samples=request.pre_unlearn_samples,
            post_unlearn_samples=request.post_unlearn_samples,
            feature_names=request.feature_names,
            method=request.method,
        )
        return result
    except MLEngineClientError as e:
        logger.error("Compare explanations failed for user %s: %s", current_user["user_id"], str(e))
        return {"error": str(e), "method": request.method}


@router.post("/privacy-heatmap", status_code=status.HTTP_200_OK)
async def privacy_heatmap(
    request: PrivacyHeatmapRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        result = await ml_engine_client.privacy_heatmap(
            samples=request.samples,
            privacy_scores=request.privacy_scores,
            feature_names=request.feature_names,
        )
        return result
    except MLEngineClientError as e:
        logger.error("Privacy heatmap failed for user %s: %s", current_user["user_id"], str(e))
        return {"error": str(e)}


@router.post("/drift", status_code=status.HTTP_200_OK)
async def model_drift(
    request: DriftRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        result = await ml_engine_client.model_drift(
            pre_confidences=request.pre_confidences,
            post_confidences=request.post_confidences,
            pre_importances=request.pre_importances,
            post_importances=request.post_importances,
        )
        return result
    except MLEngineClientError as e:
        logger.error("Model drift failed for user %s: %s", current_user["user_id"], str(e))
        return {"error": str(e)}


@router.get("/methods", status_code=status.HTTP_200_OK)
async def list_methods(
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        result = await ml_engine_client.list_explain_methods()
        return result
    except MLEngineClientError as e:
        logger.error("List explain methods failed: %s", str(e))
        return {"methods": []}
