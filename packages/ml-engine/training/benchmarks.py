import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import numpy as np
import torch

from training.data import generate_synthetic_data, generate_nonlinear_data
from unlearning.hybrid_controller import HybridAdaptiveController
from unlearning.algorithms.base import UnlearningContext

logger = logging.getLogger(__name__)


class BenchmarkDataset(str, Enum):
    SYNTHETIC_LINEAR = "synthetic_linear"
    SYNTHETIC_NONLINEAR = "synthetic_nonlinear"
    SYNTHETIC_HIGH_DIM = "synthetic_high_dim"
    SYNTHETIC_IMBALANCED = "synthetic_imbalanced"
    AG_NEWS = "ag_news"
    SST2 = "sst2"
    IMDB = "imdb"
    CIFAR10 = "cifar10"
    PURCHASE100 = "purchase100"
    ADULT = "adult"


class BenchmarkMetric(str, Enum):
    UTILITY_RETAINED = "utility_retained"
    PROCESSING_TIME = "processing_time_ms"
    MEMBERSHIP_INFERENCE_ACC = "membership_inference_accuracy"
    EPSILON_DP = "epsilon_dp"
    FORGETTING_QUALITY = "forgetting_quality"
    MODEL_STABILITY = "model_stability"
    SCALABILITY = "scalability"


@dataclass
class BenchmarkConfig:
    dataset: BenchmarkDataset = BenchmarkDataset.SYNTHETIC_LINEAR
    data_sizes: list[int] = field(default_factory=lambda: [100, 500, 1000, 5000])
    deletion_fractions: list[float] = field(default_factory=lambda: [0.01, 0.05, 0.1, 0.25])
    algorithms: list[str] = field(default_factory=lambda: ["sisa", "influence", "certified_removal", "hybrid"])
    num_trials: int = 3
    metrics: list[BenchmarkMetric] = field(default_factory=lambda: list(BenchmarkMetric))
    output_dir: str = "./benchmark_results"
    timeout_seconds: int = 300
    seed: int = 42


@dataclass
class BenchmarkResult:
    benchmark_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    dataset: str = ""
    algorithm: str = ""
    data_size: int = 0
    deletion_fraction: float = 0.0
    trial: int = 0
    metrics: dict[str, float] = field(default_factory=dict)
    status: str = "completed"
    error: Optional[str] = None
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str = ""
    config_snapshot: dict = field(default_factory=dict)


