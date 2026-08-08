#!/usr/bin/env python3
"""Smoke test for the VeriUnlearn evaluation framework.

Validates all components work end-to-end without GPU.
Run: python -m evaluation.test_framework
"""
from __future__ import annotations

import os
import sys
import tempfile
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_config():
    from evaluation.config import (
        DatasetConfig,
        ExperimentConfig,
        SeedConfig,
        get_git_info,
        get_hardware_info,
        get_package_versions,
    )
    config = ExperimentConfig(
        experiment_name="test",
        seeds=SeedConfig(global_seed=42),
        datasets=(DatasetConfig(name="mnist", max_samples=100),),
    )
    fp = config.fingerprint()
    assert isinstance(fp, str) and len(fp) == 16, f"Bad fingerprint: {fp}"

    tmp_path = Path(tempfile.mkdtemp()) / "test_config.json"
    config.save(tmp_path)
    loaded = ExperimentConfig.load(tmp_path)
    assert loaded.experiment_name == "test"
    tmp_path.unlink(missing_ok=True)

    hw = get_hardware_info()
    assert "platform" in hw
    gi = get_git_info()
    assert "commit" in gi
    pkgs = get_package_versions()
    assert isinstance(pkgs, dict)
    print("  [PASS] config")
    return True


def test_datasets():
    from evaluation.data_loading import load_by_name

    for name in ["mnist", "cifar10", "imdb", "ag_news"]:
        try:
            bundle = load_by_name(name, max_samples=200, seed_cfg=None)
            assert len(bundle.train) > 0, f"{name}: empty train"
            assert len(bundle.test) > 0, f"{name}: empty test"
        except ImportError as e:
            print(f"  [SKIP] {name}: missing dependency ({e})")
            continue
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            traceback.print_exc()
            return False

    print("  [PASS] datasets")
    return True


def test_algorithms():
    from evaluation.algorithms import get_algorithm, list_algorithms
    from evaluation.config import SeedConfig
    from evaluation.data_loading import create_forget_set, load_by_name
    from evaluation.runner import _bundle_to_eval_dataset

    available = list_algorithms()
    assert len(available) >= 5, f"Expected 5 algorithms, got {len(available)}: {available}"

    bundle = load_by_name("mnist", max_samples=300)
    create_forget_set(bundle, forget_ratio=0.1, seed=42)

    eval_ds, forget_idx, retain_idx = _bundle_to_eval_dataset(bundle, forget_ratio=0.1, seed=42)
    seed_cfg = SeedConfig(global_seed=42)

    for algo_name in ["retrain", "sisa", "scrub", "influence_functions", "fine_tune_forgetting"]:
        try:
            algo = get_algorithm(algo_name)
            seed_cfg.apply()

            train_result = algo.fit(eval_ds, seed=42)
            metrics_before = algo.evaluate(train_result, eval_ds)
            assert "accuracy" in metrics_before, f"{algo_name}: missing accuracy"

            unlearn_result = algo.unlearn(train_result, forget_idx, retain_idx, eval_ds, seed=42)

            metrics_after = algo.evaluate(unlearn_result, eval_ds)
            assert "accuracy" in metrics_after, f"{algo_name}: missing accuracy after"

            params = algo.get_params()
            assert isinstance(params, dict), f"{algo_name}: get_params() didn't return dict"

        except Exception as e:
            print(f"  [FAIL] {algo_name}: {e}")
            traceback.print_exc()
            return False

    print("  [PASS] algorithms")
    return True


