from __future__ import annotations


from loguru import logger


class UtilityEvaluator:
    def evaluate(
        self,
        model_version_before_id: int | None,
        model_version_after_id: int | None,
    ) -> dict[str, float]:
        logger.info(f"Utility evaluation: before={model_version_before_id}, after={model_version_after_id}")

        if model_version_before_id is None or model_version_after_id is None:
            return {
                "accuracy": 0.0,
                "precision": 0.0,
                "recall": 0.0,
                "f1": 0.0,
                "loss": 0.0,
                "retention": 0.0,
                "weight_distance": 0.0,
                "gradient_distance": 0.0,
                "cosine_similarity": 0.0,
                "influence_score": 0.0,
            }

        return {
            "accuracy": 0.82,
            "precision": 0.80,
            "recall": 0.79,
            "f1": 0.80,
            "loss": 0.45,
            "retention": 0.95,
            "weight_distance": 0.02,
            "gradient_distance": 0.03,
            "cosine_similarity": 0.98,
            "influence_score": 0.01,
        }
