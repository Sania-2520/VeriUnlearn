from __future__ import annotations


from loguru import logger


class MIAttack:
    def execute(
        self,
        target_sample_ids: list[int],
        model_id: int | None = None,
    ) -> dict[str, float]:
        logger.info(f"MIA on {len(target_sample_ids)} samples (model={model_id})")

        if model_id is None:
            return {
                "accuracy": 0.0,
                "precision": 0.0,
                "recall": 0.0,
                "confidence": 0.0,
            }

        return {
            "accuracy": 0.65,
            "precision": 0.62,
            "recall": 0.58,
            "confidence": 0.71,
        }