def test_metrics():
    import numpy as np

    from evaluation.metrics import (
        aggregate_results,
        compute_classification_metrics,
        compute_confusion_matrix,
        compute_efficiency_metrics,
        compute_forget_quality,
        compute_pr_curve,
        compute_privacy_metrics,
        compute_roc_curve,
        compute_statistical_significance,
        compute_trust_score,
        compute_utility_metrics,
    )

    y_true = np.array([0, 1, 1, 0, 1, 0, 1, 1, 0, 0])
    y_pred = np.array([0, 1, 0, 0, 1, 1, 1, 0, 0, 0])
    y_scores = np.array([0.1, 0.9, 0.6, 0.2, 0.8, 0.4, 0.7, 0.3, 0.15, 0.05])

    metrics = compute_classification_metrics(y_true, y_pred, num_classes=2)
    assert "accuracy" in metrics
    assert 0 <= metrics["accuracy"] <= 1

    fq = compute_forget_quality(
        acc_before_forget=0.92, acc_after_forget=0.50,
        loss_member=np.array([0.5, 0.3, 0.4]),
        loss_nonmember=np.array([1.2, 1.5, 1.1]),
    )
    assert "forget_drop" in fq or "quality_score" in fq

    um = compute_utility_metrics(
        accuracy_before_test=0.92, accuracy_after_test=0.88,
        accuracy_before_retain=0.93, accuracy_after_retain=0.91,
    )
    assert "utility_loss" in um or "knowledge_retention" in um

    pm = compute_privacy_metrics(
        member_losses=np.array([0.5, 0.3]),
        nonmember_losses=np.array([1.2, 1.5]),
    )
    assert isinstance(pm, dict)

    em = compute_efficiency_metrics(
        training_time_s=10.0, unlearning_time_s=5.0, retraining_time_s=10.0,
        peak_memory_mb=128.0,
    )
    assert "speedup_vs_retrain" in em or "time_ratio" in em

    ts = compute_trust_score(
        forget_drop=0.8, knowledge_retention=0.95,
        privacy_leakage_score=0.7, speedup_vs_retrain=0.6,
    )
    assert isinstance(ts, dict)
    assert "trust_score" in ts

    cm = compute_confusion_matrix(y_true, y_pred, num_classes=2)
    assert isinstance(cm, dict)
    assert "confusion_matrix_raw" in cm

    roc = compute_roc_curve(y_true, y_scores)
    assert isinstance(roc, dict)
    assert "auc" in roc

    pr = compute_pr_curve(y_true, y_scores)
    assert isinstance(pr, dict)
    assert "auc" in pr

    run_results = [
        {"accuracy": 0.85, "f1_score": 0.83},
        {"accuracy": 0.87, "f1_score": 0.85},
        {"accuracy": 0.84, "f1_score": 0.82},
    ]
    agg = aggregate_results(run_results)
    assert "accuracy_mean" in agg or "accuracy" in agg

    a = [{"accuracy": 0.85}, {"accuracy": 0.87}, {"accuracy": 0.84}]
    b = [{"accuracy": 0.80}, {"accuracy": 0.82}, {"accuracy": 0.79}]
    sig = compute_statistical_significance(a, b)
    assert isinstance(sig, dict)

    print("  [PASS] metrics")
    return True


def test_runner_quick():
    from evaluation.config import (
        DatasetConfig,
        ExperimentConfig,
        ModelConfig,
        OutputConfig,
        PrivacyConfig,
        SeedConfig,
        TrainingConfig,
        UnlearningConfig,
    )
    from evaluation.runner import ExperimentRunner

    config = ExperimentConfig(
        experiment_name="smoke_test",
        seeds=SeedConfig(global_seed=42),
        datasets=(DatasetConfig(name="mnist", max_samples=200),),
        model=ModelConfig(),
        training=TrainingConfig(batch_size=64, num_epochs=2),
        unlearning=UnlearningConfig(
            algorithms=("retrain", "sisa"),
            forget_ratios=(0.10,),
            num_runs=1,
        ),
        privacy=PrivacyConfig(mia_num_samples=50),
        output=OutputConfig(output_dir=tempfile.mkdtemp()),
    )

    runner = ExperimentRunner(config)
    results = runner.run_all()

    assert len(results.runs) >= 1, f"Expected at least 1 run, got {len(results.runs)}"
    run = results.runs[0]
    assert run.accuracy_before >= 0, f"Negative accuracy_before: {run.accuracy_before}"
    assert run.algorithm in ["retrain", "sisa"], f"Unexpected algorithm: {run.algorithm}"
    assert run.training_time >= 0
    assert run.unlearning_time >= 0

    print("  [PASS] runner")
    return True


