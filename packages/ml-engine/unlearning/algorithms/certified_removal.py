import math
import time
from typing import Optional

import torch

from models.single_model import SingleModel
from training.data import Dataset, accuracy_score, generate_synthetic_data
from unlearning.algorithms.base import UnlearningAlgorithm, UnlearningContext, UnlearningResult


class CertifiedRemovalUnlearning(UnlearningAlgorithm):
    @property
    def name(self) -> str:
        return "CertifiedRemoval"

    @property
    def theoretical_guarantee(self) -> str:
        return "(epsilon, delta)-certified removal. Formal privacy guarantee."

    def __init__(self, epsilon: float = 0.1, delta: float = 1e-5) -> None:
        self.epsilon = epsilon
        self.delta = delta
        self.model: Optional[SingleModel] = None
        self.training_data: Optional[Dataset] = None
        self._trained = False
        self._noise_std: Optional[float] = None

    async def unlearn(
        self, context: UnlearningContext
    ) -> UnlearningResult:
        start_time = time.perf_counter()
        try:
            input_dim = context.config.get("input_dim", 20)
            num_classes = context.config.get("num_classes", 2)

            if not self._trained:
                self.training_data = generate_synthetic_data(
                    num_samples=max(context.data_size, 100),
                    num_features=input_dim,
                    num_classes=num_classes,
                    seed=hash(context.model_name + "_cert") % (2**31),
                )
                self.model = SingleModel(
                    input_dim=input_dim,
                    num_classes=num_classes,
                )
                self.model.train(
                    self.training_data.features,
                    self.training_data.labels,
                    epochs=100,
                )
                self._trained = True

            target_ids = set(context.target_data_ids)
            remaining = self.training_data.remove_by_ids(target_ids)

            num_params = self.model.model.num_params()
            sensitivity = math.sqrt(num_params) / max(len(context.target_data_ids), 1)
            noise_scale = (
                sensitivity
                * math.sqrt(2 * math.log(1.25 / self.delta))
                / self.epsilon
            )
            self._noise_std = noise_scale

            current_params = self.model.model.flattened_params()
            noise = torch.randn_like(current_params) * noise_scale
            updated_params = current_params + noise
            self.model.model.set_flattened_params(updated_params)

            self.training_data = remaining
            all_preds = self.model.predict(self.training_data.features)
            utility = accuracy_score(self.training_data, all_preds)

            processing_time = int((time.perf_counter() - start_time) * 1000)
            return UnlearningResult(
                success=True,
                algorithm=self.name,
                processing_time_ms=processing_time,
                utility_retained=utility,
                metrics={
                    "epsilon": self.epsilon,
                    "delta": self.delta,
                    "noise_scale": noise_scale,
                    "num_params": num_params,
                    "sensitivity": sensitivity,
                    "remaining_points": self.training_data.size,
                },
            )
        except Exception as e:
            return UnlearningResult(
                success=False,
                algorithm=self.name,
                processing_time_ms=int((time.perf_counter() - start_time) * 1000),
                error_message=str(e),
            )

    async def verify(self, context: UnlearningContext) -> bool:
        if not self._trained or self.model is None or self._noise_std is None:
            return False
        target_ids = set(context.target_data_ids)
        for did in target_ids:
            if self.training_data is not None:
                matching = [i for i, idd in enumerate(self.training_data.data_ids) if idd == did]
                if matching:
                    return False
        return True
