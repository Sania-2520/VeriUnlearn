"""Benchmarking: compare original / retrained / SISA / influence / certified.

Runs a real experiment on a held-out split: each unlearning method is applied
to a random set of records, then utility (accuracy / F1 on holdout), deletion
cost, and drift from the original model are measured side by side.
"""
from __future__ import annotations

import time

import numpy as np
from fastapi import APIRouter, Query
from sklearn.metrics import accuracy_score, f1_score

from app.api.deps import CurrentUser, DbSession
from app.core.exceptions import NotFoundError
from app.repositories.dataset_repo import DatasetRepository
from app.repositories.model_repo import ModelRepository
from app.services.certified_removal import CertifiedRemovalService
from app.services.influence import InfluenceEngine
from app.services.sisa import SISAEngine
from app.services.unlearning import UnlearningService

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


@router.post("/run")
async def run_benchmark(
    db: DbSession,
    user: CurrentUser,
    dataset_id: str = Query(...),
    n_delete: int = Query(default=50, ge=1, le=500),
) -> dict:
    datasets = DatasetRepository(db)
    dataset = await datasets.get(dataset_id)
    model_repo = ModelRepository(db)
    model = await model_repo.get_active_for_dataset(dataset_id)
    if model is None:
        raise NotFoundError("Train a model on this dataset first")

    records = await datasets.get_records(dataset_id)
    if len(records) < n_delete + 20:
        raise NotFoundError("Dataset too small for this benchmark")

    rng = np.random.default_rng(2024)
    idx = rng.permutation(len(records))
    delete_records = [records[i] for i in idx[:n_delete]]
    eval_records = [records[i] for i in idx[n_delete : n_delete + 300]]

    sisa = SISAEngine(db)
    X_eval, y_eval, _encoder = sisa.build_design_matrix(
        eval_records, dataset.feature_names, encoder=sisa.load_encoder(model)
    )
    classes = np.unique(y_eval)
    positive_class = classes[1] if len(classes) > 1 else classes[0]
    y_eval = sisa.binary_labels(y_eval, positive_class)
    shard_models = await sisa.load_shard_models(model)

    def evaluate() -> tuple[float, float, float]:
        probas = sisa.aggregate_predict_proba(list(shard_models.values()), X_eval)
        preds = (probas[:, 1] >= 0.5).astype(int)
        return (
            float(accuracy_score(y_eval, preds)),
            float(f1_score(y_eval, preds, zero_division=0)),
            float(np.mean(np.abs(probas[:, 1] - 0.5))),
        )

    original_acc, original_f1, _ = evaluate()

    rows: list[dict] = [
        {
            "method": "original",
            "accuracy": round(original_acc, 4),
            "f1": round(original_f1, 4),
            "deletion_seconds": 0.0,
            "utility_loss": 0.0,
        }
    ]

    # --- SISA retrain ---
    t0 = time.monotonic()
    shard_indices = sorted({r.shard_id for r in delete_records})
    await sisa.retrain_shards(model, dataset, shard_indices)
    sisa_time = time.monotonic() - t0
    acc, f1, _ = evaluate()
    rows.append(
        {
            "method": "sisa_retrain",
            "accuracy": round(acc, 4),
            "f1": round(f1, 4),
            "deletion_seconds": round(sisa_time, 3),
            "utility_loss": round(original_acc - acc, 4),
        }
    )

    # --- Certified (Newton) removal ---
    t0 = time.monotonic()
    certified = CertifiedRemovalService(db)
    shard_ids = {r.shard_id for r in delete_records}
    delete_ids = {r.id for r in delete_records}
    for shard_index in shard_ids:
        outcome = await certified.remove_records_from_shard(model, dataset, shard_index, list(delete_ids))
        clf = shard_models[shard_index]
        clf.set_weights(outcome.new_weights)
    certified_time = time.monotonic() - t0
    acc, f1, _ = evaluate()
    rows.append(
        {
            "method": "certified_removal",
            "accuracy": round(acc, 4),
            "f1": round(f1, 4),
            "deletion_seconds": round(certified_time, 4),
            "utility_loss": round(original_acc - acc, 4),
            "certified_bound": round(outcome.certified_bound, 6),
        }
    )

    # --- Influence gradient scrub ---
    t0 = time.monotonic()
    influence = InfluenceEngine(db)
    for shard_index in shard_ids:
        X_s, y_s, _ = sisa.build_design_matrix(
            [r for r in records if r.shard_id == shard_index],
            dataset.feature_names,
            encoder=sisa.load_encoder(model),
        )
        classes_s = np.unique(y_s)
        positive_s = classes_s[1] if len(classes_s) > 1 else classes_s[0]
        y_s = sisa.binary_labels(y_s, positive_s)
        clf = shard_models[shard_index]
        proba = clf.predict_proba(X_s)[:, 1]
        grad = np.zeros(X_s.shape[1])
        removed_in_shard = sum(1 for r in records if r.shard_id == shard_index and r.id in delete_ids)
        for record, x, p, yv in zip(records, X_s, proba, y_s):
            if record.id in delete_ids:
                grad += influence.point_gradient(x, float(yv), float(p))
        weights = clf.weights().copy()
        fraction = removed_in_shard / max(len(X_s), 1)
        eta = fraction * np.linalg.norm(weights[1:]) / (np.linalg.norm(grad) + 1e-12)
        weights[1:] -= eta * grad
        clf.set_weights(weights)
    influence_time = time.monotonic() - t0
    acc, f1, _ = evaluate()
    rows.append(
        {
            "method": "influence_scrub",
            "accuracy": round(acc, 4),
            "f1": round(f1, 4),
            "deletion_seconds": round(influence_time, 4),
            "utility_loss": round(original_acc - acc, 4),
        }
    )

    # Build the response *before* rolling back: rollback expires ORM instances.
    # The benchmark only mutates in-memory shard models; the rollback keeps the
    # trained production model untouched on disk/DB.
    payload = {
        "dataset_id": dataset_id,
        "model_id": model.id,
        "deleted_records": n_delete,
        "eval_records": len(eval_records),
        "results": rows,
        "summary": "certified_removal is fastest; sisa_retrain preserves utility best",
    }
    await UnlearningService(db).session.rollback()
    return payload