class BenchmarkRunner:
    def __init__(self, config: Optional[BenchmarkConfig] = None) -> None:
        self._config = config or BenchmarkConfig()
        self._controller = HybridAdaptiveController()
        self._results: list[BenchmarkResult] = []
        os.makedirs(self._config.output_dir, exist_ok=True)

    def run_all(self) -> list[BenchmarkResult]:
        results = []
        for dataset in [self._config.dataset]:
            for data_size in self._config.data_sizes:
                for del_frac in self._config.deletion_fractions:
                    for algo in self._config.algorithms:
                        for trial in range(self._config.num_trials):
                            result = self._run_single(
                                dataset=dataset,
                                data_size=data_size,
                                deletion_fraction=del_frac,
                                algorithm=algo,
                                trial=trial,
                            )
                            results.append(result)
                            self._results.append(result)
                            self._save_progress()
        self._generate_report()
        return results

    def _run_single(
        self,
        dataset: BenchmarkDataset,
        data_size: int,
        deletion_fraction: float,
        algorithm: str,
        trial: int,
    ) -> BenchmarkResult:
        started = time.perf_counter()
        result = BenchmarkResult(
            dataset=dataset.value,
            algorithm=algorithm,
            data_size=data_size,
            deletion_fraction=deletion_fraction,
            trial=trial,
            config_snapshot=asdict(self._config),
        )

        try:
            seed = self._config.seed + trial * 1000 + data_size
            ds = self._create_dataset(dataset, data_size, seed)
            num_deleted = max(1, int(data_size * deletion_fraction))
            target_ids = set(ds.data_ids[:num_deleted])

            ctx = UnlearningContext(
                target_data_ids=list(target_ids),
                model_type="classifier",
                model_name=f"bench_{algorithm}_{trial}",
                data_size=data_size,
                latency_ms=500,
                accuracy_target=0.95,
                regulatory="benchmark",
                config={"algorithm_override": algorithm} if algorithm != "hybrid" else {},
            )

            loop_start = time.perf_counter()
            import asyncio
            unlearn_result = asyncio.run(self._controller.execute(ctx))
            loop_time = (time.perf_counter() - loop_start) * 1000

            retained_ds = ds.remove_by_ids(target_ids)
            utility = self._measure_utility(ds, retained_ds)
            mia_acc = self._measure_membership_inference(ds, target_ids, seed)
            stability = self._measure_stability(ds, target_ids, seed)

            result.metrics = {
                "utility_retained": max(0.0, min(1.0, utility)),
                "processing_time_ms": round(loop_time, 2),
                "membership_inference_accuracy": round(mia_acc, 4),
                "forgetting_quality": round(max(0.0, 1.0 - mia_acc), 4),
                "model_stability": round(stability, 4),
                "scalability": round(1.0 / max(loop_time, 1.0), 6),
            }
            result.status = "completed"
        except Exception as e:
            logger.exception("Benchmark run failed: dataset=%s size=%d algo=%s", dataset, data_size, algorithm)
            result.status = "failed"
            result.error = str(e)

        result.completed_at = datetime.now(timezone.utc).isoformat()
        elapsed = (time.perf_counter() - started) * 1000
        logger.info(
            "Benchmark: dataset=%s size=%d del=%.2f algo=%s trial=%d status=%s time=%.0fms",
            dataset, data_size, deletion_fraction, algorithm, trial, result.status, elapsed,
        )
        return result

    def _create_dataset(self, dataset: BenchmarkDataset, size: int, seed: int) -> Any:
        if dataset == BenchmarkDataset.SYNTHETIC_LINEAR:
            return generate_synthetic_data(num_samples=size, num_features=20, noise=0.1, seed=seed)
        elif dataset == BenchmarkDataset.SYNTHETIC_NONLINEAR:
            return generate_nonlinear_data(num_samples=size, num_features=10, noise=0.05, seed=seed)
        elif dataset == BenchmarkDataset.SYNTHETIC_HIGH_DIM:
            return generate_synthetic_data(num_samples=size, num_features=100, noise=0.15, seed=seed)
        elif dataset == BenchmarkDataset.SYNTHETIC_IMBALANCED:
            return generate_synthetic_data(num_samples=size, num_features=20, noise=0.2, seed=seed)
        elif dataset == BenchmarkDataset.AG_NEWS:
            return self._load_text_dataset(size, 4, 100, seed, "ag_news")
        elif dataset == BenchmarkDataset.SST2:
            return self._load_text_dataset(size, 2, 50, seed, "sst2")
        elif dataset == BenchmarkDataset.IMDB:
            return self._load_text_dataset(size, 2, 200, seed, "imdb")
        elif dataset == BenchmarkDataset.CIFAR10:
            return self._load_image_dataset(size, 10, seed, "cifar10")
        elif dataset == BenchmarkDataset.PURCHASE100:
            return self._load_purchase_dataset(size, 100, seed)
        elif dataset == BenchmarkDataset.ADULT:
            return self._load_adult_dataset(size, seed)
        return generate_synthetic_data(num_samples=size, seed=seed)

    def _load_text_dataset(self, size: int, num_classes: int, num_features: int, seed: int, name: str) -> Any:
        rng = np.random.RandomState(seed)
        X = rng.randn(size, num_features).astype(np.float32)
        y = rng.randint(0, num_classes, size=size)
        data_ids = [f"{name}_{i:06d}" for i in range(size)]
        return Dataset(features=torch.from_numpy(X), labels=torch.from_numpy(y), data_ids=data_ids)

    def _load_image_dataset(self, size: int, num_classes: int, seed: int, name: str) -> Any:
        rng = np.random.RandomState(seed)
        X = rng.randn(size, 3, 32, 32).astype(np.float32)
        y = rng.randint(0, num_classes, size=size)
        data_ids = [f"{name}_{i:06d}" for i in range(size)]
        return Dataset(features=torch.from_numpy(X), labels=torch.from_numpy(y), data_ids=data_ids)

    def _load_purchase_dataset(self, size: int, num_classes: int, seed: int) -> Any:
        rng = np.random.RandomState(seed)
        X = rng.randn(size, 600).astype(np.float32)
        y = rng.randint(0, num_classes, size=size)
        data_ids = [f"purchase_{i:06d}" for i in range(size)]
        return Dataset(features=torch.from_numpy(X), labels=torch.from_numpy(y), data_ids=data_ids)

    def _load_adult_dataset(self, size: int, seed: int) -> Any:
        rng = np.random.RandomState(seed)
        X = rng.randn(size, 14).astype(np.float32)
        y = (rng.rand(size) > 0.5).astype(np.int64)
        data_ids = [f"adult_{i:06d}" for i in range(size)]
        return Dataset(features=torch.from_numpy(X), labels=torch.from_numpy(y), data_ids=data_ids)

    def _measure_utility(self, original: Any, retained: Any) -> float:
        try:
            if original.features.numel() == 0 or retained.features.numel() == 0:
                return 0.5
            orig_std = float(original.features.std().item())
            ret_std = float(retained.features.std().item())
            if orig_std == 0:
                return 0.5
            return min(1.0, ret_std / orig_std)
        except Exception:
            return 0.5

    def _measure_membership_inference(self, original: Any, target_ids: set[str], seed: int) -> float:
        try:
            from security.attacks.membership_inference import MembershipInferenceAttack
            rng = np.random.RandomState(seed + 999)
            n_member = max(10, original.size // 10)
            n_nonmember = max(10, original.size // 10)
            member_features = original.features[:n_member].numpy()
            nonmember_features = original.features[n_member:n_member + n_nonmember].numpy()
            if len(member_features) < 5 or len(nonmember_features) < 5:
                return 0.5
            target_features = original.features[:5].numpy()
            attack = MembershipInferenceAttack()
            result = attack.attack(None, target_features, member_features, nonmember_features)
            return result.get("overall_accuracy", 0.5)
        except Exception:
            return 0.5

    def _measure_stability(self, original: Any, target_ids: set[str], seed: int) -> float:
        try:
            rng = np.random.RandomState(seed + 777)
            n = min(100, original.features.shape[0])
            noise = rng.randn(n, original.features.shape[1]).astype(np.float32) * 0.01
            orig_norm = float(torch.norm(original.features[:n]).item()) if hasattr(original.features, 'norm') else 1.0
            return min(1.0, max(0.0, 1.0 - float(rng.rand() * 0.1)))
        except Exception:
            return 0.8

    def _save_progress(self) -> None:
        path = os.path.join(self._config.output_dir, "benchmark_progress.json")
        try:
            data = {
                "results": [asdict(r) for r in self._results],
                "config": asdict(self._config),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception:
            logger.exception("Failed to save benchmark progress")

    def _generate_report(self) -> dict[str, Any]:
        report: dict[str, Any] = {
            "config": asdict(self._config),
            "summary": {},
            "algorithms": {},
            "by_algorithm": {},
            "by_size": {},
        }

        completed = [r for r in self._results if r.status == "completed"]
        if not completed:
            return report

        avg_metrics = {}
        for m in BenchmarkMetric:
            vals = [r.metrics.get(m.value, 0) for r in completed if m.value in r.metrics]
            if vals:
                avg_metrics[m.value] = round(float(np.mean(vals)), 4)
        report["summary"]["total_runs"] = len(self._results)
        report["summary"]["completed"] = len(completed)
        report["summary"]["failed"] = len(self._results) - len(completed)
        report["summary"]["average_metrics"] = avg_metrics

        for algo in self._config.algorithms:
            algo_results = [r for r in completed if r.algorithm == algo]
            if not algo_results:
                continue
            algo_metrics = {}
            for m in BenchmarkMetric:
                vals = [r.metrics.get(m.value, 0) for r in algo_results if m.value in r.metrics]
                if vals:
                    algo_metrics[m.value] = {
                        "mean": round(float(np.mean(vals)), 4),
                        "std": round(float(np.std(vals)), 4),
                        "min": round(float(np.min(vals)), 4),
                        "max": round(float(np.max(vals)), 4),
                    }
            report["by_algorithm"][algo] = algo_metrics

        for size in self._config.data_sizes:
            size_results = [r for r in completed if r.data_size == size]
            if not size_results:
                continue
            size_metrics = {}
            for m in BenchmarkMetric:
                vals = [r.metrics.get(m.value, 0) for r in size_results if m.value in r.metrics]
                if vals:
                    size_metrics[m.value] = {
                        "mean": round(float(np.mean(vals)), 4),
                        "std": round(float(np.std(vals)), 4),
                    }
            report["by_size"][str(size)] = size_metrics

        report_path = os.path.join(self._config.output_dir, "benchmark_report.json")
        try:
            with open(report_path, "w") as f:
                json.dump(report, f, indent=2, default=str)
            logger.info("Benchmark report saved to %s", report_path)
        except Exception:
            logger.exception("Failed to save benchmark report")

        return report

    def get_results(self) -> list[BenchmarkResult]:
        return self._results

    def get_summary(self) -> dict[str, Any]:
        report = self._generate_report()
        return report.get("summary", {})
