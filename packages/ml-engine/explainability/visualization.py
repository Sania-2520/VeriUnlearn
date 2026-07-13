import base64
import io
import logging
from typing import Any, Optional

import numpy as np

from explainability.base import ExplanationResult

logger = logging.getLogger(__name__)


class ExplanationVisualizer:
    @staticmethod
    def importance_chart_data(
        explanation: ExplanationResult, top_k: int = 20
    ) -> dict[str, Any]:
        sorted_fi = sorted(
            explanation.feature_importances, key=lambda x: x.importance_score, reverse=True
        )[:top_k]
        return {
            "method": explanation.method,
            "labels": [fi.feature_name for fi in sorted_fi],
            "scores": [fi.importance_score for fi in sorted_fi],
            "directions": [fi.direction for fi in sorted_fi],
            "base_value": explanation.base_value,
            "prediction": explanation.prediction,
            "confidence": explanation.confidence,
        }

    @staticmethod
    def comparison_chart_data(
        pre_explanation: ExplanationResult,
        post_explanation: ExplanationResult,
        top_k: int = 15,
    ) -> dict[str, Any]:
        pre_map = {fi.feature_name: fi.importance_score for fi in pre_explanation.feature_importances}
        post_map = {fi.feature_name: fi.importance_score for fi in post_explanation.feature_importances}
        all_features = set(pre_map.keys()) | set(post_map.keys())
        shifts = [
            {
                "feature": f,
                "pre": pre_map.get(f, 0.0),
                "post": post_map.get(f, 0.0),
                "shift": post_map.get(f, 0.0) - pre_map.get(f, 0.0),
            }
            for f in all_features
        ]
        shifts.sort(key=lambda x: abs(x["shift"]), reverse=True)
        return {
            "pre_method": pre_explanation.method,
            "post_method": post_explanation.method,
            "shifts": shifts[:top_k],
            "pre_prediction": pre_explanation.prediction,
            "post_prediction": post_explanation.prediction,
            "pre_confidence": pre_explanation.confidence,
            "post_confidence": post_explanation.confidence,
            "confidence_shift": post_explanation.confidence - pre_explanation.confidence,
        }

    @staticmethod
    def privacy_risk_heatmap(
        feature_importances: list[dict[str, float]],
        privacy_scores: list[float],
        feature_names: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        n_features = len(feature_importances[0]) if feature_importances else 0
        n_samples = len(feature_importances)
        heatmap_data = np.zeros((n_samples, n_features))
        for i, row in enumerate(feature_importances):
            for j, (fname, val) in enumerate(sorted(row.items())):
                heatmap_data[i, j] = val
        return {
            "samples": n_samples,
            "features": n_features,
            "feature_names": feature_names or [f"f{i}" for i in range(n_features)],
            "heatmap_values": heatmap_data.tolist(),
            "privacy_scores": privacy_scores,
            "max_risk": float(np.max(privacy_scores)) if privacy_scores else 0.0,
            "avg_risk": float(np.mean(privacy_scores)) if privacy_scores else 0.0,
        }

    @staticmethod
    def drift_summary(
        pre_confidences: list[float],
        post_confidences: list[float],
        pre_importances: list[dict[str, float]],
        post_importances: list[dict[str, float]],
    ) -> dict[str, Any]:
        pre_conf = np.array(pre_confidences)
        post_conf = np.array(post_confidences)
        confidence_drift = float(np.mean(post_conf - pre_conf))
        volatility_pre = float(np.std(pre_conf))
        volatility_post = float(np.std(post_conf))

        importance_drift = 0.0
        for pre_row, post_row in zip(pre_importances, post_importances):
            for key in pre_row:
                importance_drift += abs(pre_row.get(key, 0.0) - post_row.get(key, 0.0))
        importance_drift = importance_drift / max(len(pre_importances), 1)

        return {
            "confidence_drift": confidence_drift,
            "volatility_pre": volatility_pre,
            "volatility_post": volatility_post,
            "volatility_change": volatility_post - volatility_pre,
            "importance_drift": importance_drift,
            "drift_detected": abs(confidence_drift) > 0.05 or importance_drift > 0.1,
            "confidence_trajectory": ["increasing" if confidence_drift > 0.01 else "decreasing" if confidence_drift < -0.01 else "stable"],
        }

    @staticmethod
    def shap_summary_plot_data(
        shap_values: list[float],
        feature_names: Optional[list[str]] = None,
        max_display: int = 20,
    ) -> dict[str, Any]:
        arr = np.array(shap_values)
        sorted_idx = np.argsort(np.abs(arr))[::-1][:max_display]
        return {
            "feature_names": [(feature_names or [f"f{i}" for i in range(len(shap_values))])[int(i)] for i in sorted_idx],
            "shap_values": [float(shap_values[int(i)]) for i in sorted_idx],
            "mean_abs_shap": float(np.mean(np.abs(arr))),
            "max_shap": float(np.max(np.abs(arr))),
        }
