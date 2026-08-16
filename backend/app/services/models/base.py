"""Model abstraction layer.

Every model family that VeriUnlearn can unlearn implements
:class:`UnlearnableModel`. This keeps the SISA / influence / certified-removal
engines independent of the concrete estimator (sklearn linear, PyTorch MLP,
PEFT LoRA adapters, ...).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np


@dataclass
class ModelSpec:
    """Serializable description of a model to train/unlearn."""

    name: str
    model_type: str  # "linear" | "llm_lora"
    dataset_id: str
    feature_names: list[str] = field(default_factory=list)
    label_column: str = "income"
    shard_count: int = 4
    params: dict[str, Any] = field(default_factory=dict)

    @property
    def n_features(self) -> int:
        return len(self.feature_names)


class UnlearnableModel(Protocol):
    """Protocol implemented by all unlearnable model backends."""

    model_type: str

    def fit(self, X: np.ndarray, y: np.ndarray) -> None: ...

    def predict_proba(self, X: np.ndarray) -> np.ndarray: ...

    def predict(self, X: np.ndarray) -> np.ndarray: ...

    def weights(self) -> np.ndarray: ...

    def set_weights(self, weights: np.ndarray) -> None: ...

    def embed(self, X: np.ndarray) -> np.ndarray:
        """Feature-space representation used for vector search."""
        ...