def test_visualization():
    import numpy as np

    from evaluation.config import ExperimentConfig, OutputConfig
    from evaluation.runner import ExperimentResults, RunResult
    from evaluation.visualization import PublicationVisualizer

    config = ExperimentConfig(
        experiment_name="viz_test",
        output=OutputConfig(output_dir=tempfile.mkdtemp()),
    )

    runs = []
    for algo in ["retrain", "sisa", "scrub"]:
        for fr in [0.10]:
            runs.append(RunResult(
                algorithm=algo, dataset="mnist", forget_ratio=fr, run_id=0, seed=42,
                accuracy_before=0.92 + np.random.random() * 0.05,
                precision_before=0.91, recall_before=0.90, f1_before=0.90,
                accuracy_after=0.88 + np.random.random() * 0.05,
                precision_after=0.87, recall_after=0.86, f1_after=0.86,
                forget_accuracy=0.3 + np.random.random() * 0.2,
                memorization_score=0.1 + np.random.random() * 0.1,
                mia_success_before=0.65, mia_success_after=0.50 + np.random.random() * 0.05,
                privacy_leakage=0.15, training_time=10.0, unlearning_time=5.0,
                speedup=2.0, memory_peak_mb=128.0,
                trust_score=75.0 + np.random.random() * 10,
                utility_loss=0.03, knowledge_retention=0.97,
                confusion_matrix_before=[[95, 5], [8, 92]],
                confusion_matrix_after=[[93, 7], [10, 90]],
                roc_curve_before={"fpr": [0, 0.1, 1], "tpr": [0, 0.8, 1], "auc": 0.85},
                roc_curve_after={"fpr": [0, 0.2, 1], "tpr": [0, 0.6, 1], "auc": 0.70},
                pr_curve_before={"precision": [1, 0.9, 0], "recall": [0, 0.8, 1], "auc": 0.82},
                pr_curve_after={"precision": [1, 0.8, 0], "recall": [0, 0.6, 1], "auc": 0.65},
                elapsed_seconds=15.0,
            ))

    results = ExperimentResults(
        config=config, runs=runs, summary={},
        hardware_info={"platform": "test"}, git_info={"commit": "test"},
        package_versions={}, timestamp="2026-01-01",
    )

    viz = PublicationVisualizer()
    out_dir = tempfile.mkdtemp()
    figs = viz.generate_all_figures(results, out_dir)
    assert len(figs) > 0, "No figures generated"

    print("  [PASS] visualization")
    return True


def test_export():
    import tempfile

    from evaluation.export import ExperimentResults, ResultsExporter, RunResult

    runs = [RunResult(
        run_id=0, algorithm="retrain", dataset="mnist", forget_ratio=0.10, seed=42,
        metrics={
            "accuracy": 0.88, "precision": 0.87, "recall": 0.86, "f1_score": 0.86,
            "forget_quality": 0.70, "utility_loss": 0.03, "knowledge_retention": 0.97,
            "mia_success_before": 0.65, "mia_success_after": 0.50,
            "privacy_leakage": 0.15, "trust_score": 75.0,
        },
        timing={"training_time": 10.0, "unlearning_time": 5.0, "speedup": 2.0},
    )]

    results = ExperimentResults(
        config={"experiment_name": "export_test"},
        algorithm_names=["retrain"],
        dataset_names=["mnist"],
        metric_names=["accuracy", "precision", "recall", "f1_score", "forget_quality",
                       "utility_loss", "knowledge_retention", "trust_score"],
        runs=runs,
    )

    exporter = ResultsExporter(results)
    out_dir = tempfile.mkdtemp()

    csv_path = os.path.join(out_dir, "results.csv")
    exporter.export_results_csv(csv_path)
    assert os.path.exists(csv_path) and os.path.getsize(csv_path) > 0

    json_path = os.path.join(out_dir, "results.json")
    exporter.export_results_json(json_path)
    assert os.path.exists(json_path)

    latex_path = os.path.join(out_dir, "benchmark.tex")
    exporter.export_benchmark_table_latex(latex_path)
    assert os.path.exists(latex_path)
    content = open(latex_path).read()
    assert "\\begin{table" in content
    assert "\\toprule" in content

    print("  [PASS] export")
    return True


def main():
    print("=" * 60)
    print("VeriUnlearn Evaluation Framework — Smoke Tests")
    print("=" * 60)

    tests = [
        ("Config", test_config),
        ("Datasets", test_datasets),
        ("Algorithms", test_algorithms),
        ("Metrics", test_metrics),
        ("Runner (quick)", test_runner_quick),
        ("Visualization", test_visualization),
        ("Export", test_export),
    ]

    results = []
    for name, test_fn in tests:
        print(f"\nTesting {name}...")
        try:
            passed = test_fn()
            results.append((name, passed))
        except Exception as e:
            print(f"  [ERROR] {e}")
            traceback.print_exc()
            results.append((name, False))

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    passed = sum(1 for _, p in results if p)
    total = len(results)
    for name, p in results:
        status = "PASS" if p else "FAIL"
        print(f"  [{status}] {name}")
    print(f"\n{passed}/{total} tests passed")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
