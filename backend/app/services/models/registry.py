"""Model factory: maps ``model_type`` strings to concrete implementations."""
from __future__ import annotations

from app.core.config import settings
from app.services.models.base import ModelSpec, UnlearnableModel
from app.services.models.linear import SklearnLinearModel


def build_model(spec: ModelSpec) -> UnlearnableModel:
    if spec.model_type == "linear":
        return SklearnLinearModel(
            feature_names=spec.feature_names,
            C=float(spec.params.get("C", 1.0)),
            random_state=int(spec.params.get("random_state", settings.IDENTITY_SYNTHESIS_SEED)),
        )
    if spec.model_type == "llm_lora":
        from app.services.models.llm_lora import LoRAUnlearnableModel

        return LoRAUnlearnableModel(
            base_model_name=spec.params.get("base_model", "TinyLlama/TinyLlama-1.1B-Chat-v1.0"),
            adapter_name=spec.params.get("adapter_name"),
        )
    raise ValueError(f"Unknown model_type: {spec.model_type}")
