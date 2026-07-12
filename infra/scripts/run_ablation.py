#!/usr/bin/env python3
"""Ablation study runner for VeriUnlearn.

Systematically varies one hyperparameter at a time and records its effect
on unlearning quality, latency, and privacy. Results are saved as
timestamped JSON for analysis and graphing.
"""
import argparse
import asyncio
import csv
import json
import math
import sys
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
_MLENGINE = _SCRIPT_DIR.parent.parent / "packages" / "ml-engine"
sys.path.insert(0, str(_MLENGINE))

import numpy as np
import torch

from training.data import Dataset, accuracy_score, generate_synthetic_data
from models.single_model import SingleModel
from unlearning.algorithms.sisa import SISAUnlearning
from unlearning.algorithms.influence import InfluenceFunctionUnlearning
from unlearning.algorithms.certified_removal import CertifiedRemovalUnlearning
from unlearning.algorithms.base import UnlearningContext


# ---------------------------------------------------------------------------
# Ablation configurations
# ---------------------------------------------------------------------------

ABLATION_SHARD_COUNTS = [2, 4, 8, 16, 32]
ABLATION_LORA_RANKS = [2, 4, 8, 16, 32, 64]
ABLATION_EPSILONS = [0.01, 0.05, 0.1, 0.5, 1.0, 2.0]
ABLATION_DATASET_SIZES = [100, 200, 500, 1000, 2000, 5000]


@dataclass
class AblationPoint:
    study: str
    parameter: str
    value: Any
    dataset_size: int
    num_features: int
    num_classes: int
    # Metrics
    accuracy: float = 0.0
    utility_retained: float = 0.0
    f1_macro: float = 0.0
    latency_ms: int = 0
    success: bool = False
    error: str = ""
    extra: dict = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _precision_recall_f1(
    preds: torch.Tensor, labels: torch.Tensor, num_classes: int,
) -> float:
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
    return float(np.mean(f1s))


async def _run_sisa_ablation(
    dataset: Dataset, num_shards: int, target_ids: list[str],
) -> AblationPoint:
    ap = AblationPoint(
        study="shard_count",
        parameter="num_shards",
        value=num_shards,
        dataset_size=dataset.size,
        num_features=dataset.features.shape[1],
        num_classes=int(len(dataset.labels.unique())),
    )
    try:
        algo = SISAUnlearning(num_shards=num_shards)
        context = UnlearningContext(
            target_data_ids=target_ids,
            model_type="tabular",
            model_name="ablation_sisa",
            data_size=dataset.size,
            latency_ms=5000,
            accuracy_target=0.95,
            config={
                "input_dim": dataset.features.shape[1],
                "num_classes": int(len(dataset.labels.unique())),
            },
        )
        t0 = time.perf_counter()
        ur = await algo.unlearn(context)
        ap.latency_ms = int((time.perf_counter() - t0) * 1000)
        ap.success = ur.success
        ap.utility_retained = ur.utility_retained
        ap.extra = ur.metrics

        if algo.model is not None:
            remaining = dataset.remove_by_ids(set(target_ids))
            preds = algo.model.predict(remaining.features)
            ap.accuracy = accuracy_score(remaining, preds)
            ap.f1_macro = _precision_recall_f1(
                preds, remaining.labels, int(len(dataset.labels.unique())),
            )
    except Exception as e:
        ap.error = str(e)
    return ap


async def _run_lora_rank_ablation(
    dataset: Dataset, rank: int, target_ids: list[str],
) -> AblationPoint:
    """Test LoRA rank impact by varying hidden_dim (proxy for rank) in SingleModel."""
    ap = AblationPoint(
        study="lora_rank",
        parameter="lora_rank",
        value=rank,
        dataset_size=dataset.size,
        num_features=dataset.features.shape[1],
        num_classes=int(len(dataset.labels.unique())),
    )
    try:
        hidden = max(rank * 4, 16)
        model = SingleModel(
            input_dim=dataset.features.shape[1],
            hidden_dim=hidden,
            num_classes=int(len(dataset.labels.unique())),
        )
        remaining = dataset.remove_by_ids(set(target_ids))
        if remaining.size > 0:
            t0 = time.perf_counter()
            model.train(remaining.features, remaining.labels, epochs=30)
            ap.latency_ms = int((time.perf_counter() - t0) * 1000)
            preds = model.predict(remaining.features)
            ap.accuracy = accuracy_score(remaining, preds)
            ap.f1_macro = _precision_recall_f1(
                preds, remaining.labels, int(len(dataset.labels.unique())),
            )
            ap.success = True
        ap.extra = {"hidden_dim": hidden, "approximate_params": hidden * hidden * 3}
    except Exception as e:
        ap.error = str(e)
    return ap


