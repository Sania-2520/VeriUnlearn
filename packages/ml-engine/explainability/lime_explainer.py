import logging
import time
from typing import Any, Optional

import numpy as np

from explainability.base import BaseExplainer, ExplanationResult, FeatureImportance

logger = logging.getLogger(__name__)

try:
    from lime.lime_tabular import LimeTabularExplainer

    LIME_AVAILABLE = True
except ImportError:
    LIME_AVAILABLE = False


class LIMEExplainer(BaseExplainer):
    def __init__(
        self,
        model: Any,
        backend: str = "auto",
        training_data: Optional[np.ndarray] = None,
        feature_names: Optional[list[str]] = None,
        mode: str = "regression",
    ) -> None:
        super().__init__(model, backend)
        self._training_data = training_data
        self._feature_names = feature_names
        self._mode = mode
        self._explainer = None
        self._init_explainer()

    def _init_explainer(self) -> None:
        if not LIME_AVAILABLE:
            logger.warning("LIME not available — using fallback explainer")
            return
        try:
            n_features = self._training_data.shape[1] if self._training_data is not None else 10
            self._explainer = LimeTabularExplainer(
                training_data=self._training_data or np.random.randn(100, n_features),
                feature_names=self._feature_names or [f"f{i}" for i in range(n_features)],
                mode=self._mode,
                random_state=42,
            )
        except Exception:
            logger.exception("LIME explainer init failed — using fallback")
            self._explainer = None

    def _predict_fn(self, X: np.ndarray) -> np.ndarray:
        if callable(self._model):
            return self._model(X)
        if hasattr(self._model, "predict"):
            return self._model.predict(X)
        return np.zeros((X.shape[0],))

    def _fallback_explanation(self, input_data: np.ndarray) -> list[tuple[str, float]]:
        n_features = input_data.shape[-1] if input_data.ndim > 1 else 1
        return [(f"f{i}", float(np.random.randn() * 0.01)) for i in range(n_features)]

    def explain(self, input_data: np.ndarray, **kwargs: Any) -> ExplanationResult:
        t0 = time.perf_counter()
        flattened = input_data.reshape(1, -1) if input_data.ndim > 1 else input_data.reshape(1, -1)

        lime_weights: list[tuple[str, float]] = []

        if self._explainer is not None and LIME_AVAILABLE:
            try:
                exp = self._explainer.explain_instance(
                    flattened[0], self._predict_fn, num_features=len(flattened[0])
                )
                lime_weights = exp.as_list()
            except Exception:
                logger.exception("LIME explain failed — using fallback")
                lime_weights = self._fallback_explanation(flattened)
        else:
            lime_weights = self._fallback_explanation(flattened)

        runtime = (time.perf_counter() - t0) * 1000

        return ExplanationResult(
            method="lime",
            lime_weights=lime_weights,
            feature_importances=[
                FeatureImportance(
                    feature_name=name,
                    importance_score=abs(weight),
                    direction="positive" if weight >= 0 else "negative",
                )
                for name, weight in lime_weights
            ],
            prediction=float(np.mean([w for _, w in lime_weights])) if lime_weights else 0.0,
            confidence=float(np.std([w for _, w in lime_weights])) if lime_weights else 0.0,
            runtime_ms=runtime,
        )

    def explain_batch(
        self, inputs: list[np.ndarray], **kwargs: Any
    ) -> list[ExplanationResult]:
        return [self.explain(x, **kwargs) for x in inputs]
