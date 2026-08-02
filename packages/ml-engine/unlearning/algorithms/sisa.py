import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

import torch

from models.sharded_classifier import ShardedModel
from training.data import Dataset, accuracy_score, generate_synthetic_data, split_dataset
from unlearning.algorithms.base import UnlearningAlgorithm, UnlearningContext, UnlearningResult


class SISAUnlearning(UnlearningAlgorithm):
    @property
    def name(self) -> str:
        return "SISA"

    @property
    def theoretical_guarantee(self) -> str:
        return "Exact unlearning within shard. Trade-off: more shards = faster unlearning, lower accuracy."

    def __init__(self, num_shards: int = 10) -> None:
        self.num_shards = num_shards
        self.model: Optional[ShardedModel] = None
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
                    seed=hash(context.model_name + "_sisa") % (2**31),
                )
                self.model = ShardedModel(
                    input_dim=input_dim,
                    num_shards=self.num_shards,
                    num_classes=num_classes,
                )
                for shard_idx in range(self.num_shards):
                    shard_data = split_dataset(self.training_data, shard_idx, self.num_shards)
                    if shard_data.size > 0:
                        self.model.train_shard(
                            shard_idx, shard_data.features, shard_data.labels, epochs=30
                        )
                self._trained = True

            target_ids = set(context.target_data_ids)
            affected_shards: set[int] = set()
            for did in target_ids:
                shard_idx = hash(did) % self.num_shards
                affected_shards.add(shard_idx)

            retrained_count = 0
            for shard_idx in affected_shards:
                remaining = self.training_data.remove_by_ids(target_ids)
                shard_data = split_dataset(remaining, shard_idx, self.num_shards)
                if shard_data.size > 0:
                    self.model.train_shard(
                        shard_idx, shard_data.features, shard_data.labels, epochs=30
                    )
                    retrained_count += 1

            self.training_data = self.training_data.remove_by_ids(target_ids)

            all_preds = self.model.predict(self.training_data.features)
            utility = accuracy_score(self.training_data, all_preds)

            processing_time = int((time.perf_counter() - start_time) * 1000)
            return UnlearningResult(
                success=True,
                algorithm=self.name,
                processing_time_ms=processing_time,
                utility_retained=utility,
                metrics={
                    "shards_affected": len(affected_shards),
                    "shards_total": self.num_shards,
                    "retrained_shards": retrained_count,
                    "model_input_dim": input_dim,
                    "training_samples": self.training_data.size,
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
            try:
                shard_idx = hash(did) % self.num_shards
                if self.training_data is not None:
                    matching = [i for i, idd in enumerate(self.training_data.data_ids) if idd == did]
                    if matching:
                        return False
            except Exception:
                logger.warning("SISA verification failed")
                return False
        return True
