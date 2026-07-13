import math
from typing import Any, Optional

import torch
from torch import Tensor, nn
from torch.optim import AdamW


class ShardNet(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 64, num_classes: int = 2):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, num_classes),
        )

    def forward(self, x: Tensor) -> Tensor:
        return self.net(x)


class ShardedModel:
    def __init__(
        self,
        input_dim: int,
        num_shards: int,
        hidden_dim: int = 64,
        num_classes: int = 2,
        learning_rate: float = 1e-3,
        device: Optional[torch.device] = None,
    ):
        self.num_shards = num_shards
        self.input_dim = input_dim
        self.num_classes = num_classes
        self.device = device or torch.device("cpu")
        self.models: list[ShardNet] = [
            ShardNet(input_dim, hidden_dim, num_classes).to(self.device)
            for _ in range(num_shards)
        ]
        self.learning_rate = learning_rate
        self._shard_datasets: dict[int, Any] = {}

    def get_device(self) -> torch.device:
        return self.device

    def train_shard(
        self,
        shard_idx: int,
        features: Tensor,
        labels: Tensor,
        epochs: int = 50,
        verbose: bool = False,
    ):
        model = self.models[shard_idx]
        model.train()
        optimizer = AdamW(model.parameters(), lr=self.learning_rate)
        criterion = nn.CrossEntropyLoss()
        features, labels = features.to(self.device), labels.to(self.device)

        for epoch in range(epochs):
            optimizer.zero_grad()
            outputs = model(features)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

    def predict_shard(self, shard_idx: int, features: Tensor) -> Tensor:
        model = self.models[shard_idx]
        model.eval()
        with torch.no_grad():
            logits = model(features.to(self.device))
            return logits.softmax(dim=-1)

    def predict(self, features: Tensor) -> Tensor:
        all_probs = []
        for shard_idx in range(self.num_shards):
            probs = self.predict_shard(shard_idx, features)
            all_probs.append(probs.unsqueeze(0))

        stacked = torch.cat(all_probs, dim=0)
        avg_probs = stacked.mean(dim=0)
        return avg_probs.argmax(dim=-1)

    def predict_logits(self, features: Tensor) -> Tensor:
        all_logits = []
        for shard_idx in range(self.num_shards):
            model = self.models[shard_idx]
            model.eval()
            with torch.no_grad():
                logits = model(features.to(self.device))
                all_logits.append(logits.unsqueeze(0))
        stacked = torch.cat(all_logits, dim=0)
        return stacked.mean(dim=0)

    def get_shard_params(self, shard_idx: int) -> list[Tensor]:
        return [p.data.clone() for p in self.models[shard_idx].parameters()]

    def set_shard_params(self, shard_idx: int, params: list[Tensor]):
        for p, new_p in zip(self.models[shard_idx].parameters(), params):
            p.data.copy_(new_p.data)

    def num_params(self) -> int:
        return sum(p.numel() for p in self.models[0].parameters())

    def flattened_params(self, shard_idx: int) -> Tensor:
        return torch.cat([p.data.flatten() for p in self.models[shard_idx].parameters()])

    def set_flattened_params(self, shard_idx: int, flat: Tensor):
        idx = 0
        for p in self.models[shard_idx].parameters():
            n = p.numel()
            p.data.copy_(flat[idx:idx + n].reshape(p.shape))
            idx += n
