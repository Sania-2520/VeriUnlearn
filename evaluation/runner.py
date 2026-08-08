"""Experiment runner — orchestrates the full VeriUnlearn benchmark pipeline.

Integrates with the existing evaluation modules:
- ``evaluation.data_loading`` for loading & splitting
- ``evaluation.algorithms`` for unlearning strategies
- ``evaluation.metrics`` for MetricsComputer and per-metric functions
"""
from __future__ import annotations

import gc
import json
import logging
import os
import random
import sys
import time
import traceback
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Sized, cast

import numpy as np
import torch

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Imports from sibling evaluation modules
# ---------------------------------------------------------------------------

try:
    from evaluation.config import (
        DatasetConfig,
        ExperimentConfig,
        OutputConfig,
        SeedConfig,
        TrainingConfig,
        UnlearningConfig,
        get_git_info,
        get_hardware_info,
        get_package_versions,
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from evaluation.config import (
        DatasetConfig,
        ExperimentConfig,
        OutputConfig,
        SeedConfig,
        TrainingConfig,
        UnlearningConfig,
        get_git_info,
        get_hardware_info,
        get_package_versions,
    )

try:
    from evaluation.data_loading import (
        DatasetBundle,
        create_forget_set,
        load_dataset,
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from evaluation.data_loading import (
        DatasetBundle,
        create_forget_set,
        load_dataset,
    )

try:
    from evaluation.algorithms import (
        EvalDataset,
        _ShardedEnsemble,
        get_algorithm,
        list_algorithms,
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from evaluation.algorithms import (
        EvalDataset,
        _ShardedEnsemble,
        get_algorithm,
        list_algorithms,
    )

try:
    from evaluation.metrics import (
        compute_confusion_matrix,
        compute_efficiency_metrics,
        compute_forget_quality,
        compute_losses,
        compute_pr_curve,
        compute_privacy_metrics,
        compute_roc_curve,
        compute_trust_score,
        compute_utility_metrics,
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from evaluation.metrics import (
        compute_confusion_matrix,
        compute_efficiency_metrics,
        compute_forget_quality,
        compute_losses,
        compute_pr_curve,
        compute_privacy_metrics,
        compute_roc_curve,
        compute_trust_score,
        compute_utility_metrics,
    )


# ---------------------------------------------------------------------------
# DatasetBundle → EvalDataset bridge
# ---------------------------------------------------------------------------

def _sample_to_xy(sample):
    """Normalise a dataset sample (tuple or tokeniser dict) into (x, y)."""
    if isinstance(sample, dict):
        x = sample.get("input_ids", sample.get("image"))
        y = sample.get("label", sample.get("labels"))
        if y is None and "input_ids" in sample:
            y = sample.get("label")
        return x, y
    return sample


def _bundle_to_numpy(bundle: DatasetBundle) -> tuple[np.ndarray, np.ndarray]:
    """Extract flat numpy arrays from a torch Dataset inside a DatasetBundle."""
    xs: list[np.ndarray] = []
    ys: list[int] = []
    # torch's ``Dataset`` stub does not expose ``__len__``; cast to Sized for
    # the length checks (all concrete datasets implement ``__len__``).
    n_train = len(cast(Sized, bundle.train))
    for i in range(n_train):
        x, y = _sample_to_xy(bundle.train[i])
        if x is None or y is None:
            continue
        if isinstance(x, torch.Tensor):
            xs.append(x.numpy().reshape(-1))
        else:
            xs.append(np.asarray(x).reshape(-1))
        ys.append(int(y) if not isinstance(y, (int, np.integer)) else int(y))
    if not xs:
        return np.empty((0, 1), dtype=np.float32), np.empty(0, dtype=np.int64)
    return np.stack(xs).astype(np.float32), np.array(ys, dtype=np.int64)


def _bundle_test_to_numpy(bundle: DatasetBundle) -> tuple[np.ndarray, np.ndarray]:
    """Extract flat numpy arrays from the test split."""
    xs: list[np.ndarray] = []
    ys: list[int] = []
    n_test = len(cast(Sized, bundle.test))
    for i in range(n_test):
        x, y = _sample_to_xy(bundle.test[i])
        if x is None or y is None:
            continue
        if isinstance(x, torch.Tensor):
            xs.append(x.numpy().reshape(-1))
        else:
            xs.append(np.asarray(x).reshape(-1))
        ys.append(int(y) if not isinstance(y, (int, np.integer)) else int(y))
    if not xs:
        return np.empty((0, 1), dtype=np.float32), np.empty(0, dtype=np.int64)
    return np.stack(xs).astype(np.float32), np.array(ys, dtype=np.int64)


def _subset_to_numpy(dataset, max_n: int | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Extract numpy arrays from a torch Subset (or any Dataset)."""
    xs: list[np.ndarray] = []
    ys: list[int] = []
    n = len(dataset)
    if max_n is not None:
        n = min(n, max_n)
    for i in range(n):
        x, y = _sample_to_xy(dataset[i])
        if x is None or y is None:
            continue
        if isinstance(x, torch.Tensor):
            xs.append(x.numpy().reshape(-1))
        else:
            xs.append(np.asarray(x).reshape(-1))
        ys.append(int(y) if not isinstance(y, (int, np.integer)) else int(y))
    if not xs:
        return np.empty((0, 1), dtype=np.float32), np.empty(0, dtype=np.int64)
    return np.stack(xs).astype(np.float32), np.array(ys, dtype=np.int64)


def _bundle_to_eval_dataset(
    bundle: DatasetBundle,
    forget_ratio: float,
    seed: int,
) -> tuple[EvalDataset, np.ndarray, np.ndarray]:
    """Convert a DatasetBundle into an EvalDataset + forget/retain index arrays.

    Returns
    -------
    eval_dataset : EvalDataset
    forget_indices : np.ndarray
    retain_indices : np.ndarray
    """
    is_text = bundle.name in ("imdb", "ag_news")
    is_image = bundle.name in ("mnist", "cifar10")

    train_x, train_y = _bundle_to_numpy(bundle)
    test_x, test_y = _bundle_test_to_numpy(bundle)

    texts_train = None
    texts_test = None
    if is_text and bundle.tokenizer is not None:
        texts_train = _extract_texts(bundle.train)
        texts_test = _extract_texts(bundle.test)

    n_total = len(train_y)
    n_forget = max(1, int(n_total * forget_ratio))
    rng = np.random.RandomState(seed)
    forget_indices = np.sort(rng.choice(n_total, size=n_forget, replace=False))
    forget_set = set(forget_indices.tolist())
    retain_indices = np.array([i for i in range(n_total) if i not in forget_set], dtype=np.int64)

    return EvalDataset(
        X=train_x,
        y=train_y,
        X_test=test_x,
        y_test=test_y,
        dataset_name=bundle.name,
        is_text=is_text,
        is_image=is_image,
        texts=texts_train,
        texts_test=texts_test,
    ), forget_indices, retain_indices


def _extract_texts(dataset) -> list[str]:
    """Pull raw text strings from a _TextClassificationDataset."""
    if hasattr(dataset, "_texts"):
        return list(dataset._texts)
    if hasattr(dataset, "dataset") and hasattr(dataset.dataset, "_texts"):
        return [dataset.dataset._texts[i] for i in dataset.indices]
    texts: list[str] = []
    for i in range(len(dataset)):
        sample = dataset[i]
        if isinstance(sample, dict) and "input_ids" in sample:
            break
        texts.append(str(sample))
    return texts


# ---------------------------------------------------------------------------
# Memory tracking
# ---------------------------------------------------------------------------

def _get_peak_memory_mb() -> float:
    if torch.cuda.is_available():
        return torch.cuda.max_memory_allocated() / (1024 * 1024)
    try:
        import tracemalloc
        if tracemalloc.is_tracing():
            _, peak = tracemalloc.get_traced_memory()
            return peak / (1024 * 1024)
    except Exception:
        logger.debug("tracemalloc not available for memory tracking")
    try:
        import resource  # type: ignore[import-not-found]  # POSIX-only module
        usage = resource.getrusage(resource.RUSAGE_SELF)  # type: ignore[attr-defined]
        return float(usage.ru_maxrss) / 1024
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Membership inference attack (threshold-based on loss distribution)
# ---------------------------------------------------------------------------

def _membership_inference_attack(
    estimator: Any,
    X_member: np.ndarray,
    y_member: np.ndarray,
    X_nonmember: np.ndarray,
    y_nonmember: np.ndarray,
    n_samples: int = 500,
    is_text: bool = False,
    vectorizer: Any = None,
    scaler: Any = None,
) -> float:
    """Threshold-based MIA on the cross-entropy loss distribution.

    Members (training data) should have lower loss than non-members (test data).
    The attack accuracy measures how well we can distinguish them.
    """
    if len(y_member) == 0 or len(y_nonmember) == 0:
        return 0.5

    n_m = min(n_samples, len(y_member))
    n_nm = min(n_samples, len(y_nonmember))

    try:
        member_losses = compute_losses(estimator, X_member[:n_m], y_member[:n_m])
        nonmember_losses = compute_losses(estimator, X_nonmember[:n_nm], y_nonmember[:n_nm])
    except Exception:
        return 0.5

    if len(member_losses) == 0 or len(nonmember_losses) == 0:
        return 0.5

    all_losses = np.concatenate([member_losses, nonmember_losses])
    threshold = float(np.percentile(all_losses, 50.0))

    member_correct = float(np.mean(member_losses <= threshold))
    nonmember_correct = float(np.mean(nonmember_losses > threshold))
    return (member_correct + nonmember_correct) / 2.0


def _compute_mia_curves(
    estimator: Any,
    X_member: np.ndarray,
    y_member: np.ndarray,
    X_nonmember: np.ndarray,
    y_nonmember: np.ndarray,
    n_samples: int = 500,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Compute ROC and PR curves for MIA."""
    n_m = min(n_samples, len(y_member))
    n_nm = min(n_samples, len(y_nonmember))

    try:
        member_losses = compute_losses(estimator, X_member[:n_m], y_member[:n_m])
        nonmember_losses = compute_losses(estimator, X_nonmember[:n_nm], y_nonmember[:n_nm])
    except Exception:
        return {}, {}

    if len(member_losses) == 0 or len(nonmember_losses) == 0:
        return {}, {}

    all_losses = np.concatenate([member_losses, nonmember_losses])
    labels = np.concatenate([
        np.ones(len(member_losses), dtype=int),
        np.zeros(len(nonmember_losses), dtype=int),
    ])
    scores = -all_losses

    roc = compute_roc_curve(labels, scores)
    pr = compute_pr_curve(labels, scores)
    return roc, pr


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class RunResult:
    algorithm: str
    dataset: str
    forget_ratio: float
    run_id: int
    seed: int
    # Before unlearning
    accuracy_before: float = 0.0
    precision_before: float = 0.0
    recall_before: float = 0.0
    f1_before: float = 0.0
    # After unlearning
    accuracy_after: float = 0.0
    precision_after: float = 0.0
    recall_after: float = 0.0
    f1_after: float = 0.0
    # Forget quality
    forget_accuracy: float = 0.0
    memorization_score: float = 0.0
    # Privacy
    mia_success_before: float = 0.0
    mia_success_after: float = 0.0
    privacy_leakage: float = 0.0
    # Efficiency
    training_time: float = 0.0
    unlearning_time: float = 0.0
    speedup: float = 0.0
    memory_peak_mb: float = 0.0
    # Trust
    trust_score: float = 0.0
    utility_loss: float = 0.0
    knowledge_retention: float = 0.0
    # Raw data
    confusion_matrix_before: list = field(default_factory=list)
    confusion_matrix_after: list = field(default_factory=list)
    roc_curve_before: dict = field(default_factory=dict)
    roc_curve_after: dict = field(default_factory=dict)
    pr_curve_before: dict = field(default_factory=dict)
    pr_curve_after: dict = field(default_factory=dict)
    elapsed_seconds: float = 0.0
    error: str | None = None


@dataclass
class ExperimentResults:
    config: ExperimentConfig
    runs: list[RunResult]
    summary: dict
    hardware_info: dict
    git_info: dict
    package_versions: dict
    timestamp: str

    def save(self, output_dir: str) -> None:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        with open(path / "results.json", "w") as f:
            json.dump(asdict(self), f, indent=2, default=str)
        with open(path / "runs.json", "w") as f:
            json.dump([asdict(r) for r in self.runs], f, indent=2, default=str)
        with open(path / "summary.json", "w") as f:
            json.dump(self.summary, f, indent=2, default=str)
        logger.info("Results saved to %s", path)

    # Metric fields extracted from the flat RunResult into the exporter model.
    _EXPORT_METRIC_MAP = (
        ("accuracy_before", "accuracy_before"),
        ("accuracy_after", "accuracy_after"),
        ("f1_after", "f1_after"),
        ("forget_accuracy", "forget_accuracy"),
        ("memorization_score", "memorization_score"),
        ("mia_success_before", "mia_success_before"),
        ("mia_success_after", "mia_success_after"),
        ("privacy_leakage", "privacy_leakage"),
        ("utility_loss", "utility_loss"),
        ("knowledge_retention", "knowledge_retention"),
        ("trust_score", "trust_score"),
        ("training_time", "training_time"),
        ("unlearning_time", "unlearning_time"),
        ("speedup", "speedup"),
        ("memory_peak_mb", "memory_peak_mb"),
    )

    def to_export_model(self):
        """Convert to :class:`evaluation.export.ExperimentResults`.

        The runner produces a richly-typed flat ``RunResult`` while the
        exporter/report/visualiser expect the ``export`` package's lighter
        ``ExperimentResults`` (which aggregates per-metric ``metrics`` dicts).
        This adapter bridges the two without duplicating the exporter code.
        """
        from evaluation.export import ExperimentResults as ExportResults
        from evaluation.export import RunResult as ExportRunResult

        metric_names = [dst for _src, dst in self._EXPORT_METRIC_MAP]
        algorithm_names = sorted({r.algorithm for r in self.runs})
        dataset_names = sorted({r.dataset for r in self.runs})

        export_runs = []
        for r in self.runs:
            metrics = {}
            for src, dst in self._EXPORT_METRIC_MAP:
                val = getattr(r, src, None)
                if val is not None:
                    metrics[dst] = float(val) if isinstance(val, (int, float)) else val
            timing = {
                "training_time": float(getattr(r, "training_time", 0.0) or 0.0),
                "unlearning_time": float(getattr(r, "unlearning_time", 0.0) or 0.0),
                "speedup": float(getattr(r, "speedup", 0.0) or 0.0),
                "memory_peak_mb": float(getattr(r, "memory_peak_mb", 0.0) or 0.0),
                "elapsed_seconds": float(getattr(r, "elapsed_seconds", 0.0) or 0.0),
            }
            export_runs.append(
                ExportRunResult(
                    run_id=getattr(r, "run_id", 0),
                    algorithm=r.algorithm,
                    dataset=r.dataset,
                    forget_ratio=float(getattr(r, "forget_ratio", 0.0)),
                    seed=getattr(r, "seed", 0),
                    metrics=metrics,
                    timing=timing,
                    success=(getattr(r, "error", None) in (None, "")),
                    error=getattr(r, "error", "") or "",
                    # Curve/confusion payloads flow through to the visualizer.
                    roc_curve_before=getattr(r, "roc_curve_before", {}) or {},
                    roc_curve_after=getattr(r, "roc_curve_after", {}) or {},
                    pr_curve_before=getattr(r, "pr_curve_before", {}) or {},
                    pr_curve_after=getattr(r, "pr_curve_after", {}) or {},
                    confusion_matrix_before=getattr(r, "confusion_matrix_before", []) or [],
                    confusion_matrix_after=getattr(r, "confusion_matrix_after", []) or [],
                )
            )

        return ExportResults(
            config=asdict(self.config) if hasattr(self.config, "__dict__") else dict(self.config),
            algorithm_names=algorithm_names,
            dataset_names=dataset_names,
            metric_names=metric_names,
            runs=export_runs,
        )


# ---------------------------------------------------------------------------
# ExperimentRunner
# ---------------------------------------------------------------------------

class ExperimentRunner:
    """Orchestrate reproducible benchmark experiments."""

    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config
        self.output_dir = Path(config.output.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._checkpoint_path = self.output_dir / ".checkpoint.json"
        self._completed: set[str] = self._load_checkpoint()

    def _load_checkpoint(self) -> set[str]:
        if self._checkpoint_path.exists():
            try:
                data = json.loads(self._checkpoint_path.read_text())
                return set(data.get("completed", []))
            except Exception:
                return set()
        return set()

    def _save_checkpoint(self, completed: set[str]) -> None:
        self._checkpoint_path.write_text(json.dumps({"completed": sorted(completed)}))

    def _make_run_key(self, algo: str, ds: str, fr: float, run_id: int) -> str:
        return f"{algo}|{ds}|{fr}|{run_id}"

    # ------------------------------------------------------------------
    # Seed
    # ------------------------------------------------------------------

    def _apply_seed(self, seed: int) -> None:
        os.environ["PYTHONHASHSEED"] = str(seed)
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False

    # ------------------------------------------------------------------
    # run_all
    # ------------------------------------------------------------------

    def run_all(self) -> ExperimentResults:
        """Run the complete benchmark suite."""
        logger.info("=" * 70)
        logger.info("VeriUnlearn Benchmark — Starting full experiment suite")
        logger.info("Available algorithms: %s", list_algorithms())
        logger.info("=" * 70)
        all_runs: list[RunResult] = []
        total = 0
        for ds_cfg in self.config.datasets:
            for algo in self.config.unlearning.algorithms:
                for fr in self.config.unlearning.forget_ratios:
                    for run_id in range(self.config.unlearning.num_runs):
                        total += 1
        completed_count = 0
        for ds_cfg in self.config.datasets:
            for algo in self.config.unlearning.algorithms:
                for fr in self.config.unlearning.forget_ratios:
                    for run_id in range(self.config.unlearning.num_runs):
                        completed_count += 1
                        key = self._make_run_key(algo, ds_cfg.name, fr, run_id)
                        if key in self._completed:
                            logger.info(
                                "[%d/%d] SKIP (cached): %s / %s / fr=%.2f / run=%d",
                                completed_count, total, algo, ds_cfg.name, fr, run_id,
                            )
                            cached = self._load_cached_result(key)
                            if cached is not None:
                                all_runs.append(cached)
                            continue
                        seed = self.config.unlearning.seed_start + run_id
                        logger.info(
                            "[%d/%d] Running: %s / %s / fr=%.2f / run=%d (seed=%d)",
                            completed_count, total, algo, ds_cfg.name, fr, run_id, seed,
                        )
                        try:
                            result = self.run_single(algo, ds_cfg, fr, run_id, seed)
                            all_runs.append(result)
                            self._completed.add(key)
                            self._save_checkpoint(self._completed)
                            self._persist_run_result(key, result)
                        except Exception as exc:
                            logger.error(
                                "FAILED: %s / %s / fr=%.2f / run=%d — %s",
                                algo, ds_cfg.name, fr, run_id, exc,
                            )
                            traceback.print_exc()
                            fail_result = RunResult(
                                algorithm=algo,
                                dataset=ds_cfg.name,
                                forget_ratio=fr,
                                run_id=run_id,
                                seed=seed,
                                error=str(exc),
                            )
                            all_runs.append(fail_result)
                            self._completed.add(key)
                            self._save_checkpoint(self._completed)

        summary = self._compute_summary(all_runs)
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
        results = ExperimentResults(
            config=self.config,
            runs=all_runs,
            summary=summary,
            hardware_info=get_hardware_info(),
            git_info=get_git_info(),
            package_versions=get_package_versions(),
            timestamp=timestamp,
        )
        results.save(str(self.output_dir))
        logger.info("=" * 70)
        logger.info(
            "Benchmark complete — %d runs, %d succeeded, %d failed",
            len(all_runs),
            sum(1 for r in all_runs if r.error is None),
            sum(1 for r in all_runs if r.error is not None),
        )
        logger.info("=" * 70)
        return results

    # ------------------------------------------------------------------
    # run_single
    # ------------------------------------------------------------------

    def run_single(
        self,
        algorithm: str,
        dataset_cfg: DatasetConfig,
        forget_ratio: float,
        run_id: int,
        seed: int | None = None,
    ) -> RunResult:
        """Run a single experiment configuration."""
        if seed is None:
            seed = self.config.unlearning.seed_start + run_id
        t_start = time.perf_counter()
        self._apply_seed(seed)
        seed_cfg = SeedConfig(global_seed=seed, numpy_seed=seed, torch_seed=seed, cuda_seed=seed, python_hash_seed=seed)

        # --- 1. Load dataset ------------------------------------------------
        logger.info("  Loading dataset '%s' ...", dataset_cfg.name)
        bundle = load_dataset(dataset_cfg, seed_cfg=seed_cfg)

        # --- 2. Create forget set -------------------------------------------
        bundle = create_forget_set(bundle, forget_ratio=forget_ratio, seed=seed)

        # --- 3. Convert to EvalDataset for algorithm -------------------------
        eval_ds, forget_indices, retain_indices = _bundle_to_eval_dataset(
            bundle, forget_ratio=forget_ratio, seed=seed,
        )
        num_classes = int(eval_ds.y.max()) + 1

        # --- 4. Create algorithm --------------------------------------------
        algo = get_algorithm(algorithm)

        # --- 5. Train baseline ----------------------------------------------
        logger.info("  Training baseline with '%s' ...", algo.name)
        t_train_start = time.perf_counter()
        trained = algo.fit(eval_ds, seed=seed)
        training_time = time.perf_counter() - t_train_start

        # --- 6. Evaluate baseline -------------------------------------------
        logger.info("  Evaluating baseline ...")
        before_metrics = algo.evaluate(trained, eval_ds)

        # Compute confusion matrix before
        test_preds_before = trained.estimator.predict(
            _transform_for_algo(trained, eval_ds, "test")
        )
        cm_before = compute_confusion_matrix(eval_ds.y_test, test_preds_before, num_classes)

        # --- 7. Run MIA before unlearning -----------------------------------
        logger.info("  Running MIA before unlearning ...")
        mia_before_acc, roc_before, pr_before = self._run_mia(
            trained, eval_ds, seed,
        )

        # --- 8. Run unlearning algorithm ------------------------------------
        logger.info("  Running unlearning algorithm '%s' ...", algo.name)
        t_unlearn_start = time.perf_counter()
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        gc.collect()

        unlearned = algo.unlearn(
            trained,
            forget_indices,
            retain_indices,
            eval_ds,
            seed=seed,
        )
        unlearning_time = time.perf_counter() - t_unlearn_start
        memory_peak = _get_peak_memory_mb()

        # --- 9. Evaluate unlearned model ------------------------------------
        logger.info("  Evaluating unlearned model ...")
        after_metrics = algo.evaluate(unlearned, eval_ds)

        test_preds_after = _predict_for_algo(unlearned, eval_ds, "test")
        cm_after = compute_confusion_matrix(eval_ds.y_test, test_preds_after, num_classes)

        # --- 10. Run MIA after unlearning -----------------------------------
        logger.info("  Running MIA after unlearning ...")
        mia_after_acc, roc_after, pr_after = self._run_mia(
            unlearned, eval_ds, seed,
        )

        # --- 11. Compute differential & composite metrics ------------------
        # Forget quality: evaluate on forget set before and after
        forget_preds_before = trained.estimator.predict(
            _transform_for_algo(trained, eval_ds, "forget", forget_indices)
        )
        forget_preds_after = _predict_for_algo(unlearned, eval_ds, "forget", forget_indices)

        forget_labels = eval_ds.y[forget_indices]
        forget_acc_before = float(np.mean(forget_preds_before == forget_labels)) if len(forget_labels) > 0 else 0.0
        forget_acc_after = float(np.mean(forget_preds_after == forget_labels)) if len(forget_labels) > 0 else 0.0

        # Compute member/non-member losses for memorization score
        try:
            member_losses = compute_losses(
                _get_estimator(trained), _transform_for_algo(trained, eval_ds, "train_subsample"),
                eval_ds.y[:min(200, len(eval_ds.y))],
            )
            nonmember_losses = compute_losses(
                _get_estimator(trained), _transform_for_algo(trained, eval_ds, "test_subsample"),
                eval_ds.y_test[:min(200, len(eval_ds.y_test))],
            )
            forget_quality = compute_forget_quality(
                forget_acc_before, forget_acc_after, member_losses, nonmember_losses,
            )
        except Exception:
            forget_quality = compute_forget_quality(
                forget_acc_before, forget_acc_after, np.array([]), np.array([]),
            )

        # Utility metrics
        acc_before_test = before_metrics.get("accuracy", 0.0)
        acc_after_test = after_metrics.get("accuracy", 0.0)
        utility = compute_utility_metrics(
            accuracy_before_test=acc_before_test,
            accuracy_after_test=acc_after_test,
            accuracy_before_retain=acc_before_test,
            accuracy_after_retain=acc_after_test,
        )

        # Privacy metrics
        try:
            member_losses_unlearned = compute_losses(
                _get_estimator(unlearned),
                _transform_for_algo(unlearned, eval_ds, "train_subsample"),
                eval_ds.y[:min(200, len(eval_ds.y))],
            )
            nonmember_losses_unlearned = compute_losses(
                _get_estimator(unlearned),
                _transform_for_algo(unlearned, eval_ds, "test_subsample"),
                eval_ds.y_test[:min(200, len(eval_ds.y_test))],
            )
            privacy = compute_privacy_metrics(member_losses_unlearned, nonmember_losses_unlearned)
        except Exception:
            privacy = compute_privacy_metrics(np.array([]), np.array([]))

        # Efficiency metrics
        efficiency = compute_efficiency_metrics(
            training_time_s=training_time,
            unlearning_time_s=unlearning_time,
            retraining_time_s=training_time,
            peak_memory_mb=memory_peak,
        )

        # Trust score
        forget_drop = forget_quality.get("forget_drop", 0.0)
        kr = utility.get("knowledge_retention", 1.0)
        pl = privacy.get("privacy_leakage_score", 0.5)
        sp = efficiency.get("speedup_vs_retrain", 1.0)
        trust = compute_trust_score(
            forget_drop=forget_drop,
            knowledge_retention=kr,
            privacy_leakage_score=pl,
            speedup_vs_retrain=sp,
        )

        # Speedup
        speedup = efficiency.get("speedup_vs_retrain", 1.0)
        memorization_score = forget_quality.get("memorization_score", 0.0)
        trust_score_val = trust.get("trust_score", 0.0)
        utility_loss = utility.get("utility_loss", 0.0)
        knowledge_retention = utility.get("knowledge_retention", 1.0)
        privacy_leakage = privacy.get("privacy_leakage_score", 0.5)

        elapsed = time.perf_counter() - t_start
        result = RunResult(
            algorithm=algorithm,
            dataset=dataset_cfg.name,
            forget_ratio=forget_ratio,
            run_id=run_id,
            seed=seed,
            accuracy_before=acc_before_test,
            precision_before=before_metrics.get("precision_macro", 0.0),
            recall_before=before_metrics.get("recall_macro", 0.0),
            f1_before=before_metrics.get("f1_macro", 0.0),
            accuracy_after=acc_after_test,
            precision_after=after_metrics.get("precision_macro", 0.0),
            recall_after=after_metrics.get("recall_macro", 0.0),
            f1_after=after_metrics.get("f1_macro", 0.0),
            forget_accuracy=forget_acc_after,
            memorization_score=memorization_score,
            mia_success_before=mia_before_acc,
            mia_success_after=mia_after_acc,
            privacy_leakage=privacy_leakage,
            training_time=training_time,
            unlearning_time=unlearning_time,
            speedup=speedup,
            memory_peak_mb=memory_peak,
            trust_score=trust_score_val,
            utility_loss=utility_loss,
            knowledge_retention=knowledge_retention,
            confusion_matrix_before=cm_before.get("confusion_matrix_raw", []),
            confusion_matrix_after=cm_after.get("confusion_matrix_raw", []),
            roc_curve_before=roc_before,
            roc_curve_after=roc_after,
            pr_curve_before=pr_before,
            pr_curve_after=pr_after,
            elapsed_seconds=elapsed,
        )
        logger.info(
            "  Done in %.1fs — acc_before=%.4f  acc_after=%.4f  forget_acc=%.4f  mia=%.4f",
            elapsed, result.accuracy_before, result.accuracy_after,
            result.forget_accuracy, result.mia_success_after,
        )
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return result

    # ------------------------------------------------------------------
    # MIA helper
    # ------------------------------------------------------------------

    def _run_mia(
        self,
        result,
        eval_ds: EvalDataset,
        seed: int,
    ) -> tuple[float, dict, dict]:
        """Run membership inference attack and return (accuracy, roc_data, pr_data)."""
        n_samples = self.config.privacy.mia_num_samples
        try:
            estimator = _get_estimator(result)
            X_train = _transform_for_algo(result, eval_ds, "train_subsample")
            X_test = _transform_for_algo(result, eval_ds, "test_subsample")
            y_train = eval_ds.y[:len(X_train)]
            y_test = eval_ds.y_test[:len(X_test)]

            mia_acc = _membership_inference_attack(
                estimator, X_train, y_train, X_test, y_test,
                n_samples=n_samples,
            )
            roc_data, pr_data = _compute_mia_curves(
                estimator, X_train, y_train, X_test, y_test,
                n_samples=n_samples,
            )
        except Exception as exc:
            logger.debug("MIA failed: %s", exc)
            mia_acc = 0.5
            roc_data = {}
            pr_data = {}
        return mia_acc, roc_data, pr_data

    # ------------------------------------------------------------------
    # Summary aggregation
    # ------------------------------------------------------------------

    def _compute_summary(self, runs: list[RunResult]) -> dict:
        valid = [r for r in runs if r.error is None]
        if not valid:
            return {"total_runs": len(runs), "successful": 0, "failed": len(runs)}

        grouped: dict[str, list[RunResult]] = {}
        for r in valid:
            key = f"{r.algorithm}|{r.dataset}|{r.forget_ratio}"
            grouped.setdefault(key, []).append(r)

        agg: dict[str, dict] = {}
        for key, group in grouped.items():
            algo, ds, fr = key.split("|")
            metric_keys = [
                "accuracy_before", "accuracy_after", "f1_before", "f1_after",
                "forget_accuracy", "memorization_score", "mia_success_before",
                "mia_success_after", "privacy_leakage", "training_time",
                "unlearning_time", "speedup", "trust_score", "utility_loss",
                "knowledge_retention", "memory_peak_mb",
            ]
            stats: dict[str, Any] = {}
            for mk in metric_keys:
                vals = [getattr(r, mk) for r in group]
                stats[f"{mk}_mean"] = float(np.mean(vals))
                stats[f"{mk}_std"] = float(np.std(vals))
                stats[f"{mk}_min"] = float(np.min(vals))
                stats[f"{mk}_max"] = float(np.max(vals))
            stats["n_runs"] = len(group)
            agg[key] = stats

        algorithm_means: dict[str, dict] = {}
        for algo in set(r.algorithm for r in valid):
            algo_runs = [r for r in valid if r.algorithm == algo]
            algo_means = {}
            for mk in [
                "accuracy_after", "f1_after", "forget_accuracy",
                "mia_success_after", "trust_score", "utility_loss",
                "unlearning_time", "speedup",
            ]:
                vals = [getattr(r, mk) for r in algo_runs]
                algo_means[mk] = float(np.mean(vals))
            algorithm_means[algo] = algo_means

        return {
            "total_runs": len(runs),
            "successful": len(valid),
            "failed": len(runs) - len(valid),
            "per_config": agg,
            "algorithm_means": algorithm_means,
        }

    # ------------------------------------------------------------------
    # Checkpoint persistence
    # ------------------------------------------------------------------

    def _load_cached_result(self, key: str) -> RunResult | None:
        runs_path = self.output_dir / "runs.json"
        if not runs_path.exists():
            return None
        try:
            data = json.loads(runs_path.read_text())
            for rd in data:
                rk = f"{rd['algorithm']}|{rd['dataset']}|{rd['forget_ratio']}|{rd['run_id']}"
                if rk == key:
                    valid_fields = set(RunResult.__dataclass_fields__.keys())
                    filtered = {k: v for k, v in rd.items() if k in valid_fields}
                    return RunResult(**filtered)
        except Exception:
            pass
        return None

    def _persist_run_result(self, key: str, result: RunResult) -> None:
        runs_path = self.output_dir / "runs.json"
        existing: list[dict] = []
        if runs_path.exists():
            try:
                existing = json.loads(runs_path.read_text())
            except Exception:
                existing = []
        existing.append(asdict(result))
        runs_path.write_text(json.dumps(existing, indent=2, default=str))


# ---------------------------------------------------------------------------
# Utility helpers for EvalDataset ↔ algorithm bridging
# ---------------------------------------------------------------------------

def _get_estimator(result) -> Any:
    """Extract the underlying estimator from a TrainResult or UnlearnResult."""
    return result.estimator


def _transform_for_algo(
    result,
    eval_ds: EvalDataset,
    split: str,
    indices: np.ndarray | None = None,
) -> Any:
    """Transform data using the result's vectorizer/scaler for the given split."""
    estimator = result.estimator

    if split == "train_subsample":
        n = min(200, len(eval_ds.y))
        X = eval_ds.X[:n]
        if isinstance(estimator, list):
            return X
        if isinstance(estimator, _ShardedEnsemble) and eval_ds.texts is not None:
            return eval_ds.texts[:n]
        if result.vectorizer is not None and eval_ds.texts is not None:
            texts_sub = eval_ds.texts[:n]
            return result.vectorizer.transform(texts_sub)
        if result.scaler is not None:
            return result.scaler.transform(X)
        return X

    if split == "test_subsample":
        n = min(200, len(eval_ds.y_test))
        X_test = eval_ds.X_test[:n]
        if isinstance(estimator, list):
            return X_test
        if isinstance(estimator, _ShardedEnsemble) and eval_ds.texts_test is not None:
            return eval_ds.texts_test[:n]
        if result.vectorizer is not None and eval_ds.texts_test is not None:
            texts_sub = eval_ds.texts_test[:n]
            return result.vectorizer.transform(texts_sub)
        if result.scaler is not None:
            return result.scaler.transform(X_test)
        return X_test

    if split == "test":
        if isinstance(estimator, list):
            return eval_ds.X_test
        if isinstance(estimator, _ShardedEnsemble) and eval_ds.texts_test is not None:
            return eval_ds.texts_test
        if result.vectorizer is not None and eval_ds.texts_test is not None:
            return result.vectorizer.transform(eval_ds.texts_test)
        if result.scaler is not None:
            return result.scaler.transform(eval_ds.X_test)
        return eval_ds.X_test

    if split == "forget" and indices is not None:
        X_forget = eval_ds.X[indices]
        if isinstance(estimator, list):
            return X_forget
        if isinstance(estimator, _ShardedEnsemble) and eval_ds.texts is not None:
            return [eval_ds.texts[i] for i in indices]
        if result.vectorizer is not None and eval_ds.texts is not None:
            texts_f = [eval_ds.texts[i] for i in indices]
            return result.vectorizer.transform(texts_f)
        if result.scaler is not None:
            return result.scaler.transform(X_forget)
        return X_forget

    return eval_ds.X_test


def _predict_for_algo(
    result,
    eval_ds: EvalDataset,
    split: str,
    indices: np.ndarray | None = None,
) -> np.ndarray:
    """Run prediction using the result's estimator."""
    estimator = result.estimator
    X = _transform_for_algo(result, eval_ds, split, indices)

    if isinstance(estimator, list):
        if split == "forget" and indices is not None:
            return estimator[0].predict(X) if len(estimator) > 0 else np.zeros(len(indices))
        return estimator[0].predict(X) if len(estimator) > 0 else np.zeros(len(eval_ds.y_test))

    return np.asarray(estimator.predict(X))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="VeriUnlearn Benchmark Runner")
    parser.add_argument("--experiment-name", default="veriunlearn_benchmark")
    parser.add_argument(
        "--datasets", nargs="+", default=["mnist"],
        choices=["mnist", "cifar10", "imdb", "ag_news"],
    )
    parser.add_argument(
        "--algorithms", nargs="+",
        default=["retrain", "fine_tune_forgetting", "scrub", "influence_functions", "sisa"],
    )
    parser.add_argument("--forget-ratios", nargs="+", type=float, default=[0.05, 0.10, 0.20])
    parser.add_argument("--num-runs", type=int, default=3)
    parser.add_argument("--num-epochs", type=int, default=10)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--output-dir", default="evaluation/results")
    parser.add_argument("--seed-start", type=int, default=42)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )
    datasets_cfg = []
    for ds_name in args.datasets:
        if ds_name in ("mnist", "cifar10"):
            nc, inp = (10, (1, 28, 28)) if ds_name == "mnist" else (10, (3, 32, 32))
            mean, std = (
                ((0.1307,), (0.3081,)) if ds_name == "mnist"
                else ((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010))
            )
            datasets_cfg.append(DatasetConfig(name=ds_name, num_classes=nc, input_shape=inp, mean=mean, std=std))
        elif ds_name == "imdb":
            datasets_cfg.append(DatasetConfig(
                name="imdb", num_classes=2, vocab_size=30000, max_seq_length=512, input_shape=(512,),
            ))
        elif ds_name == "ag_news":
            datasets_cfg.append(DatasetConfig(
                name="ag_news", num_classes=4, vocab_size=30000, max_seq_length=256, input_shape=(256,),
            ))
    cfg = ExperimentConfig(
        experiment_name=args.experiment_name,
        datasets=tuple(datasets_cfg),
        training=TrainingConfig(
            num_epochs=args.num_epochs,
            learning_rate=args.lr,
            batch_size=args.batch_size,
        ),
        unlearning=UnlearningConfig(
            algorithms=tuple(args.algorithms),
            forget_ratios=tuple(args.forget_ratios),
            num_runs=args.num_runs,
            seed_start=args.seed_start,
        ),
        output=OutputConfig(output_dir=args.output_dir),
    )
    runner = ExperimentRunner(cfg)
    results = runner.run_all()
    print(f"\nBenchmark complete. Results saved to {args.output_dir}/")
    print(f"  Total runs: {len(results.runs)}")
    print(f"  Successful: {sum(1 for r in results.runs if r.error is None)}")
    print(f"  Failed:     {sum(1 for r in results.runs if r.error is not None)}")


if __name__ == "__main__":
    main()
