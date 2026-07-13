#!/usr/bin/env python3
"""Research benchmark runner for VeriUnlearn.

Runs all unlearning algorithms across standard datasets, measures quality
metrics (accuracy, F1, latency, privacy leakage, MIA success), and persists
results as timestamped JSON + CSV for publication.
"""
import argparse
import asyncio
import csv
import json
import math
import os
import sys
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path setup – make ML-engine imports work when invoked from any cwd
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_MLENGINE = _SCRIPT_DIR.parent.parent / "packages" / "ml-engine"
sys.path.insert(0, str(_MLENGINE))

import numpy as np
import torch

from training.data import Dataset, accuracy_score, generate_synthetic_data
from models.single_model import SingleModel
from models.sharded_classifier import ShardedModel
from unlearning.algorithms.sisa import SISAUnlearning
from unlearning.algorithms.influence import InfluenceFunctionUnlearning
from unlearning.algorithms.certified_removal import CertifiedRemovalUnlearning
from unlearning.hybrid_controller import HybridAdaptiveController, ControllerConfig
from unlearning.algorithms.base import UnlearningContext, UnlearningResult
from security.attacks.membership_inference import MembershipInferenceAttack, LossBasedMIA
from verification.privacy_evaluation import PrivacyEvaluator


# ---------------------------------------------------------------------------
# Dataset descriptors
# ---------------------------------------------------------------------------

@dataclass
class DatasetDescriptor:
    name: str
    num_samples: int
    num_features: int
    num_classes: int
    task_type: str  # "classification"
    noise: float = 0.1


DATASETS: dict[str, DatasetDescriptor] = {
    "ag_news": DatasetDescriptor(
        name="AG News", num_samples=120000, num_features=100,
        num_classes=4, task_type="classification", noise=0.15,
    ),
    "imdb": DatasetDescriptor(
        name="IMDB", num_samples=50000, num_features=100,
        num_classes=2, task_type="classification", noise=0.1,
    ),
    "sst2": DatasetDescriptor(
        name="SST-2", num_samples=67349, num_features=80,
        num_classes=2, task_type="classification", noise=0.08,
    ),
    "cifar10": DatasetDescriptor(
        name="CIFAR-10", num_samples=60000, num_features=128,
        num_classes=10, task_type="classification", noise=0.12,
    ),
}

