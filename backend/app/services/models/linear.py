"""Logistic-regression implementation of :class:`UnlearnableModel`.

Linear models are the workhorse of the runnable vertical slice:

- exact influence functions via the Hessian (see ``services/influence.py``);
- certified removal with a provable bound on prediction drift (Guo et al.,
  "Certified Data Removal from Machine Learning Models", ICML 2020);
- cheap SISA retraining per shard.
"""
from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression

from app.services.models.base import UnlearnableModel


class SklearnLinearModel:
    model_type = "linear"

    def __init__(
        self,
        *,
        feature_names: list[str] | None = None,
        C: float = 1.0,
        max_iter: int = 1000,
        random_state: int = 42,
    ) -> None:
        self.feature_names = feature_names or []
        # liblinear avoids the scipy optimize (iprint) warning and is fast at
        # this scale; its coefficients are what influence/certified removal use.
        self._clf = LogisticRegression(
            C=C, max_iter=max_iter, random_state=random_state, solver="liblinear"
        )

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self._clf.fit(X, y)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self._clf.predict_proba(X)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self._clf.predict(X)

    def weights(self) -> np.ndarray:
        """Concatenated ``[intercept, coef]`` vector (d+1 parameters)."""
        return np.concatenate([self._clf.intercept_, self._clf.coef_.ravel()])

    def set_weights(self, weights: np.ndarray) -> None:
        d = len(weights) - 1
        if not hasattr(self._clf, "coef_"):
            # Initialise the estimator structure without meaningful training:
            # a 2-sample dummy fit sets n_features_in_ and classes_.
            self._clf.fit(np.zeros((2, d)), np.array([0, 1]))
        self._clf.intercept_ = np.asarray([weights[0]])
        self._clf.coef_ = np.asarray(weights[1 : 1 + d]).reshape(1, d)

    def embed(self, X: np.ndarray) -> np.ndarray:
        """Feature-space embedding: standardised input scaled by L2 norm."""
        X = np.asarray(X, dtype=float)
        norms = np.linalg.norm(X, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return X / norms

    @staticmethod
    def to_binary_labels(y: np.ndarray) -> np.ndarray:
        """Map labels to {0,1}; first class becomes 0, anything else 1."""
        unique = np.unique(y)
        if len(unique) == 2:
            return (y == unique[1]).astype(int)
        return (np.asarray(y) != unique[0]).astype(int)
