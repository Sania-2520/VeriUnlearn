import time
from typing import Optional

import torch

from training.data import Dataset, accuracy_score, generate_synthetic_data
from models.single_model import SingleModel
from unlearning.algorithms.base import UnlearningAlgorithm, UnlearningContext, UnlearningResult


class InfluenceFunctionUnlearning(UnlearningAlgorithm):
    @property
    def name(self) -> str:
        return "InfluenceFunction"

    @property
    def theoretical_guarantee(self) -> str:
        return "Approximate unlearning via influence estimation. Fast but no theoretical guarantee."

    def __init__(self, damping: float = 1e-3) -> None:
        self.damping = damping
        self.model: Optional[SingleModel] = None
        self.training_data: Optional[Dataset] = None
        self._trained = False

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
                    seed=hash(context.model_name + "_inf") % (2**31),
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
            target_dataset = self.training_data.get_by_ids(target_ids)
            remaining = self.training_data.remove_by_ids(target_ids)

            if target_dataset.size > 0:
                self.model.model.train()

                remaining_features = remaining.features.to(self.model.device)
                remaining_labels = remaining.labels.to(self.model.device)

                target_grad = self._compute_avg_grad(
                    target_dataset.features, target_dataset.labels
                )

                train_outputs = self.model.model(remaining_features)
                train_losses = torch.nn.CrossEntropyLoss(reduction="none")(
                    train_outputs, remaining_labels
                )
                n = len(train_losses)
                grads = []
                for loss in train_losses:
                    self.model.model.zero_grad()
                    loss.backward(retain_graph=True)
                    grads.append(self.model.model.get_flattened_grad().clone())

                G = torch.stack(grads)
                GGN = (G.T @ G) / n
                reg_matrix = GGN + self.damping * torch.eye(
                    GGN.size(0), device=self.model.device
                )

                try:
                    inv_ggn = torch.linalg.inv(reg_matrix)
                except RuntimeError:
                    inv_ggn = torch.linalg.pinv(reg_matrix)

                param_update = inv_ggn @ target_grad
                current_params = self.model.model.flattened_params()
                updated_params = current_params - param_update / n
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
                    "target_points": target_dataset.size if hasattr(target_dataset, 'size') else 0,
                    "remaining_points": self.training_data.size,
                    "damping": self.damping,
                    "gradient_norm": target_grad.norm().item() if target_dataset.size > 0 else 0.0,
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
        if not self._trained or self.model is None:
            return False
        target_ids = set(context.target_data_ids)
        for did in target_ids:
            if self.training_data is not None:
                matching = [i for i, idd in enumerate(self.training_data.data_ids) if idd == did]
                if matching:
                    return False
        return True

    def _compute_avg_grad(
        self, features: torch.Tensor, labels: torch.Tensor
    ) -> torch.Tensor:
        self.model.model.zero_grad()
        outputs = self.model.model(features.to(self.model.device))
        loss = torch.nn.CrossEntropyLoss()(
            outputs, labels.to(self.model.device)
        )
        loss.backward()
        return self.model.model.get_flattened_grad().clone()
