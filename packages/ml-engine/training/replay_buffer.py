import json
import logging
import os
import random
import threading
import uuid
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ReplaySample:
    sample_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    input_data: list[float] = field(default_factory=list)
    target: Any = None
    task_id: str = "default"
    importance: float = 0.5
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict = field(default_factory=dict)


@dataclass
class ReplayBufferConfig:
    capacity: int = 10000
    storage_path: str = "./replay_buffer"
    min_samples_for_replay: int = 100
    sampling_strategy: str = "uniform"
    importance_decay: float = 0.99
    persist_interval: int = 100


class ReservoirSampler:
    def __init__(self, capacity: int, rng: Optional[random.Random] = None) -> None:
        self._capacity = capacity
        self._buffer: list[ReplaySample] = []
        self._counter = 0
        self._rng = rng or random.Random(42)

    def add(self, sample: ReplaySample) -> Optional[ReplaySample]:
        self._counter += 1
        if len(self._buffer) < self._capacity:
            self._buffer.append(sample)
            return None
        j = self._rng.randint(0, self._counter - 1)
        if j < self._capacity:
            evicted = self._buffer[j]
            self._buffer[j] = sample
            return evicted
        return None

    def sample(self, n: int) -> list[ReplaySample]:
        k = min(n, len(self._buffer))
        return self._rng.sample(self._buffer, k)

    def __len__(self) -> int:
        return len(self._buffer)

    def get_all(self) -> list[ReplaySample]:
        return list(self._buffer)


class ImportanceSampler:
    def __init__(self, capacity: int, rng: Optional[random.Random] = None) -> None:
        self._capacity = capacity
        self._buffer: list[ReplaySample] = []
        self._rng = rng or random.Random(42)

    def add(self, sample: ReplaySample) -> Optional[ReplaySample]:
        if len(self._buffer) < self._capacity:
            self._buffer.append(sample)
            return None
        min_imp = min(s.importance for s in self._buffer)
        if sample.importance > min_imp:
            for i, s in enumerate(self._buffer):
                if s.importance == min_imp:
                    evicted = self._buffer.pop(i)
                    self._buffer.append(sample)
                    return evicted
        return sample

    def sample(self, n: int) -> list[ReplaySample]:
        k = min(n, len(self._buffer))
        weights = [s.importance for s in self._buffer]
        total = sum(weights)
        if total == 0:
            return self._rng.sample(self._buffer, k)
        probs = [w / total for w in weights]
        indices = self._rng.choices(range(len(self._buffer)), weights=probs, k=k)
        return [self._buffer[i] for i in indices]

    def __len__(self) -> int:
        return len(self._buffer)

    def get_all(self) -> list[ReplaySample]:
        return list(self._buffer)


class ReplayBuffer:
    def __init__(self, config: Optional[ReplayBufferConfig] = None) -> None:
        self._config = config or ReplayBufferConfig()
        self._lock = threading.RLock()

        if self._config.sampling_strategy == "importance":
            self._sampler = ImportanceSampler(self._config.capacity)
        else:
            self._sampler = ReservoirSampler(self._config.capacity)

        self._add_count = 0
        self._task_distribution: dict[str, int] = {}
        os.makedirs(self._config.storage_path, exist_ok=True)
        self._load()

    def add(
        self,
        input_data: list[float],
        target: Any = None,
        task_id: str = "default",
        importance: float = 0.5,
        metadata: Optional[dict] = None,
    ) -> None:
        with self._lock:
            sample = ReplaySample(
                input_data=input_data,
                target=target,
                task_id=task_id,
                importance=importance,
                metadata=metadata or {},
            )
            self._sampler.add(sample)
            self._add_count += 1
            self._task_distribution[task_id] = self._task_distribution.get(task_id, 0) + 1
            if self._add_count % self._config.persist_interval == 0:
                self._persist()

    def sample(self, n: int, task_id: Optional[str] = None) -> list[ReplaySample]:
        with self._lock:
            if task_id:
                filtered = [s for s in self._sampler.get_all() if s.task_id == task_id]
                k = min(n, len(filtered))
                return random.sample(filtered, k) if filtered else []
            return self._sampler.sample(n)

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "capacity": self._config.capacity,
                "size": len(self._sampler),
                "add_count": self._add_count,
                "sampling_strategy": self._config.sampling_strategy,
                "task_distribution": dict(self._task_distribution),
                "num_tasks": len(self._task_distribution),
                "fill_pct": round(len(self._sampler) / max(self._config.capacity, 1) * 100, 2),
            }

    def clear_task(self, task_id: str) -> int:
        with self._lock:
            before = len(self._sampler)
            remaining = [s for s in self._sampler.get_all() if s.task_id != task_id]
            new_sampler = ReservoirSampler(self._config.capacity)
            for s in remaining:
                new_sampler.add(s)
            self._sampler = new_sampler
            self._task_distribution.pop(task_id, None)
            removed = before - len(remaining)
            self._persist()
            return removed

    def update_importance(self, sample_id: str, importance: float) -> bool:
        with self._lock:
            for s in self._sampler.get_all():
                if s.sample_id == sample_id:
                    s.importance = importance
                    return True
            return False

    def decay_importances(self) -> None:
        with self._lock:
            for s in self._sampler.get_all():
                s.importance *= self._config.importance_decay

    def _persist(self) -> None:
        try:
            path = os.path.join(self._config.storage_path, "replay_buffer.json")
            data = {
                "config": asdict(self._config),
                "samples": [asdict(s) for s in self._sampler.get_all()],
                "add_count": self._add_count,
                "task_distribution": self._task_distribution,
            }
            with open(path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception:
            logger.exception("Failed to persist replay buffer")

    def _load(self) -> None:
        path = os.path.join(self._config.storage_path, "replay_buffer.json")
        if not os.path.exists(path):
            return
        try:
            with open(path) as f:
                data = json.load(f)
            for sd in data.get("samples", []):
                s = ReplaySample(**sd)
                self._sampler.add(s)
            self._add_count = data.get("add_count", 0)
            self._task_distribution.update(data.get("task_distribution", {}))
            logger.info("Loaded %d replay samples from %s", len(self._sampler), path)
        except Exception:
            logger.exception("Failed to load replay buffer")
