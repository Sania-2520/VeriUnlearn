import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from unlearning.algorithms.base import (
    UnlearningAlgorithm,
    UnlearningContext,
    UnlearningResult,
)
from unlearning.algorithms.sisa import SISAUnlearning
from unlearning.algorithms.influence import InfluenceFunctionUnlearning
from unlearning.algorithms.certified_removal import CertifiedRemovalUnlearning

logger = logging.getLogger(__name__)

try:
    import torch
    CUDA_AVAILABLE = torch.cuda.is_available()
except ImportError:
    CUDA_AVAILABLE = False


@dataclass
class StrategyDecision:
    algorithm_name: str
    reasons: list[str] = field(default_factory=list)
    estimated_time_ms: int = 0
    confidence: float = 0.5
    priority: int = 0


@dataclass
class ControllerMetrics:
    total_requests: int = 0
    requests_by_algorithm: dict[str, int] = field(default_factory=dict)
    avg_latency_ms: float = 0.0
    total_processing_time_ms: float = 0.0
    success_rate: float = 1.0
    errors: int = 0
    decisions_log: list[dict] = field(default_factory=list)


@dataclass
class ControllerConfig:
    sisa_shards: int = 10
    influence_damping: float = 1e-3
    certified_epsilon: float = 0.1
    certified_delta: float = 1e-5
    max_retries: int = 2
    timeout_multiplier: float = 1.5
    gpu_weight: float = 0.2
    latency_weight: float = 0.3
    accuracy_weight: float = 0.3
    regulatory_weight: float = 0.2


# Baseline estimated times in ms per algorithm (heuristic defaults)
_BASELINE_TIMES: dict[str, dict[str, int]] = {
    "influence": {"small": 50, "medium": 200, "large": 800},
    "sisa": {"small": 150, "medium": 400, "large": 1200},
    "certified": {"small": 80, "medium": 300, "large": 1000},
}

_TIGHT_LATENCY_MS = 200


