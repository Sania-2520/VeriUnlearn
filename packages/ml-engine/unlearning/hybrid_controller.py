import asyncio
import time
from typing import Optional

from unlearning.algorithms.base import (
    UnlearningAlgorithm,
    UnlearningContext,
    UnlearningResult,
)
from unlearning.algorithms.sisa import SISAUnlearning
from unlearning.algorithms.influence import InfluenceFunctionUnlearning
from unlearning.algorithms.certified_removal import CertifiedRemovalUnlearning


class HybridAdaptiveController:
    """Hybrid Adaptive Unlearning Controller (HAUC).
    
    Dynamically selects and combines unlearning strategies based on:
    - Data characteristics (size, distribution, sensitivity)
    - Model architecture and size
    - Latency requirements
    - Accuracy requirements
    - Regulatory requirements
    """

    def __init__(
        self,
        sisa_shards: int = 10,
        influence_damping: float = 1e-3,
        certified_epsilon: float = 0.1,
        certified_delta: float = 1e-5,
    ) -> None:
        self.algorithms: dict[str, UnlearningAlgorithm] = {
            "sisa": SISAUnlearning(num_shards=sisa_shards),
            "influence": InfluenceFunctionUnlearning(damping=influence_damping),
            "certified": CertifiedRemovalUnlearning(
                epsilon=certified_epsilon, delta=certified_delta
            ),
        }

    def select_strategies(
        self, context: UnlearningContext
    ) -> list[UnlearningAlgorithm]:
        strategies: list[UnlearningAlgorithm] = []
        num_records = len(context.target_data_ids)
        data_sensitivity = context.config.get("data_sensitivity", "standard")

        if num_records <= 20:
            strategies.append(self.algorithms["influence"])
        elif 20 < num_records <= 500:
            strategies.extend([
                self.algorithms["sisa"],
                self.algorithms["influence"],
                self.algorithms["certified"],
            ])
        else:
            strategies.append(self.algorithms["sisa"])

        if data_sensitivity in ("healthcare", "legal", "financial"):
            strategies.append(self.algorithms["certified"])

        if context.regulatory in ("gdpr", "ai_act", "hipaa", "ccpa"):
            strategies.append(self.algorithms["certified"])

        return self._deduplicate(strategies)

    async def execute(
        self, context: UnlearningContext
    ) -> UnlearningResult:
        strategies = self.select_strategies(context)
        if not strategies:
            return UnlearningResult(
                success=False,
                algorithm="hybrid",
                error_message="No suitable strategy found",
            )

        start_time = time.perf_counter()
        results = await asyncio.gather(
            *[strategy.unlearn(context) for strategy in strategies],
            return_exceptions=True,
        )

        successful_results = [
            r for r in results
            if isinstance(r, UnlearningResult) and r.success
        ]

        if not successful_results:
            return UnlearningResult(
                success=False,
                algorithm="hybrid",
                processing_time_ms=int((time.perf_counter() - start_time) * 1000),
                error_message="All strategies failed",
            )

        combined_result = self._combine_results(successful_results)
        combined_result.processing_time_ms = int(
            (time.perf_counter() - start_time) * 1000
        )
        return combined_result

    async def verify_all(self, context: UnlearningContext) -> dict[str, bool]:
        verification_results = {}
        for name, algorithm in self.algorithms.items():
            verification_results[name] = await algorithm.verify(context)
        return verification_results

    def _deduplicate(
        self, strategies: list[UnlearningAlgorithm]
    ) -> list[UnlearningAlgorithm]:
        seen: set[str] = set()
        deduplicated: list[UnlearningAlgorithm] = []
        for s in strategies:
            if s.name not in seen:
                seen.add(s.name)
                deduplicated.append(s)
        return deduplicated

    def _combine_results(
        self, results: list[UnlearningResult]
    ) -> UnlearningResult:
        combined = UnlearningResult(
            success=True,
            algorithm="hybrid",
            utility_retained=min(r.utility_retained for r in results),
            metrics={},
        )
        for r in results:
            combined.metrics[r.algorithm] = r.metrics
        return combined