async def _run_epsilon_ablation(
    dataset: Dataset, epsilon: float, target_ids: list[str],
) -> AblationPoint:
    ap = AblationPoint(
        study="epsilon",
        parameter="epsilon",
        value=epsilon,
        dataset_size=dataset.size,
        num_features=dataset.features.shape[1],
        num_classes=int(len(dataset.labels.unique())),
    )
    try:
        algo = CertifiedRemovalUnlearning(epsilon=epsilon, delta=1e-5)
        context = UnlearningContext(
            target_data_ids=target_ids,
            model_type="tabular",
            model_name="ablation_cert",
            data_size=dataset.size,
            latency_ms=5000,
            accuracy_target=0.95,
            config={
                "input_dim": dataset.features.shape[1],
                "num_classes": int(len(dataset.labels.unique())),
            },
        )
        t0 = time.perf_counter()
        ur = await algo.unlearn(context)
        ap.latency_ms = int((time.perf_counter() - t0) * 1000)
        ap.success = ur.success
        ap.utility_retained = ur.utility_retained
        ap.extra = ur.metrics

        if algo.model is not None:
            remaining = dataset.remove_by_ids(set(target_ids))
            preds = algo.model.predict(remaining.features)
            ap.accuracy = accuracy_score(remaining, preds)
            ap.f1_macro = _precision_recall_f1(
                preds, remaining.labels, int(len(dataset.labels.unique())),
            )
    except Exception as e:
        ap.error = str(e)
    return ap


