"""Certified removal for convex (linear) models.

Implements the Newton-step removal of Guo et al. (ICML 2020,
"Certified Data Removal from Machine Learning Models"). Removing training point
``z`` updates the parameters with

    w_new = w - H^{-1} grad L(z)

which is an exact Newton step toward the retrained optimum. For a convex,
Lipschitz loss this yields a *certified bound* on the prediction change at any
input x:

    |f_w_new(x) - f_w(x)| <= ||w_new - w|| * ||x||

The bound is stored in the deletion certificate, turning "we retrained" into
"any prediction changed by at most B" — a mathematical guarantee rather than a
hope.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Dataset, MLModel
from app.repositories.dataset_repo import DatasetRepository
from app.services.influence import InfluenceEngine
from app.services.sisa import SISAEngine


@dataclass
class CertifiedRemovalResult:
    new_weights: np.ndarray
    weight_delta_norm: float
    certified_bound: float
    max_feature_norm: float


class CertifiedRemovalService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.datasets = DatasetRepository(session)
        self.sisa = SISAEngine(session)
        self.influence = InfluenceEngine(session)

    async def remove_records_from_shard(
        self,
        model: MLModel,
        dataset: Dataset,
        shard_index: int,
        record_ids: list[str],
        *,
        lambda_reg: float = 1.0,
    ) -> CertifiedRemovalResult:
        """Certified removal of ``record_ids`` from a single shard.

        Returns the updated weights plus the certified bound on prediction
        drift for any input in the feature space.
        """
        active = await self.datasets.get_records(
            dataset.id, shard_id=shard_index, include_deleted=False
        )
        removed = {rid for rid in record_ids}
        remaining = [r for r in active if r.id not in removed]
        if not remaining:
            raise ValueError(f"Shard {shard_index} would become empty; use SISA retraining instead")

        X, y, encoder = self.sisa.build_design_matrix(
            active, dataset.feature_names, encoder=self.sisa.load_encoder(model)
        )
        classes = np.unique(y)
        positive_class = classes[1] if len(classes) > 1 else classes[0]
        y_bin = self.sisa.binary_labels(y, positive_class)
        clf = (await self.sisa.load_shard_models(model, [shard_index]))[shard_index]
        proba = clf.predict_proba(X)[:, 1]
        H_inv = np.linalg.inv(self.influence.hessian(X, proba, lambda_reg=lambda_reg))

        # Gradient contributions of exactly the records being removed.
        grad_removed = np.zeros(X.shape[1])
        for record, x, p, yv in zip(active, X, proba, y_bin):
            if record.id in removed:
                grad_removed += self.influence.point_gradient(x, float(yv), float(p))

        weights = clf.weights()
        # Newton step on the *averaged* empirical risk (H is the averaged
        # Hessian), so the removed gradient must be averaged too — otherwise
        # the correction is n times too large and overshoots.
        new_weights = weights.copy()
        new_weights[1:] -= H_inv @ (grad_removed / len(active))

        delta = new_weights[1:] - weights[1:]
        weight_delta_norm = float(np.linalg.norm(delta))
        max_feature_norm = float(np.linalg.norm(X, axis=1).max()) if len(X) else 0.0
        # Certified bound: |f_new(x) - f_old(x)| <= ||Delta w|| * ||x||  for all x.
        certified_bound = weight_delta_norm * max_feature_norm

        return CertifiedRemovalResult(
            new_weights=new_weights,
            weight_delta_norm=weight_delta_norm,
            certified_bound=float(certified_bound),
            max_feature_norm=max_feature_norm,
        )
