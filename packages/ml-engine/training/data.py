import math
import random
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import torch
from torch import Tensor


@dataclass
class Dataset:
    features: Tensor
    labels: Tensor
    data_ids: list[str] = field(default_factory=list)

    @property
    def size(self) -> int:
        return len(self.labels)

    def get_subset(self, indices: list[int]) -> "Dataset":
        return Dataset(
            features=self.features[indices],
            labels=self.labels[indices],
            data_ids=[self.data_ids[i] for i in indices],
        )

    def get_by_ids(self, target_ids: set[str]) -> "Dataset":
        indices = [i for i, did in enumerate(self.data_ids) if did in target_ids]
        return self.get_subset(indices)

    def remove_by_ids(self, target_ids: set[str]) -> "Dataset":
        keep_indices = [i for i, did in enumerate(self.data_ids) if did not in target_ids]
        return self.get_subset(keep_indices)

    def to_tensors(self, device: torch.device = torch.device("cpu")):
        return self.features.to(device), self.labels.to(device)


def generate_synthetic_data(
    num_samples: int,
    num_features: int = 20,
    num_classes: int = 2,
    noise: float = 0.1,
    seed: int = 42,
) -> Dataset:
    rng = np.random.RandomState(seed)
    X = rng.randn(num_samples, num_features).astype(np.float32)
    true_w = rng.randn(num_features, num_classes).astype(np.float32)
    logits = X @ true_w
    if num_classes == 2:
        probs = 1.0 / (1.0 + np.exp(-logits[:, 0]))
        y = (probs > 0.5).astype(np.int64)
    else:
        probs = np.exp(logits - logits.max(axis=1, keepdims=True))
        probs /= probs.sum(axis=1, keepdims=True)
        y = np.array([rng.multinomial(1, p).argmax() for p in probs])

    flip_mask = rng.rand(num_samples) < noise
    if num_classes == 2:
        y[flip_mask] = 1 - y[flip_mask]
    else:
        y[flip_mask] = rng.randint(0, num_classes, size=flip_mask.sum())

    data_ids = [f"data_{i:06d}" for i in range(num_samples)]

    return Dataset(
        features=torch.from_numpy(X),
        labels=torch.from_numpy(y),
        data_ids=data_ids,
    )


def generate_nonlinear_data(
    num_samples: int,
    num_features: int = 10,
    num_classes: int = 2,
    noise: float = 0.05,
    seed: int = 42,
) -> Dataset:
    rng = np.random.RandomState(seed)
    X = rng.randn(num_samples, num_features).astype(np.float32)
    hidden = np.tanh(X @ rng.randn(num_features, 8).astype(np.float32))
    logits = hidden @ rng.randn(8, num_classes).astype(np.float32)
    if num_classes == 2:
        probs = 1.0 / (1.0 + np.exp(-logits[:, 0]))
        y = (probs > 0.5).astype(np.int64)
    else:
        probs = np.exp(logits - logits.max(axis=1, keepdims=True))
        probs /= probs.sum(axis=1, keepdims=True)
        y = np.array([rng.multinomial(1, p).argmax() for p in probs])

    flip_mask = rng.rand(num_samples) < noise
    if num_classes == 2:
        y[flip_mask] = 1 - y[flip_mask]
    else:
        y[flip_mask] = rng.randint(0, num_classes, size=flip_mask.sum())

    data_ids = [f"data_{i:06d}" for i in range(num_samples)]

    return Dataset(
        features=torch.from_numpy(X),
        labels=torch.from_numpy(y),
        data_ids=data_ids,
    )


def accuracy_score(dataset: Dataset, predictions: Tensor) -> float:
    return (predictions == dataset.labels).float().mean().item()


def split_dataset(dataset: Dataset, shard_id: int, num_shards: int) -> Dataset:
    indices = [i for i in range(dataset.size) if hash(dataset.data_ids[i]) % num_shards == shard_id]
    return dataset.get_subset(indices)
