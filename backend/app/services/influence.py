"""Influence function engine.

For a logistic-regression shard model with parameters ``w`` and empirical risk
``L``, the influence of training point ``z`` on the parameters is

    I(z) = -H^{-1} grad L(z)          (H = Hessian of the empirical risk)

and its influence on the loss at a test point ``z_test`` is

    I_loss(z, z_test) = grad L(z_test) . I(z).

These quantities power the identity footprint ("influence score" per record),
prioritised deletion, and the Newton-step certified removal in
``services/certified_removal.py``.

Implementation notes: for a linear model the Hessian is ``X^T D X + lambda I``
(D diagonal with p_i(1-p_i)), which is exact and cheap to invert at this scale.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Dataset, DatasetRecord, MLModel
from app.repositories.dataset_repo import DatasetRepository
from app.services.sisa import SISAEngine


@dataclass
class InfluenceResult:
    record_id: str
    self_influence: float
    parameter_norm: float
    loss_gradient_norm: float


class InfluenceEngine:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.datasets = DatasetRepository(session)
        self.sisa = SISAEngine(session)

    # ------------------------------------------------------------------ math

    @staticmethod
    def hessian(X: np.ndarray, proba: np.ndarray, lambda_reg: float = 1.0) -> np.ndarray:
        """Exact Hessian of L2-regularised logistic loss.

        ``lambda_reg`` must match the model's actual L2 strength (1/C for
        scikit-learn's LogisticRegression). Using a near-zero value makes the
        Hessian ill-conditioned on one-hot encoded features, which destabilises
        the Newton removal step.
        """
        d = X.shape[1]
        D = proba * (1 - proba)
        H = (X.T * D) @ X / len(proba)
        H += lambda_reg * np.eye(d)
        return H

    @staticmethod
    def loss_gradient(X: np.ndarray, y: np.ndarray, proba: np.ndarray) -> np.ndarray:
        """Gradient of the empirical logistic loss w.r.t. parameters."""
        resid = proba - y
        return (X.T @ resid) / len(y)

    @staticmethod
    def point_gradient(x: np.ndarray, y: float, proba: float) -> np.ndarray:
        return x * (proba - y)

    def compute_influences(
        self,
        X: np.ndarray,
        y: np.ndarray,
        proba: np.ndarray,
        *,
        lambda_reg: float = 1e-3,
    ) -> np.ndarray:
        """Self-influence (influence of each point on the model parameters)."""
        H = self.hessian(X, proba, lambda_reg=lambda_reg)
        H_inv = np.linalg.inv(H)
        influences = np.zeros(len(y))
        for i in range(len(y)):
            g = self.point_gradient(X[i], float(y[i]), float(proba[i]))
            influences[i] = float(-g @ H_inv @ g)
        return influences

    # ------------------------------------------------------------------ service

    async def score_shard(
        self, model: MLModel, dataset: Dataset, shard_index: int
    ) -> dict[str, float]:
        """Compute influence score for every active record in a shard."""
        records = await self.datasets.get_records(
            dataset.id, shard_id=shard_index, include_deleted=False
        )
        if not records:
            return {}
        X, y, encoder = self.sisa.build_design_matrix(
            records, dataset.feature_names, encoder=self.sisa.load_encoder(model)
        )
        classes = np.unique(y)
        positive_class = classes[1] if len(classes) > 1 else classes[0]
        y_bin = self.sisa.binary_labels(y, positive_class)
        clf = (await self.sisa.load_shard_models(model, [shard_index]))[shard_index]
        proba = clf.predict_proba(X)[:, 1]
        influences = self.compute_influences(X, y_bin, proba)
        return {records[i].id: float(influences[i]) for i in range(len(records))}

    async def update_all_scores(self, model: MLModel, dataset: Dataset) -> int:
        """Background job: persist influence scores for all shards."""
        shard_indices = sorted({r.shard_id for r in await self.datasets.get_records(dataset.id)})
        updated = 0
        for shard_index in shard_indices:
            scores = await self.score_shard(model, dataset, shard_index)
            for record_id, score in scores.items():
                record = await self.datasets.get_record(record_id)
                record.influence_score = score
                updated += 1
        await self.session.flush()
        return updated
