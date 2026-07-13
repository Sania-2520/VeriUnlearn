import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class FeatureImportance:
    feature_name: str
    importance_score: float
    direction: str = "positive"


@dataclass
class ExplanationResult:
    method: str
    feature_importances: list[FeatureImportance] = field(default_factory=list)
    shap_values: Optional[list[float]] = None
    lime_weights: Optional[list[tuple[str, float]]] = None
    ig_attributions: Optional[list[float]] = None
    base_value: float = 0.0
    prediction: float = 0.0
    confidence: float = 0.0
    runtime_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseExplainer(ABC):
    def __init__(self, model: Any, backend: str = "auto") -> None:
        self._model = model
        self._backend = backend

    @abstractmethod
    def explain(self, input_data: np.ndarray, **kwargs: Any) -> ExplanationResult:
        ...

    @abstractmethod
    def explain_batch(
        self, inputs: list[np.ndarray], **kwargs: Any
    ) -> list[ExplanationResult]:
        ...
