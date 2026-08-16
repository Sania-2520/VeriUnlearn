"""SISA (Sharded, Isolated, Sliced, Aggregated) training engine.

The dataset is split into K independent shards; each shard trains its own
model. Deleting records only requires retraining the affected shard(s) —
other shards are untouched, giving near-constant deletion cost.

Aggregation: soft voting (mean of shard class probabilities). Each shard's
weights are persisted separately so a shard can be re-trained and re-hashed in
isolation, and so shard-level unlearning can be verified per shard.

The feature encoder is fitted once per model over the full dataset so that
retraining a shard does not shift the feature space of other shards (standard
SISA practice; documented in the architecture doc).
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Dataset, DatasetRecord, MLModel, ModelShard
from app.repositories.dataset_repo import DatasetRepository
from app.repositories.model_repo import ModelRepository
from app.services.crypto import canonical_json, sha256_hex
from app.services.models.base import ModelSpec
from app.services.models.linear import SklearnLinearModel
from app.services.models.registry import build_model

logger = logging.getLogger("veriunlearn.sisa")

_ENC_FILENAME = "encoder.joblib"


class SISAEngine:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.datasets = DatasetRepository(session)
        self.models_repo = ModelRepository(session)

    # ------------------------------------------------------------------ data prep

    @staticmethod
    def build_design_matrix(
        records: list[DatasetRecord],
        feature_names: list[str],
        *,
        encoder: ColumnTransformer | None = None,
    ) -> tuple[np.ndarray, np.ndarray, ColumnTransformer]:
        """One-hot encode categorical features; fit encoder on first call."""
        df = pd.DataFrame([r.features for r in records])[feature_names]
        categorical = [c for c in feature_names if df[c].dtype == object]
        numeric = [c for c in feature_names if c not in categorical]
        transformers: list[tuple[str, Any, list[str]]] = []
        if numeric:
            transformers.append(("num", "passthrough", numeric))
        if categorical:
            transformers.append(("cat", OneHotEncoder(handle_unknown="ignore"), categorical))
        if not transformers:
            raise ValueError("Dataset has no usable feature columns")

        if encoder is None:
            encoder = ColumnTransformer(transformers=transformers, sparse_threshold=0.5)
            encoder.fit(df)
        X = encoder.transform(df).toarray() if hasattr(encoder.transform(df), "toarray") else np.asarray(encoder.transform(df))
        y = np.asarray([r.label for r in records])
        return X, y, encoder

    @staticmethod
    def binary_labels(y: np.ndarray, positive_class: Any) -> np.ndarray:
        """Map labels to {0,1} relative to the model's positive class."""
        return (y == positive_class).astype(int)

    @staticmethod
    def serialize_weights(weights: np.ndarray) -> str:
        return sha256_hex(canonical_json({"w": weights.tolist()}))

    # ------------------------------------------------------------------ training

    def model_dir(self, model: MLModel) -> Path:
        path = Path(settings.MODEL_DIR) / model.id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def load_encoder(self, model: MLModel) -> ColumnTransformer | None:
        """Load the model-level feature encoder (fitted on the full dataset).

        Every scoring path must use this encoder so the feature space matches
        what the shard models were trained on.
        """
        path = self.model_dir(model) / _ENC_FILENAME
        return joblib.load(path) if path.exists() else None

    async def train_model(
        self,
        model: MLModel,
        dataset: Dataset,
        *,
        actor: str = "system",
    ) -> MLModel:
        """Train all shards of ``model`` over ``dataset`` (SISA)."""
        model.status = "training"
        await self.session.flush()
        start = time.monotonic()

        records = await self.datasets.get_records(dataset.id, include_deleted=False)
        if not records:
            raise ValueError("Dataset has no active records to train on")

        X_all, y_all, encoder = self.build_design_matrix(records, dataset.feature_names)
        classes = np.unique(np.asarray([r.label for r in records]))
        positive_class = classes[1] if len(classes) > 1 else classes[0]
        y_bin = self.binary_labels(y_all, positive_class)

        encoder_path = self.model_dir(model) / _ENC_FILENAME
        joblib.dump(encoder, encoder_path)

        shard_indices = sorted({r.shard_id for r in records})
        shard_models: dict[int, SklearnLinearModel] = {}
        holdout_concat_X: list[np.ndarray] = []
        holdout_concat_y: list[np.ndarray] = []
        shards: list[ModelShard] = []

        for shard_index in shard_indices:
            shard_records = [r for r in records if r.shard_id == shard_index]
            indices = [records.index(r) for r in shard_records]
            X_s = X_all[np.array(indices)]
            y_s = y_bin[np.array(indices)]
            if len(np.unique(y_s)) < 2:
                raise ValueError(f"Shard {shard_index} has a single class; reduce shard count")
            X_tr, X_te, y_tr, y_te = train_test_split(
                X_s, y_s, test_size=0.2, random_state=settings.IDENTITY_SYNTHESIS_SEED
            )
            holdout_concat_X.append(X_te)
            holdout_concat_y.append(y_te)

            clf = SklearnLinearModel(feature_names=dataset.feature_names)
            clf.fit(X_tr, y_tr)
            shard_models[shard_index] = clf

            accuracy = float(accuracy_score(y_te, clf.predict(X_te)))
            loss = float(self._log_loss(X_tr, y_tr, clf))
            shard = ModelShard(
                model_id=model.id,
                shard_index=shard_index,
                weights_path=str(self.model_dir(model) / f"shard_{shard_index}.npz"),
                weights_hash=self.serialize_weights(clf.weights()),
                status="ready",
                accuracy=accuracy,
                train_loss=loss,
                retrained_at=datetime.now(timezone.utc),
                trained_on=len(shard_records),
            )
            shards.append(shard)
            self.session.add(shard)
            np.savez(shard.weights_path, weights=clf.weights())

        # Model-level metrics on the pooled holdout (soft voting).
        X_holdout = np.vstack(holdout_concat_X)
        y_holdout = np.concatenate(holdout_concat_y)
        probas = np.mean(
            np.stack([clf.predict_proba(X_holdout) for clf in shard_models.values()]), axis=0
        )
        preds = (probas[:, 1] >= 0.5).astype(int)
        model.metrics = {
            "accuracy": float(accuracy_score(y_holdout, preds)),
            "precision": float(precision_score(y_holdout, preds, zero_division=0)),
            "recall": float(recall_score(y_holdout, preds, zero_division=0)),
            "f1": float(f1_score(y_holdout, preds, zero_division=0)),
            "train_records": len(records),
            "positive_class": str(positive_class),
            "feature_names": dataset.feature_names,
            "training_seconds": round(time.monotonic() - start, 3),
        }
        model.weights_hash = sha256_hex(
            canonical_json(
                {f"shard_{sh.shard_index}": sh.weights_hash for sh in sorted(shards, key=lambda s: s.shard_index)}
            )
        )
        model.status = "ready"
        await self.session.flush()
        logger.info("Trained SISA model %s (%s)", model.id, model.metrics)
        return model

    @staticmethod
    def _log_loss(X: np.ndarray, y: np.ndarray, clf: SklearnLinearModel) -> float:
        p = clf.predict_proba(X)[:, 1]
        p = np.clip(p, 1e-12, 1 - 1e-12)
        return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))

    # ------------------------------------------------------------------ aggregation

    @staticmethod
    def aggregate_predict_proba(shard_models: list[SklearnLinearModel], X: np.ndarray) -> np.ndarray:
        """Soft voting: mean class probabilities across shards."""
        return np.mean(np.stack([m.predict_proba(X) for m in shard_models]), axis=0)

    # ------------------------------------------------------------------ retraining

    async def retrain_shards(
        self,
        model: MLModel,
        dataset: Dataset,
        shard_indices: list[int],
        *,
        actor: str = "system",
    ) -> dict[str, Any]:
        """SISA selective retraining: only the affected shards are re-trained."""
        start = time.monotonic()
        encoder = self.load_encoder(model)

        retrained: list[int] = []
        for shard_index in shard_indices:
            shard = await self.models_repo.get_shard(model.id, shard_index)
            shard.status = "training"
            await self.session.flush()

            records = await self.datasets.get_records(
                dataset.id, shard_id=shard_index, include_deleted=False
            )
            if not records:
                # Shard fully deleted: represent it as an empty model (all-zeros weights).
                weights = np.zeros(1 + len(dataset.feature_names))
                clf = SklearnLinearModel(feature_names=dataset.feature_names)
                clf.set_weights(weights)
            else:
                X, y, _ = self.build_design_matrix(records, dataset.feature_names, encoder=encoder)
                classes = np.unique(np.asarray([r.label for r in records]))
                positive_class = classes[1] if len(classes) > 1 else classes[0]
                y_bin = self.binary_labels(y, positive_class)
                if len(np.unique(y_bin)) < 2:
                    raise ValueError(f"Shard {shard_index} has a single class; cannot retrain")
                model.metrics["positive_class"] = str(positive_class)
                clf = SklearnLinearModel(feature_names=dataset.feature_names)
                clf.fit(X, y_bin)

            shard.weights_hash = self.serialize_weights(clf.weights())
            np.savez(shard.weights_path, weights=clf.weights())
            shard.status = "ready"
            shard.accuracy = None
            shard.retrained_at = datetime.now(timezone.utc)
            shard.record_version += 1
            shard.trained_on = len(records)
            retrained.append(shard_index)

        all_shards = await self.models_repo.get_shards(model.id)
        model.weights_hash = sha256_hex(
            canonical_json(
                {f"shard_{sh.shard_index}": sh.weights_hash for sh in all_shards}
            )
        )
        await self.session.flush()
        return {
            "retrained_shards": retrained,
            "duration_seconds": round(time.monotonic() - start, 3),
            "model_weights_hash": model.weights_hash,
        }

    async def load_shard_models(
        self, model: MLModel, shard_indices: list[int] | None = None
    ) -> dict[int, SklearnLinearModel]:
        """Load persisted shard weights into in-memory models (for inference/attacks)."""
        result: dict[int, SklearnLinearModel] = {}
        shards = await self.models_repo.get_shards(model.id)
        for shard in shards:
            if shard_indices is not None and shard.shard_index not in shard_indices:
                continue
            clf = SklearnLinearModel(feature_names=model.metrics.get("feature_names", []))
            data = np.load(shard.weights_path, allow_pickle=True)
            clf.set_weights(data["weights"])
            result[shard.shard_index] = clf
        return result