class HybridAdaptiveController:
    """Hybrid Adaptive Unlearning Controller (HAUC).

    Dynamically selects and combines unlearning strategies based on:
    - Data characteristics (size, distribution, sensitivity)
    - Model architecture and size
    - Latency requirements
    - Accuracy requirements
    - Regulatory requirements
    - GPU availability
    """

    def __init__(self, config: Optional[ControllerConfig] = None) -> None:
        self.config = config or ControllerConfig()

        self.algorithms: dict[str, UnlearningAlgorithm] = {
            "sisa": SISAUnlearning(num_shards=self.config.sisa_shards),
            "influence": InfluenceFunctionUnlearning(
                damping=self.config.influence_damping
            ),
            "certified": CertifiedRemovalUnlearning(
                epsilon=self.config.certified_epsilon,
                delta=self.config.certified_delta,
            ),
        }

        self.metrics = ControllerMetrics()
        self._decisions_log: deque[dict] = deque(maxlen=200)
        self._execution_history: list[dict[str, Any]] = []
        self._algorithm_health: dict[str, bool] = {
            name: True for name in self.algorithms
        }

    # ------------------------------------------------------------------
    # Strategy selection
    # ------------------------------------------------------------------

    def select_strategies(
        self, context: UnlearningContext,
    ) -> list[StrategyDecision]:
        decisions: list[StrategyDecision] = []
        num_records = len(context.target_data_ids)
        data_sensitivity = context.config.get("data_sensitivity", "standard")
        latency_req = context.latency_ms
        accuracy_req = context.accuracy_target
        model_type = context.model_type.lower()
        regulatory = context.regulatory.lower()

        size_bucket = (
            "small" if num_records <= 20
            else "medium" if num_records <= 500
            else "large"
        )

        # ----- Influence scoring -----
        inf_score = 0.0
        inf_reasons: list[str] = []
        if num_records <= 20:
            inf_score += 0.4
            inf_reasons.append(f"small data size ({num_records} records)")
        if latency_req <= _TIGHT_LATENCY_MS:
            inf_score += 0.3
            inf_reasons.append(f"tight latency ({latency_req}ms)")
        if model_type == "transformer":
            inf_score += 0.15
            inf_reasons.append("transformer model favours influence")
        if not CUDA_AVAILABLE:
            inf_score += 0.15
            inf_reasons.append("CPU-only: influence is more efficient")
        if inf_score > 0:
            decisions.append(StrategyDecision(
                algorithm_name="influence",
                reasons=inf_reasons,
                estimated_time_ms=self._estimate_time("influence", size_bucket),
                confidence=min(inf_score, 1.0),
                priority=1 if latency_req <= _TIGHT_LATENCY_MS else 3,
            ))

        # ----- SISA scoring -----
        sis_score = 0.0
        sis_reasons: list[str] = []
        if num_records > 500:
            sis_score += 0.4
            sis_reasons.append(f"large data size ({num_records} records)")
        elif num_records > 20:
            sis_score += 0.2
            sis_reasons.append(f"medium data size ({num_records} records)")
        if model_type == "tabular":
            sis_score += 0.2
            sis_reasons.append("tabular model favours SISA")
        if CUDA_AVAILABLE:
            sis_score += 0.15
            sis_reasons.append("GPU available: SISA shards train faster")
        if sis_score > 0:
            decisions.append(StrategyDecision(
                algorithm_name="sisa",
                reasons=sis_reasons,
                estimated_time_ms=self._estimate_time("sisa", size_bucket),
                confidence=min(sis_score, 1.0),
                priority=1 if num_records > 500 else 3,
            ))

        # ----- Certified scoring -----
        cert_score = 0.0
        cert_reasons: list[str] = []
        if accuracy_req >= 0.95:
            cert_score += 0.25
            cert_reasons.append(f"high accuracy target ({accuracy_req})")
        if regulatory in ("gdpr", "ai_act", "hipaa", "ccpa"):
            cert_score += 0.35
            cert_reasons.append(f"regulatory requirement ({regulatory})")
        if data_sensitivity in ("healthcare", "legal", "financial"):
            cert_score += 0.25
            cert_reasons.append(f"sensitive domain ({data_sensitivity})")
        if cert_score > 0:
            decisions.append(StrategyDecision(
                algorithm_name="certified",
                reasons=cert_reasons,
                estimated_time_ms=self._estimate_time("certified", size_bucket),
                confidence=min(cert_score, 1.0),
                priority=2,
            ))

        decisions = self._deduplicate(decisions)
        decisions.sort(key=lambda d: (d.priority, -d.confidence))

        self._log_decision(decisions, context)
        return decisions

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute(self, context: UnlearningContext) -> UnlearningResult:
        decisions = self.select_strategies(context)
        if not decisions:
            self.metrics.errors += 1
            return UnlearningResult(
                success=False,
                algorithm="hybrid",
                error_message="No suitable strategy found",
            )

        start_time = time.perf_counter()
        self.metrics.total_requests += 1

        results = await self._execute_with_retries(decisions, context)

        successful_results = [
            r for r in results if isinstance(r, UnlearningResult) and r.success
        ]

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        for d in decisions:
            self.metrics.requests_by_algorithm[d.algorithm_name] = (
                self.metrics.requests_by_algorithm.get(d.algorithm_name, 0) + 1
            )

        if not successful_results:
            self.metrics.errors += 1
            self._update_latency_metric(elapsed_ms)
            return UnlearningResult(
                success=False,
                algorithm="hybrid",
                processing_time_ms=elapsed_ms,
                error_message="All strategies failed",
            )

        combined = self._combine_results(successful_results)
        combined.processing_time_ms = elapsed_ms
        combined.metadata["decisions"] = [
            {
                "algorithm": d.algorithm_name,
                "reasons": d.reasons,
                "confidence": d.confidence,
                "estimated_time_ms": d.estimated_time_ms,
            }
            for d in decisions
        ]

        self._update_latency_metric(elapsed_ms)

        self._execution_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "num_records": len(context.target_data_ids),
            "algorithms": [d.algorithm_name for d in decisions],
            "successful": [r.algorithm for r in successful_results],
            "elapsed_ms": elapsed_ms,
        })

        return combined

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    async def verify_all(self, context: UnlearningContext) -> dict[str, bool]:
        verification_results: dict[str, bool] = {}
        for name, algorithm in self.algorithms.items():
            try:
                verification_results[name] = await algorithm.verify(context)
            except Exception as exc:
                logger.warning("verify failed for %s: %s", name, exc)
                verification_results[name] = False
        return verification_results

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def health_check(self) -> dict:
        status: dict[str, Any] = {}
        for name, algorithm in self.algorithms.items():
            try:
                can_instantiate = algorithm is not None
                status[name] = {
                    "available": can_instantiate and self._algorithm_health.get(name, False),
                    "type": type(algorithm).__name__,
                    "properties": {
                        "name": algorithm.name,
                        "theoretical_guarantee": algorithm.theoretical_guarantee,
                    },
                }
            except Exception as exc:
                status[name] = {
                    "available": False,
                    "error": str(exc),
                }
        status["cuda_available"] = CUDA_AVAILABLE
        return status

    # ------------------------------------------------------------------
    # Metrics / introspection
    # ------------------------------------------------------------------

    def get_metrics(self) -> dict:
        return {
            "total_requests": self.metrics.total_requests,
            "requests_by_algorithm": dict(self.metrics.requests_by_algorithm),
            "avg_latency_ms": self.metrics.avg_latency_ms,
            "total_processing_time_ms": self.metrics.total_processing_time_ms,
            "success_rate": self.metrics.success_rate,
            "errors": self.metrics.errors,
            "recent_decisions": list(self._decisions_log)[-10:],
        }

    def get_decision_log(self, limit: int = 50) -> list[dict]:
        log = list(self._decisions_log)
        return log[-limit:]

    def estimate_time(self, context: UnlearningContext) -> dict[str, int]:
        num_records = len(context.target_data_ids)
        size_bucket = (
            "small" if num_records <= 20
            else "medium" if num_records <= 500
            else "large"
        )
        return {
            name: self._estimate_time(name, size_bucket)
            for name in self.algorithms
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _combine_results(self, results: list[UnlearningResult]) -> UnlearningResult:
        combined = UnlearningResult(
            success=True,
            algorithm="hybrid",
            utility_retained=min(r.utility_retained for r in results),
            metrics={},
        )
        for r in results:
            combined.metrics[r.algorithm] = {
                "utility_retained": r.utility_retained,
                "processing_time_ms": r.processing_time_ms,
                "sub_metrics": r.metrics,
            }
        return combined

    def _deduplicate(
        self, strategies: list[StrategyDecision],
    ) -> list[StrategyDecision]:
        seen: set[str] = set()
        deduplicated: list[StrategyDecision] = []
        for s in strategies:
            if s.algorithm_name not in seen:
                seen.add(s.algorithm_name)
                deduplicated.append(s)
        return deduplicated

    def _log_decision(
        self, decisions: list[StrategyDecision], context: UnlearningContext,
    ) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "num_records": len(context.target_data_ids),
            "model_type": context.model_type,
            "latency_ms": context.latency_ms,
            "accuracy_target": context.accuracy_target,
            "regulatory": context.regulatory,
            "cuda_available": CUDA_AVAILABLE,
            "selected": [
                {
                    "algorithm": d.algorithm_name,
                    "reasons": d.reasons,
                    "confidence": d.confidence,
                    "estimated_time_ms": d.estimated_time_ms,
                }
                for d in decisions
            ],
        }
        self._decisions_log.append(entry)
        logger.info(
            "Strategy selection: %s",
            [d.algorithm_name for d in decisions],
        )

    def _estimate_time(self, algorithm_name: str, size_bucket: str) -> int:
        base = _BASELINE_TIMES.get(algorithm_name, {}).get(size_bucket, 500)
        multiplier = self.config.timeout_multiplier if not CUDA_AVAILABLE else 1.0
        return int(base * multiplier)

    async def _execute_with_retries(
        self,
        decisions: list[StrategyDecision],
        context: UnlearningContext,
    ) -> list[UnlearningResult]:
        max_retries = self.config.max_retries
        results: list[UnlearningResult] = []
        pending: list[tuple[UnlearningAlgorithm, int, StrategyDecision]] = [
            (self.algorithms[d.algorithm_name], 0, d)
            for d in decisions
            if d.algorithm_name in self.algorithms
        ]

        while pending:
            batch: list[asyncio.Task] = []
            batch_meta: list[tuple[int, StrategyDecision]] = []
            for alg, attempt, decision in pending:
                task = asyncio.ensure_future(alg.unlearn(context))
                batch.append(task)
                batch_meta.append((attempt, decision))

            outcomes = await asyncio.gather(*batch, return_exceptions=True)

            next_pending: list[tuple[UnlearningAlgorithm, int, StrategyDecision]] = []
            for idx, outcome in enumerate(outcomes):
                attempt, decision = batch_meta[idx]
                if isinstance(outcome, UnlearningResult) and outcome.success:
                    results.append(outcome)
                elif isinstance(outcome, Exception):
                    logger.warning(
                        "Algorithm %s failed (attempt %d): %s",
                        decision.algorithm_name, attempt, outcome,
                    )
                    if attempt < max_retries:
                        next_pending.append((
                            self.algorithms[decision.algorithm_name],
                            attempt + 1,
                            decision,
                        ))
                    else:
                        results.append(UnlearningResult(
                            success=False,
                            algorithm=decision.algorithm_name,
                            error_message=str(outcome),
                        ))
                else:
                    if attempt < max_retries:
                        next_pending.append((
                            self.algorithms[decision.algorithm_name],
                            attempt + 1,
                            decision,
                        ))
                    else:
                        results.append(outcome)

            pending = next_pending
            if pending:
                await asyncio.sleep(0.05)

        return results

    def _update_latency_metric(self, elapsed_ms: int) -> None:
        n = self.metrics.total_requests
        prev_total = self.metrics.avg_latency_ms * (n - 1)
        self.metrics.avg_latency_ms = (prev_total + elapsed_ms) / max(n, 1)
        self.metrics.total_processing_time_ms += elapsed_ms
        if n > 0:
            self.metrics.success_rate = max(
                0.0,
                1.0 - (self.metrics.errors / n),
            )