# Reduced sizes for quick synthetic benchmarking
SYNTHETIC_SIZES: dict[str, int] = {
    "ag_news": 2000,
    "imdb": 2000,
    "sst2": 2000,
    "cifar10": 2000,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _try_load_real_dataset(desc: DatasetDescriptor) -> Dataset | None:
    """Attempt to load a real dataset via the `datasets` library."""
    try:
        from datasets import load_dataset as hf_load  # type: ignore
    except ImportError:
        return None

    hf_name_map = {
        "ag_news": ("fancyzhx/ag_news", None),
        "imdb": ("stanfordnlp/imdb", None),
        "sst2": ("glue", "sst2"),
        "cifar10": ("uoft-cs/cifar10", None),
    }

    mapping = hf_name_map.get(desc.name.lower().replace("-", "").replace("_", ""))
    if mapping is None:
        return None

    try:
        ds_name, subset = mapping
        ds = hf_load(ds_name, subset=subset, split="train", trust_remote_code=True)
        rows = min(desc.num_samples, len(ds))

        features_list = []
        labels_list = []
        for idx in range(rows):
            row = ds[idx]
            label = row.get("label", row.get("labels", 0))
            labels_list.append(int(label))

            # Create pseudo-features from text hash
            text = str(row.get("text", row.get("sentence", row.get("review", ""))))
            rng = np.random.RandomState(abs(hash(text)) % (2**31))
            features_list.append(rng.randn(desc.num_features).astype(np.float32))

        X = np.stack(features_list)
        y = np.array(labels_list, dtype=np.int64)
        data_ids = [f"data_{i:06d}" for i in range(rows)]

        return Dataset(
            features=torch.from_numpy(X),
            labels=torch.from_numpy(y),
            data_ids=data_ids,
        )
    except Exception:
        return None


def generate_benchmark_dataset(
    desc: DatasetDescriptor,
    size_override: int | None = None,
) -> Dataset:
    """Generate synthetic data mimicking the dataset's characteristics."""
    n = size_override or desc.num_samples
    return generate_synthetic_data(
        num_samples=n,
        num_features=desc.num_features,
        num_classes=desc.num_classes,
        noise=desc.noise,
        seed=42,
    )


def _precision_recall_f1(
    preds: torch.Tensor, labels: torch.Tensor, num_classes: int,
) -> dict[str, float]:
    """Compute per-class and macro precision/recall/F1."""
    precisions, recalls, f1s = [], [], []
    for c in range(num_classes):
        tp = ((preds == c) & (labels == c)).sum().item()
        fp = ((preds == c) & (labels != c)).sum().item()
        fn = ((preds != c) & (labels == c)).sum().item()
        p = tp / max(tp + fp, 1)
        r = tp / max(tp + fn, 1)
        f1 = 2 * p * r / max(p + r, 1e-8)
        precisions.append(p)
        recalls.append(r)
        f1s.append(f1)
    return {
        "precision_macro": float(np.mean(precisions)),
        "recall_macro": float(np.mean(recalls)),
        "f1_macro": float(np.mean(f1s)),
    }


def _run_mia(
    model: SingleModel | ShardedModel,
    dataset: Dataset,
    unlearned_ids: list[str],
) -> dict[str, Any]:
    """Membership inference attack evaluation."""
    n = dataset.size
    unlearned_set = set(unlearned_ids)

    target_indices = [i for i, did in enumerate(dataset.data_ids) if did in unlearned_set]
    if not target_indices:
        target_indices = list(range(min(10, n)))

    remaining = [i for i, did in enumerate(dataset.data_ids) if did not in unlearned_set]
    split = max(1, len(remaining) // 2)
    member_idx = remaining[:split]
    nonmember_idx = remaining[split:]
    if not member_idx:
        member_idx = list(range(min(10, n)))
    if not nonmember_idx:
        nonmember_idx = list(range(min(10, n)))

    target_feat = dataset.features[target_indices]
    member_feat = dataset.features[member_idx]
    nonmember_feat = dataset.features[nonmember_idx]

    mia = MembershipInferenceAttack(threshold_percentile=5.0)
    result = mia.attack(model, target_feat, member_feat, nonmember_feat)

    loss_mia = LossBasedMIA(threshold_percentile=10.0)
    target_ds = Dataset(
        features=target_feat,
        labels=dataset.labels[target_indices],
        data_ids=[dataset.data_ids[i] for i in target_indices],
    )
    member_ds = Dataset(
        features=member_feat,
        labels=dataset.labels[member_idx],
        data_ids=[dataset.data_ids[i] for i in member_idx],
    )
    nonmember_ds = Dataset(
        features=nonmember_feat,
        labels=dataset.labels[nonmember_idx],
        data_ids=[dataset.data_ids[i] for i in nonmember_idx],
    )
    loss_result = loss_mia.attack(model, target_ds, member_ds, nonmember_ds)

    return {
        "confidence_mia": result,
        "loss_mia": loss_result,
        "privacy_leakage": max(
            result.get("overall_accuracy", 0),
            loss_result.get("overall_accuracy", 0),
        ),
    }


def _confidence_interval(values: list[float], z: float = 1.96) -> dict[str, float]:
    n = len(values)
    if n < 2:
        return {"mean": float(np.mean(values)), "std": 0.0, "ci_lower": float(np.mean(values)), "ci_upper": float(np.mean(values))}
    mean = float(np.mean(values))
    std = float(np.std(values, ddof=1))
    se = std / math.sqrt(n)
    return {
        "mean": mean,
        "std": std,
        "ci_lower": mean - z * se,
        "ci_upper": mean + z * se,
        "n": n,
    }


# ---------------------------------------------------------------------------
# Core benchmark logic
# ---------------------------------------------------------------------------

@dataclass
class BenchmarkResult:
    dataset: str
    algorithm: str
    run_id: str
    timestamp: str
    data_size: int
    num_features: int
    num_classes: int
    # Accuracy metrics
    accuracy: float = 0.0
    precision_macro: float = 0.0
    recall_macro: float = 0.0
    f1_macro: float = 0.0
    utility_retained: float = 0.0
    # Timing
    latency_ms: int = 0
    training_latency_ms: int = 0
    # Privacy
    mia_success_rate: float = 0.0
    privacy_leakage: float = 0.0
    # Algorithm-specific
    shards_affected: int = 0
    noise_scale: float = 0.0
    epsilon: float = 0.0
    # Meta
    success: bool = False
    error: str = ""
    extra_metrics: dict = field(default_factory=dict)


async def _benchmark_single(
    dataset_name: str,
    dataset: Dataset,
    algorithm_name: str,
    num_remove: int,
    num_runs: int,
) -> list[BenchmarkResult]:
    """Run a single algorithm on a single dataset multiple times."""
    results: list[BenchmarkResult] = []
    input_dim = dataset.features.shape[1]
    num_classes = len(dataset.labels.unique())

    for run_idx in range(num_runs):
        run_id = f"{dataset_name}_{algorithm_name}_{run_idx:03d}_{uuid.uuid4().hex[:8]}"
        target_ids = dataset.data_ids[:num_remove]

        br = BenchmarkResult(
            dataset=dataset_name,
            algorithm=algorithm_name,
            run_id=run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            data_size=dataset.size,
            num_features=input_dim,
            num_classes=int(num_classes),
        )

        try:
            # Train a reference model for accuracy baseline
            ref_model = SingleModel(input_dim=input_dim, num_classes=num_classes)
            t0 = time.perf_counter()
            ref_model.train(dataset.features, dataset.labels, epochs=30)
            br.training_latency_ms = int((time.perf_counter() - t0) * 1000)
            ref_preds = ref_model.predict(dataset.features)
            baseline_acc = accuracy_score(dataset, ref_preds)

            # Unlearn
            context = UnlearningContext(
                target_data_ids=target_ids,
                model_type="tabular",
                model_name=f"bench_{dataset_name}",
                data_size=dataset.size,
                latency_ms=5000,
                accuracy_target=0.95,
                config={
                    "input_dim": input_dim,
                    "num_classes": int(num_classes),
                },
            )

            t0 = time.perf_counter()
            if algorithm_name == "sisa":
                algo = SISAUnlearning(num_shards=10)
            elif algorithm_name == "influence":
                algo = InfluenceFunctionUnlearning(damping=1e-3)
            elif algorithm_name == "certified":
                algo = CertifiedRemovalUnlearning(epsilon=0.1, delta=1e-5)
            elif algorithm_name == "hybrid":
                algo = HybridAdaptiveController()
            else:
                raise ValueError(f"Unknown algorithm: {algorithm_name}")

            if algorithm_name == "hybrid":
                ur = await algo.execute(context)
            else:
                ur = await algo.unlearn(context)

            br.latency_ms = int((time.perf_counter() - t0) * 1000)
            br.success = ur.success
            br.utility_retained = ur.utility_retained
            br.extra_metrics = ur.metrics

            # Post-unlearning accuracy
            if algorithm_name == "sisa" and algo.model is not None:
                model_for_mia = algo.model
                remaining_ds = dataset.remove_by_ids(set(target_ids))
                post_preds = model_for_mia.predict(remaining_ds.features)
                post_acc = accuracy_score(remaining_ds, post_preds)
            elif algorithm_name in ("influence", "certified") and algo.model is not None:
                model_for_mia = algo.model
                remaining_ds = dataset.remove_by_ids(set(target_ids))
                post_preds = model_for_mia.predict(remaining_ds.features)
                post_acc = accuracy_score(remaining_ds, post_preds)
            else:
                model_for_mia = ref_model
                post_acc = baseline_acc

            # Classify on full retained set for P/R/F1
            remaining_full = dataset.remove_by_ids(set(target_ids))
            if remaining_full.size > 0:
                preds = model_for_mia.predict(remaining_full.features)
                prf = _precision_recall_f1(preds, remaining_full.labels, int(num_classes))
            else:
                prf = {"precision_macro": 0.0, "recall_macro": 0.0, "f1_macro": 0.0}

            br.accuracy = post_acc
            br.precision_macro = prf["precision_macro"]
            br.recall_macro = prf["recall_macro"]
            br.f1_macro = prf["f1_macro"]

            # MIA
            mia_result = _run_mia(model_for_mia, dataset, target_ids)
            br.mia_success_rate = mia_result["confidence_mia"].get("overall_accuracy", 0.0)
            br.privacy_leakage = mia_result["privacy_leakage"]

            # Algorithm-specific fields
            if algorithm_name == "sisa" and isinstance(algo, SISAUnlearning):
                br.shards_affected = ur.metrics.get("shards_affected", 0)
            elif algorithm_name == "certified" and isinstance(algo, CertifiedRemovalUnlearning):
                br.noise_scale = ur.metrics.get("noise_scale", 0.0)
                br.epsilon = ur.metrics.get("epsilon", 0.0)

        except Exception as exc:
            br.success = False
            br.error = str(exc)

        results.append(br)

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="VeriUnlearn research benchmark runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--datasets", nargs="+",
        choices=list(DATASETS.keys()) + ["all"],
        default=["all"],
        help="Datasets to benchmark (default: all)",
    )
    p.add_argument(
        "--algorithms", nargs="+",
        choices=["sisa", "influence", "certified", "hybrid", "all"],
        default=["all"],
        help="Algorithms to benchmark (default: all)",
    )
    p.add_argument("--num-runs", type=int, default=3,
                    help="Number of runs per algorithm-dataset pair (default: 3)")
    p.add_argument("--num-remove", type=int, default=20,
                    help="Number of samples to unlearn per run (default: 20)")
    p.add_argument("--synthetic", action="store_true",
                    help="Force synthetic data even if datasets library available")
    p.add_argument("--max-samples", type=int, default=None,
                    help="Override max samples per dataset")
    p.add_argument("--output-dir", type=str, default=None,
                    help="Output directory for results")
    p.add_argument("--seed", type=int, default=42, help="Random seed")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    output_dir = Path(args.output_dir) if args.output_dir else (
        _SCRIPT_DIR.parent / "benchmark_results"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    algos = [a for a in args.algorithms if a != "all"] or ["sisa", "influence", "certified", "hybrid"]
    ds_keys = [d for d in args.datasets if d != "all"] or list(DATASETS.keys())

    print(f"VeriUnlearn Benchmark Runner")
    print(f"  Timestamp : {timestamp}")
    print(f"  Datasets  : {ds_keys}")
    print(f"  Algorithms: {algos}")
    print(f"  Runs      : {args.num_runs}")
    print(f"  Remove    : {args.num_remove}")
    print(f"  Output    : {output_dir}")
    print()

    all_results: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []

    for ds_key in ds_keys:
        desc = DATASETS[ds_key]
        size = args.max_samples or SYNTHETIC_SIZES.get(ds_key, 2000)

        print(f"--- Dataset: {desc.name} (n={size}, d={desc.num_features}, c={desc.num_classes}) ---")

        # Try real data first, fall back to synthetic
        dataset = None
        if not args.synthetic:
            dataset = _try_load_real_dataset(desc)
            if dataset is not None:
                print(f"  Loaded real dataset: {desc.name}")
            else:
                print(f"  Real dataset unavailable, using synthetic")
        if dataset is None:
            dataset = generate_benchmark_dataset(desc, size_override=size)
            print(f"  Generated synthetic data: {size} samples")

        for algo_name in algos:
            print(f"  Algorithm: {algo_name} ... ", end="", flush=True)
            algo_results = asyncio.run(
                _benchmark_single(ds_key, dataset, algo_name, args.num_remove, args.num_runs)
            )
            print(f"done ({len(algo_results)} runs)")

            for r in algo_results:
                row = asdict(r)
                row.pop("extra_metrics", None)
                all_results.append(row)

            # Aggregate summary
            successes = [r for r in algo_results if r.success]
            if successes:
                summary_rows.append({
                    "dataset": ds_key,
                    "algorithm": algo_name,
                    **_confidence_interval([r.accuracy for r in successes]),
                    "latency_mean": _confidence_interval([float(r.latency_ms) for r in successes])["mean"],
                    "f1_mean": _confidence_interval([r.f1_macro for r in successes])["mean"],
                    "mia_mean": _confidence_interval([r.mia_success_rate for r in successes])["mean"],
                    "privacy_leakage_mean": _confidence_interval([r.privacy_leakage for r in successes])["mean"],
                    "success_rate": len(successes) / len(algo_results),
                })

    # -----------------------------------------------------------------------
    # Persist results
    # -----------------------------------------------------------------------
    results_path = output_dir / f"benchmark_{timestamp}.json"
    results_path.write_text(json.dumps(all_results, indent=2, default=str), encoding="utf-8")
    print(f"\nRaw results saved: {results_path}")

    summary_path = output_dir / f"benchmark_summary_{timestamp}.json"
    summary_path.write_text(json.dumps(summary_rows, indent=2, default=str), encoding="utf-8")
    print(f"Summary saved:     {summary_path}")

    csv_path = output_dir / f"benchmark_{timestamp}.csv"
    if summary_rows:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=summary_rows[0].keys())
            writer.writeheader()
            writer.writerows(summary_rows)
        print(f"CSV saved:         {csv_path}")

    # Print summary table
    print("\n" + "=" * 80)
    print(f"{'Dataset':<12} {'Algorithm':<14} {'Accuracy':>10} {'F1':>10} {'Latency':>10} {'MIA':>10} {'Privacy':>10}")
    print("-" * 80)
    for row in summary_rows:
        print(
            f"{row['dataset']:<12} {row['algorithm']:<14} "
            f"{row['mean']:>9.4f} {row['f1_mean']:>9.4f} "
            f"{row['latency_mean']:>8.0f}ms {row['mia_mean']:>9.4f} "
            f"{row['privacy_leakage_mean']:>9.4f}"
        )
    print("=" * 80)


if __name__ == "__main__":
    main()
