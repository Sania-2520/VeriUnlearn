from __future__ import annotations

import time

from fastapi import APIRouter
import numpy as np
import pandas as pd

from app.api.deps import CurrentUser, DbSession
from app.api.serializers import model_out
from app.core.exceptions import NotFoundError, ValidationFailedError
from app.db.models import MLModel
from app.repositories.dataset_repo import DatasetRepository
from app.repositories.model_repo import ModelRepository
from app.schemas.model import ModelOut, PredictRequest, PredictResponse
from app.services.audit import AuditService
from app.services.influence import InfluenceEngine
from app.services.sisa import SISAEngine

router = APIRouter(prefix="/models", tags=["models"])


@router.post("/train", response_model=ModelOut, status_code=201)
async def train_model(dataset_id: str, db: DbSession, user: CurrentUser) -> ModelOut:
    datasets = DatasetRepository(db)
    dataset = await datasets.get(dataset_id)
    if dataset.record_count == 0:
        raise ValidationFailedError("Dataset has no records")

    model = MLModel(
        name=f"{dataset.name}-v1",
        model_type="linear",
        dataset_id=dataset_id,
        shard_count=dataset.shard_count,
    )
    model = await ModelRepository(db).add(model)
    await AuditService(db).log(
        event_type="model.training.started",
        actor=user["sub"],
        subject=model.id,
        payload={"dataset_id": dataset_id, "shards": dataset.shard_count},
    )
    await SISAEngine(db).train_model(model, dataset)

    # Influence scoring runs in the same request for the demo slice (fast at this scale).
    try:
        updated = await InfluenceEngine(db).update_all_scores(model, dataset)
    except Exception:
        updated = 0
    await AuditService(db).log(
        event_type="model.training.completed",
        actor=user["sub"],
        subject=model.id,
        payload={"metrics": model.metrics, "influence_scores": updated},
    )
    return ModelOut(**model_out(model))


@router.get("", response_model=list[ModelOut])
async def list_models(db: DbSession) -> list[ModelOut]:
    models = await ModelRepository(db).list(limit=100)
    return [ModelOut(**model_out(m)) for m in models]


@router.get("/{model_id}", response_model=ModelOut)
async def get_model(model_id: str, db: DbSession) -> ModelOut:
    model = await ModelRepository(db).get(model_id)
    return ModelOut(**model_out(model))


@router.get("/{model_id}/shards")
async def get_shards(model_id: str, db: DbSession) -> dict:
    shards = await ModelRepository(db).get_shards(model_id)
    return {
        "model_id": model_id,
        "shards": [
            {
                "id": s.id,
                "shard_index": s.shard_index,
                "status": s.status,
                "weights_hash": s.weights_hash,
                "accuracy": s.accuracy,
                "train_loss": s.train_loss,
                "retrained_at": s.retrained_at.isoformat() if s.retrained_at else None,
                "record_version": s.record_version,
                "trained_on": s.trained_on,
            }
            for s in shards
        ],
    }


@router.post("/{model_id}/predict", response_model=PredictResponse)
async def predict(model_id: str, payload: PredictRequest, db: DbSession) -> PredictResponse:
    repo = ModelRepository(db)
    model = await repo.get(model_id)
    if model.status != "ready":
        raise ValidationFailedError(f"Model not ready (status={model.status})")
    dataset = await DatasetRepository(db).get(model.dataset_id)

    missing = [c for c in dataset.feature_names if c not in payload.features]
    if missing:
        raise ValidationFailedError(f"Missing features: {missing}")

    # Build a single-row design matrix through the persisted encoder.
    sisa = SISAEngine(db)
    encoder_path = sisa.model_dir(model) / "encoder.joblib"
    import joblib

    encoder = joblib.load(encoder_path)
    row = pd.DataFrame([{c: payload.features[c] for c in dataset.feature_names}])
    X = encoder.transform(row)
    X = X.toarray() if hasattr(X, "toarray") else np.asarray(X)

    shard_models = await sisa.load_shard_models(model)
    proba = sisa.aggregate_predict_proba(list(shard_models.values()), X)[0]
    positive_class = model.metrics.get("positive_class")
    proba_positive = float(proba[1])
    prediction = 1 if proba_positive >= 0.5 else 0
    return PredictResponse(
        model_id=model.id,
        model_version=model.version,
        prediction=positive_class if positive_class is not None and prediction == 1 else prediction,
        probability=proba_positive,
        shard_count=len(shard_models),
    )


@router.delete("/{model_id}")
async def delete_model(model_id: str, db: DbSession, user: CurrentUser) -> dict:
    repo = ModelRepository(db)
    model = await repo.get(model_id)
    # Populate children explicitly (async-safe) so the cascade delete works.
    model.shards = await repo.get_shards(model_id)
    await repo.delete(model)
    await AuditService(db).log(event_type="model.deleted", actor=user["sub"], subject=model_id)
    return {"message": f"Model {model_id} deleted"}
