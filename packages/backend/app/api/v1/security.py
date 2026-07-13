from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, DatabaseSession, default_rate_limiter, require_permission
from app.core.logging import get_logger
from app.core.rbac import Permission
from app.infrastructure.external.ml_engine import ml_engine_client, MLEngineClientError

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(default_rate_limiter), Depends(require_permission(Permission.SECURITY_READ))])

_assessments: dict[str, dict] = {}


class CreateAssessmentRequest(BaseModel):
    model_version_id: str
    tests: list[str] = ["membership_inference", "model_extraction"]
    config: dict = {}


@router.post("/assessments", status_code=status.HTTP_202_ACCEPTED)
async def create_assessment(
    request: CreateAssessmentRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    assessment_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    assessment_data = {
        "id": assessment_id,
        "model_version_id": request.model_version_id,
        "tests": request.tests,
        "config": request.config,
        "user_id": current_user["user_id"],
        "tenant_id": current_user["tenant_id"],
        "status": "queued",
        "scores": {},
        "recommendations": [],
        "created_at": now,
        "updated_at": now,
    }
    _assessments[assessment_id] = assessment_data
    if "membership_inference" in request.tests:
        try:
            mia_result = await ml_engine_client.evaluate_mia(
                target_data_ids=[request.model_version_id],
                model_name=request.model_version_id,
                data_size=request.config.get("data_size", 0),
                config=request.config,
            )
            assessment_data["status"] = "completed"
            assessment_data["scores"]["membership_inference"] = mia_result.get("score", mia_result.get("mia_score", 0.0))
            assessment_data["results"] = mia_result
            assessment_data["recommendations"] = mia_result.get("recommendations", [])
        except MLEngineClientError as e:
            logger.error("ML engine MIA evaluation failed for assessment %s: %s", assessment_id, str(e))
            assessment_data["status"] = "failed"
            assessment_data["error"] = str(e)
    assessment_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    return {
        "assessment_id": assessment_id,
        "status": assessment_data["status"],
        "estimated_completion": assessment_data["updated_at"] if assessment_data["status"] == "completed" else None,
    }


@router.get("/assessments/{assessment_id}")
async def get_assessment(
    assessment_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    assessment = _assessments.get(assessment_id)
    if not assessment or assessment["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    return {
        "id": assessment["id"],
        "status": assessment["status"],
        "scores": assessment.get("scores", {}),
        "recommendations": assessment.get("recommendations", []),
        "model_version_id": assessment.get("model_version_id"),
        "tests": assessment.get("tests", []),
        "results": assessment.get("results", {}),
        "created_at": assessment.get("created_at"),
        "updated_at": assessment.get("updated_at"),
    }
    

class ModelInversionRequest(BaseModel):
    target_classes: list[int] = [0, 1]
    input_dim: int = 20
    iterations: int = 500
    learning_rate: float = 0.1


class ShadowMIARequest(BaseModel):
    num_shadow_models: int = 5
    shadow_data_size: int = 200
    shadow_epochs: int = 50


class ModelExtractionRequest(BaseModel):
    input_dim: int = 20
    num_classes: int = 2
    num_queries: int = 1000
    extraction_epochs: int = 200


@router.post("/attacks/model-inversion")
async def model_inversion_attack(
    request: ModelInversionRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        result = await ml_engine_client.run_model_inversion(
            target_classes=request.target_classes,
            input_dim=request.input_dim,
            iterations=request.iterations,
            learning_rate=request.learning_rate,
        )
        return result
    except MLEngineClientError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/attacks/shadow-mia")
async def shadow_mia_attack(
    request: ShadowMIARequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        result = await ml_engine_client.run_shadow_mia(
            num_shadow_models=request.num_shadow_models,
            shadow_data_size=request.shadow_data_size,
            shadow_epochs=request.shadow_epochs,
        )
        return result
    except MLEngineClientError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/attacks/model-extraction")
async def model_extraction_attack(
    request: ModelExtractionRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        result = await ml_engine_client.run_model_extraction(
            input_dim=request.input_dim,
            num_classes=request.num_classes,
            num_queries=request.num_queries,
            extraction_epochs=request.extraction_epochs,
        )
        return result
    except MLEngineClientError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/attacks/methods")
async def list_attack_methods(
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        return await ml_engine_client.get_attack_methods()
    except MLEngineClientError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
