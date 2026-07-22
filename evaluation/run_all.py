#!/usr/bin/env python3
"""VeriUnlearn Evaluation Framework — Main entry point.

Usage:
    # Full benchmark (all datasets, algorithms, forget ratios)
    python -m evaluation.run_all

    # Quick smoke test (small config)
    python -m evaluation.run_all --quick

    # Specific dataset
    python -m evaluation.run_all --datasets mnist cifar10

    # Specific algorithms
    python -m evaluation.run_all --algorithms retraining sisa scrub

    # Custom forget ratios
    python -m evaluation.run_all --forget-ratios 0.05 0.10 0.20

    # Number of runs per config
    python -m evaluation.run_all --num-runs 3

    # Skip visualization / export
    python -m evaluation.run_all --no-figures --no-export
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("evaluation")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="VeriUnlearn Evaluation Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--quick", action="store_true",
        help="Run a quick smoke test with minimal config",
    )
    parser.add_argument(
        "--datasets", nargs="+",
        choices=["mnist", "cifar10", "imdb", "ag_news"],
        default=None,
        help="Datasets to evaluate on",
    )
    parser.add_argument(
        "--algorithms", nargs="+",
        choices=["retraining", "sisa", "scrub", "influence_functions", "fine_tune_forgetting"],
        default=None,
        help="Algorithms to compare",
    )
    parser.add_argument(
        "--forget-ratios", nargs="+", type=float,
        default=None,
        help="Forget ratios to test",
    )
    parser.add_argument(
        "--num-runs", type=int, default=None,
        help="Number of runs per configuration",
    )
    parser.add_argument(
        "--max-samples", type=int, default=None,
        help="Max samples per dataset (for quick tests)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Global random seed",
    )
    parser.add_argument(
        "--output-dir", type=str, default="evaluation/results",
        help="Output directory for results",
    )
    parser.add_argument(
        "--no-figures", action="store_true",
        help="Skip figure generation",
    )
    parser.add_argument(
        "--no-export", action="store_true",
        help="Skip CSV/JSON/LaTeX export",
    )
    parser.add_argument(
        "--no-report", action="store_true",
        help="Skip report generation",
    )
    parser.add_argument(
        "--no-zip", action="store_true",
        help="Skip reproducibility ZIP",
    )
    return parser.parse_args()


def build_config(args: argparse.Namespace):
    """Build experiment config from CLI arguments."""
    from evaluation.config import (
        ExperimentConfig, SeedConfig, DatasetConfig,
        ModelConfig, TrainingConfig, UnlearningConfig,
        PrivacyConfig, OutputConfig,
    )

    seeds = SeedConfig(
        global_seed=args.seed,
        numpy_seed=args.seed,
        torch_seed=args.seed,
        cuda_seed=args.seed,
        python_hash_seed=args.seed,
    )

    if args.quick:
        datasets = (
            DatasetConfig(name="mnist", num_classes=10, input_shape=(1, 28, 28),
                          mean=(0.1307,), std=(0.3081,), max_samples=2000),
        )
        algorithms = ("retraining", "sisa", "scrub")
        forget_ratios = (0.10,)
        num_runs = 1
        max_samples = 2000
    else:
        all_datasets = {
            "mnist": DatasetConfig(name="mnist", num_classes=10, input_shape=(1, 28, 28),
                                   mean=(0.1307,), std=(0.3081,)),
            "cifar10": DatasetConfig(name="cifar10", num_classes=10, input_shape=(3, 32, 32),
                                      mean=(0.4914, 0.4822, 0.4465), std=(0.2023, 0.1994, 0.2010)),
            "imdb": DatasetConfig(name="imdb", num_classes=2, vocab_size=30000,
                                   max_seq_length=512, input_shape=(512,)),
            "ag_news": DatasetConfig(name="ag_news", num_classes=4, vocab_size=30000,
                                      max_seq_length=256, input_shape=(256,)),
        }
        ds_names = args.datasets or ["mnist", "cifar10", "imdb", "ag_news"]
        datasets = tuple(all_datasets[n] for n in ds_names)
        algorithms = tuple(args.algorithms) if args.algorithms else (
            "retrain", "sisa", "scrub", "influence_functions", "fine_tune_forgetting"
        )
        forget_ratios = tuple(args.forget_ratios) if args.forget_ratios else (0.05, 0.10, 0.20)
        num_runs = args.num_runs or 3
        max_samples = args.max_samples

    if max_samples is not None:
        datasets = tuple(
            DatasetConfig(
                name=d.name, root=d.root, max_samples=max_samples,
                train_split=d.train_split, val_split=d.val_split, test_split=d.test_split,
                num_classes=d.num_classes, input_shape=d.input_shape,
                vocab_size=d.vocab_size, max_seq_length=d.max_seq_length,
                normalize=d.normalize, mean=d.mean, std=d.std,
            )
            for d in datasets
        )

    config = ExperimentConfig(
        experiment_name="veriunlearn_benchmark_quick" if args.quick else "veriunlearn_benchmark",
        description="VeriUnlearn unlearning algorithm evaluation",
        seeds=seeds,
        datasets=datasets,
        model=ModelConfig(),
        training=TrainingConfig(
            batch_size=64 if args.quick else 128,
            num_epochs=3 if args.quick else 10,
        ),
        unlearning=UnlearningConfig(
            algorithms=algorithms,
            forget_ratios=forget_ratios,
            num_runs=num_runs,
            seed_start=args.seed,
        ),
        privacy=PrivacyConfig(
            mia_num_samples=200 if args.quick else 1000,
        ),
        output=OutputConfig(
            output_dir=args.output_dir,
            export_figures=not args.no_figures,
            export_csv=not args.no_export,
            export_json=not args.no_export,
            export_latex=not args.no_export,
        ),
    )
    return config


def main() -> int:
    args = parse_args()
    logger.info("=" * 70)
    logger.info("VeriUnlearn Evaluation Framework v1.0.0")
    logger.info("=" * 70)

    config = build_config(args)
    output_dir = Path(config.output.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    experiment_dir = output_dir / f"{config.experiment_name}_{timestamp}"
    experiment_dir.mkdir(parents=True, exist_ok=True)

    config.save(experiment_dir / "config.json")
    logger.info(f"Config saved: {experiment_dir / 'config.json'}")
    logger.info(f"Fingerprint: {config.fingerprint()}")
    logger.info(f"Datasets: {[d.name for d in config.datasets]}")
    logger.info(f"Algorithms: {list(config.unlearning.algorithms)}")
    logger.info(f"Forget ratios: {config.unlearning.forget_ratios}")
    logger.info(f"Num runs: {config.unlearning.num_runs}")

    total_experiments = (
        len(config.datasets)
        * len(config.unlearning.algorithms)
        * len(config.unlearning.forget_ratios)
        * config.unlearning.num_runs
    )
    logger.info(f"Total experiment runs: {total_experiments}")

    # ── Phase 1: Run experiments ──
    logger.info("")
    logger.info("Phase 1: Running experiments...")
    t0 = time.time()

    from evaluation.runner import ExperimentRunner
    runner = ExperimentRunner(config)
    results = runner.run_all()

    elapsed = time.time() - t0
    logger.info(f"Experiments completed in {elapsed:.1f}s")

    # Save raw results
    results.save(str(experiment_dir))
    logger.info(f"Results saved: {experiment_dir}")

    # Bridge runner results -> exporter/report/visualiser model
    export_results = results.to_export_model()

    # ── Phase 2: Generate figures ──
    figure_paths = []
    if config.output.export_figures:
        logger.info("")
        logger.info("Phase 2: Generating publication figures...")
        from evaluation.visualization import PublicationVisualizer
        viz = PublicationVisualizer()
        figures_dir = experiment_dir / "figures"
        figures_dir.mkdir(exist_ok=True)
        figure_paths = viz.generate_all_figures(export_results, str(figures_dir))
        logger.info(f"Generated {len(figure_paths)} figures")

    # ── Phase 3: Export ──
    if config.output.export_csv or config.output.export_json or config.output.export_latex:
        logger.info("")
        logger.info("Phase 3: Exporting results...")
        from evaluation.export import ResultsExporter
        exporter = ResultsExporter(export_results)
        exports_dir = experiment_dir / "exports"
        exports_dir.mkdir(exist_ok=True)

        if config.output.export_csv:
            exporter.export_results_csv(str(exports_dir / "results.csv"))
            exporter.export_detailed_csv(str(exports_dir / "detailed.csv"))
            exporter.export_comparison_csv(str(exports_dir / "comparison.csv"))
            logger.info("CSV exports complete")

        if config.output.export_json:
            exporter.export_results_json(str(exports_dir / "results.json"))
            exporter.export_config_json(str(exports_dir / "config.json"))
            exporter.export_summary_json(str(exports_dir / "summary.json"))
            logger.info("JSON exports complete")

        if config.output.export_latex:
            exporter.export_benchmark_table_latex(str(exports_dir / "benchmark_table.tex"))
            exporter.export_metrics_table_latex(str(exports_dir / "metrics_table.tex"))
            exporter.export_significance_table_latex(str(exports_dir / "significance_table.tex"))
            logger.info("LaTeX exports complete")

    # ── Phase 4: Report ──
    if not args.no_report:
        logger.info("")
        logger.info("Phase 4: Generating publication report...")
        from evaluation.report import PublicationReport
        report = PublicationReport(config)
        report_path = report.generate_report(export_results, figure_paths, str(experiment_dir))
        logger.info(f"Report saved: {report_path}")

    # ── Phase 5: Reproducibility package ──
    if not args.no_zip:
        logger.info("")
        logger.info("Phase 5: Creating reproducibility package...")
        from evaluation.reproducibility import ReproducibilityPackage
        repro = ReproducibilityPackage()
        zip_path = repro.create_reproducibility_zip(export_results, str(experiment_dir))
        logger.info(f"Reproducibility package: {zip_path}")

    # ── Summary ──
    logger.info("")
    logger.info("=" * 70)
    logger.info("BENCHMARK COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Results directory: {experiment_dir}")
    logger.info(f"Total time: {time.time() - t0:.1f}s")
    logger.info(f"Files generated:")
    for p in sorted(experiment_dir.rglob("*")):
        if p.is_file():
            rel = p.relative_to(experiment_dir)
            logger.info(f"  {rel}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