async def _run_dataset_size_ablation(
    size: int, num_features: int, num_classes: int, target_ids_count: int,
) -> list[AblationPoint]:
    """Test all algorithms at a given dataset size."""
    dataset = generate_synthetic_data(
        num_samples=size,
        num_features=num_features,
        num_classes=num_classes,
        seed=42,
    )
    target_ids = dataset.data_ids[:target_ids_count]

    results = []

    # SISA
    try:
        ap = await _run_sisa_ablation(dataset, num_shards=10, target_ids=target_ids)
        ap.study = "dataset_size"
        ap.parameter = "dataset_size"
        ap.value = size
        results.append(ap)
    except Exception as e:
        results.append(AblationPoint(
            study="dataset_size", parameter="dataset_size", value=size,
            dataset_size=size, num_features=num_features, num_classes=num_classes,
            error=str(e),
        ))

    # Influence
    try:
        algo = InfluenceFunctionUnlearning(damping=1e-3)
        context = UnlearningContext(
            target_data_ids=target_ids,
            model_type="tabular",
            model_name="ablation_inf",
            data_size=size,
            latency_ms=5000,
            accuracy_target=0.95,
            config={"input_dim": num_features, "num_classes": num_classes},
        )
        t0 = time.perf_counter()
        ur = await algo.unlearn(context)
        latency = int((time.perf_counter() - t0) * 1000)
        ap = AblationPoint(
            study="dataset_size", parameter="dataset_size", value=size,
            dataset_size=size, num_features=num_features, num_classes=num_classes,
            latency_ms=latency, success=ur.success, utility_retained=ur.utility_retained,
            extra={"algorithm": "influence"},
        )
        if algo.model is not None:
            remaining = dataset.remove_by_ids(set(target_ids))
            preds = algo.model.predict(remaining.features)
            ap.accuracy = accuracy_score(remaining, preds)
            ap.f1_macro = _precision_recall_f1(preds, remaining.labels, num_classes)
        results.append(ap)
    except Exception as e:
        results.append(AblationPoint(
            study="dataset_size", parameter="dataset_size", value=size,
            dataset_size=size, num_features=num_features, num_classes=num_classes,
            extra={"algorithm": "influence"}, error=str(e),
        ))

    # Certified
    try:
        ap = await _run_epsilon_ablation(dataset, epsilon=0.1, target_ids=target_ids)
        ap.study = "dataset_size"
        ap.parameter = "dataset_size"
        ap.value = size
        ap.extra["algorithm"] = "certified"
        results.append(ap)
    except Exception as e:
        results.append(AblationPoint(
            study="dataset_size", parameter="dataset_size", value=size,
            dataset_size=size, num_features=num_features, num_classes=num_classes,
            extra={"algorithm": "certified"}, error=str(e),
        ))

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="VeriUnlearn ablation study runner")
    p.add_argument(
        "--studies", nargs="+",
        choices=["shard_count", "lora_rank", "epsilon", "dataset_size", "all"],
        default=["all"],
        help="Which ablation studies to run (default: all)",
    )
    p.add_argument("--dataset-size", type=int, default=1000,
                    help="Base dataset size for studies that hold size fixed (default: 1000)")
    p.add_argument("--num-features", type=int, default=20)
    p.add_argument("--num-classes", type=int, default=2)
    p.add_argument("--num-remove", type=int, default=20)
    p.add_argument("--output-dir", type=str, default=None)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def main() -> None:
    args = parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    output_dir = Path(args.output_dir) if args.output_dir else (
        _SCRIPT_DIR.parent / "benchmark_results" / "ablation"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    studies = [s for s in args.studies if s != "all"] or [
        "shard_count", "lora_rank", "epsilon", "dataset_size",
    ]

    print(f"VeriUnlearn Ablation Study Runner")
    print(f"  Timestamp : {timestamp}")
    print(f"  Studies   : {studies}")
    print(f"  Dataset   : {args.dataset_size} samples, {args.num_features} features, {args.num_classes} classes")
    print(f"  Output    : {output_dir}")
    print()

    all_points: list[dict[str, Any]] = []

    # ----- Study 1: Shard count impact on SISA -----
    if "shard_count" in studies:
        print("--- Ablation: Shard Count (SISA) ---")
        dataset = generate_synthetic_data(
            num_samples=args.dataset_size,
            num_features=args.num_features,
            num_classes=args.num_classes,
            seed=args.seed,
        )
        target_ids = dataset.data_ids[:args.num_remove]

        for n_shards in ABLATION_SHARD_COUNTS:
            print(f"  num_shards={n_shards:3d} ... ", end="", flush=True)
            ap = asyncio.run(_run_sisa_ablation(dataset, n_shards, target_ids))
            all_points.append(asdict(ap))
            status = "OK" if ap.success else f"FAIL: {ap.error}"
            print(f"{status}  latency={ap.latency_ms}ms  acc={ap.accuracy:.4f}")

    # ----- Study 2: LoRA rank impact -----
    if "lora_rank" in studies:
        print("\n--- Ablation: LoRA Rank ---")
        dataset = generate_synthetic_data(
            num_samples=args.dataset_size,
            num_features=args.num_features,
            num_classes=args.num_classes,
            seed=args.seed,
        )
        target_ids = dataset.data_ids[:args.num_remove]

        for rank in ABLATION_LORA_RANKS:
            print(f"  rank={rank:3d} ... ", end="", flush=True)
            ap = asyncio.run(_run_lora_rank_ablation(dataset, rank, target_ids))
            all_points.append(asdict(ap))
            status = "OK" if ap.success else f"FAIL: {ap.error}"
            print(f"{status}  latency={ap.latency_ms}ms  acc={ap.accuracy:.4f}")

    # ----- Study 3: Epsilon impact on Certified Removal -----
    if "epsilon" in studies:
        print("\n--- Ablation: Epsilon (Certified Removal) ---")
        dataset = generate_synthetic_data(
            num_samples=args.dataset_size,
            num_features=args.num_features,
            num_classes=args.num_classes,
            seed=args.seed,
        )
        target_ids = dataset.data_ids[:args.num_remove]

        for eps in ABLATION_EPSILONS:
            print(f"  epsilon={eps:.3f} ... ", end="", flush=True)
            ap = asyncio.run(_run_epsilon_ablation(dataset, eps, target_ids))
            all_points.append(asdict(ap))
            status = "OK" if ap.success else f"FAIL: {ap.error}"
            print(f"{status}  latency={ap.latency_ms}ms  acc={ap.accuracy:.4f}  noise={ap.extra.get('noise_scale', 0):.6f}")

    # ----- Study 4: Dataset size impact on all algorithms -----
    if "dataset_size" in studies:
        print("\n--- Ablation: Dataset Size (All Algorithms) ---")
        target_count = min(args.num_remove, 10)

        for size in ABLATION_DATASET_SIZES:
            print(f"  size={size:5d} ... ", end="", flush=True)
            pts = asyncio.run(_run_dataset_size_ablation(
                size, args.num_features, args.num_classes, target_count,
            ))
            for pt in pts:
                all_points.append(asdict(pt))
            algos_done = [pt.get("extra", {}).get("algorithm", "sisa") for pt in [asdict(p) for p in pts]]
            print(f"done ({len(pts)} algorithms)")

    # -----------------------------------------------------------------------
    # Persist
    # -----------------------------------------------------------------------
    json_path = output_dir / f"ablation_{timestamp}.json"
    json_path.write_text(json.dumps(all_points, indent=2, default=str), encoding="utf-8")
    print(f"\nResults saved: {json_path}")

    # Per-study CSV
    for study in studies:
        study_points = [p for p in all_points if p["study"] == study]
        if study_points:
            csv_path = output_dir / f"ablation_{study}_{timestamp}.csv"
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=study_points[0].keys())
                writer.writeheader()
                writer.writerows(study_points)
            print(f"  CSV: {csv_path.name}")

    # Print summary table
    print("\n" + "=" * 90)
    print(f"{'Study':<16} {'Parameter':<16} {'Value':>8} {'Accuracy':>10} {'F1':>10} {'Latency':>10} {'Success':>8}")
    print("-" * 90)
    for p in all_points:
        print(
            f"{p['study']:<16} {p['parameter']:<16} {str(p['value']):>8} "
            f"{p['accuracy']:>9.4f} {p['f1_macro']:>9.4f} "
            f"{p['latency_ms']:>8}ms {'Y' if p['success'] else 'N':>7}"
        )
    print("=" * 90)


if __name__ == "__main__":
    main()
