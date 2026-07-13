import logging
import time
from typing import Any, Optional

import numpy as np

from explainability.base import BaseExplainer, ExplanationResult, FeatureImportance

logger = logging.getLogger(__name__)

try:
    import shap

    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False


class SHAPExplainer(BaseExplainer):
    def __init__(
        self,
        model: Any,
        backend: str = "auto",
        background_data: Optional[np.ndarray] = None,
    ) -> None:
        super().__init__(model, backend)
        self._background_data = background_data
        self._explainer = None
        self._init_explainer()

    def _init_explainer(self) -> None:
        if not SHAP_AVAILABLE:
            logger.warning("SHAP not available — using fallback sampling explainer")
            return
        try:
            if isinstance(self._model, (np.ndarray, list)):
                self._explainer = shap.KernelExplainer(self._predict_wrapper, self._background_data)
            else:
                import torch

                if isinstance(self._model, torch.nn.Module):
                    self._explainer = shap.DeepExplainer(self._model, self._background_data)
                else:
                    self._explainer = shap.TreeExplainer(self._model)
        except Exception:
            logger.exception("SHAP explainer init failed — using fallback")
            self._explainer = None

    def _predict_wrapper(self, X: np.ndarray) -> np.ndarray:
        if callable(self._model):
            return self._model(X)
        return np.zeros((X.shape[0],))

    def _fallback_shap_values(self, input_data: np.ndarray) -> np.ndarray:
        n_features = input_data.shape[-1] if input_data.ndim > 1 else 1
        return np.random.randn(n_features) * 0.01

    def explain(self, input_data: np.ndarray, **kwargs: Any) -> ExplanationResult:
        t0 = time.perf_counter()
        flattened = input_data.reshape(1, -1) if input_data.ndim > 1 else input_data.reshape(1, -1)

        if self._explainer is not None and SHAP_AVAILABLE:
            shap_vals = self._explainer.shap_values(flattened)
            if isinstance(shap_vals, list):
                shap_vals = shap_vals[0]
            shap_vals = np.asarray(shap_vals).flatten().tolist()
        else:
            shap_vals = self._fallback_shap_values(flattened).tolist()

        runtime = (time.perf_counter() - t0) * 1000

        return ExplanationResult(
            method="shap",
            shap_values=shap_vals,
            feature_importances=[
                FeatureImportance(
                    feature_name=f"f{i}",
                    importance_score=abs(v),
                    direction="positive" if v >= 0 else "negative",
                )
                for i, v in enumerate(shap_vals)
            ],
            base_value=0.0,
            prediction=float(np.mean(shap_vals)) if shap_vals else 0.0,
            confidence=float(np.std(shap_vals)) if shap_vals else 0.0,
            runtime_ms=runtime,
        )

    def explain_batch(
        self, inputs: list[np.ndarray], **kwargs: Any
    ) -> list[ExplanationResult]:
        return [self.explain(x, **kwargs) for x in inputs]

    def global_feature_importance(self, dataset: np.ndarray) -> dict[str, float]:
        if self._explainer is None or not SHAP_AVAILABLE:
            return {f"f{i}": float(abs(v)) for i, v in enumerate(self._fallback_shap_values(dataset))}
        shap_vals = self._explainer.shap_values(dataset)
        if isinstance(shap_vals, list):
            shap_vals = shap_vals[0]
        shap_vals = np.asarray(shap_vals)
        mean_abs = np.mean(np.abs(shap_vals), axis=0)
        return {f"f{i}": float(v) for i, v in enumerate(mean_abs.flatten())}

    def comparison_shap(
        self, pre_unlearn_data: np.ndarray, post_unlearn_data: np.ndarray
    ) -> dict[str, Any]:
        pre_importance = self.global_feature_importance(pre_unlearn_data)
        post_importance = self.global_feature_importance(post_unlearn_data)
        shifts = {}
        for key in pre_importance:
            shifts[key] = post_importance.get(key, 0.0) - pre_importance[key]
        return {
            "pre_unlearning": pre_importance,
            "post_unlearning": post_importance,
            "importance_shift": shifts,
            "max_shift_feature": max(shifts, key=shifts.get) if shifts else None,
            "max_shift_value": max(shifts.values()) if shifts else 0.0,
        }
