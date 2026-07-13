import logging
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class ElasticWeightConsolidation:
    def __init__(
        self,
        model: Any,
        ewc_lambda: float = 0.4,
        online: bool = True,
        gamma: float = 0.9,
    ) -> None:
        self._model = model
        self._ewc_lambda = ewc_lambda
        self._online = online
        self._gamma = gamma
        self._fisher_matrices: list[list[torch.Tensor]] = []
        self._optimal_params: list[torch.Tensor] = []
        self._params: list[torch.Tensor] = []

        if TORCH_AVAILABLE and isinstance(model, torch.nn.Module):
            self._params = [p.detach().clone() for p in model.parameters() if p.requires_grad]

    def estimate_fisher(self, dataset: Any, num_samples: int = 200, batch_size: int = 10) -> None:
        if not TORCH_AVAILABLE or not isinstance(self._model, torch.nn.Module):
            logger.warning("EWC requires PyTorch model — skipping Fisher estimation")
            return

        self._model.train()
        fisher: list[torch.Tensor] = [torch.zeros_like(p) for p in self._params]
        self._model.zero_grad()

        count = 0
        for batch_idx in range(0, min(num_samples, len(dataset)), batch_size):
            batch = dataset[batch_idx : batch_idx + batch_size] if hasattr(dataset, "__getitem__") else dataset
            inputs = batch if isinstance(batch, (list, np.ndarray)) else batch[0]
            targets = batch[1] if isinstance(batch, (tuple, list)) and len(batch) > 1 else None

            input_tensor = torch.tensor(inputs, dtype=torch.float32)
            output = self._model(input_tensor)

            if targets is not None:
                target_tensor = torch.tensor(targets, dtype=torch.long)
                loss = F.cross_entropy(output, target_tensor)
            else:
                probs = F.softmax(output, dim=-1)
                log_probs = F.log_softmax(output, dim=-1)
                loss = -torch.sum(probs * log_probs) / output.size(0)

            loss.backward()
            for i, p in enumerate(self._model.parameters()):
                if p.requires_grad and p.grad is not None:
                    fisher[i] += p.grad.pow(2) / num_samples
            count += 1

        if self._online and self._fisher_matrices:
            prev_fisher = self._fisher_matrices[-1]
            self._fisher_matrices.append([
                self._gamma * f + (1 - self._gamma) * pf
                for f, pf in zip(fisher, prev_fisher)
            ])
            for i, p in enumerate(self._params):
                self._optimal_params[i] = p.detach().clone()
        else:
            self._fisher_matrices.append(fisher)
            self._optimal_params = [p.detach().clone() for p in self._params]

        self._model.eval()
        logger.info("EWC Fisher information estimated over %d samples", count)

    def ewc_loss(self) -> torch.Tensor:
        if not TORCH_AVAILABLE or not self._fisher_matrices:
            return torch.tensor(0.0)

        loss = torch.tensor(0.0)
        for i, p in enumerate(self._model.parameters()):
            if p.requires_grad:
                for fisher, opt_param in zip(self._fisher_matrices, self._optimal_params):
                    if i < len(fisher) and i < len(self._optimal_params):
                        loss += (fisher[i] * (p - opt_param).pow(2)).sum()
        return self._ewc_lambda * loss

    def get_importance_scores(self) -> dict[str, float]:
        if not self._fisher_matrices:
            return {}
        scores = {}
        for i, fisher in enumerate(self._fisher_matrices[-1]):
            if i < len(self._params):
                fmean = float(fisher.mean().item()) if fisher.numel() > 0 else 0.0
                scores[f"param_group_{i}"] = fmean
        return scores

    def get_state(self) -> dict:
        if not TORCH_AVAILABLE:
            return {}
        return {
            "ewc_lambda": self._ewc_lambda,
            "online": self._online,
            "gamma": self._gamma,
            "num_tasks": len(self._fisher_matrices),
            "has_fisher": len(self._fisher_matrices) > 0,
        }
