#!/usr/bin/env python3
"""Phase 2 Scientific Validation — Full benchmark runner.

Runs: 4 datasets x 5 algorithms x 3 forget ratios x 5 seeds = 300 runs
"""

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("phase2")

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

PHASE2_DIR = "evaluation/results/phase2_complete"

ALGORITHMS = ("retrain", "sisa", "scrub", "influence_functions", "fine_tune_forgetting")
FORGET_RATIOS = (0.05, 0.10, 0.25)
NUM_RUNS = 5
SEED_START = 42

DATASETS = (
    DatasetConfig(
        name="mnist", num_classes=10, input_shape=(1, 28, 28),
        mean=(0.1307,), std=(0.3081,), max_samples=500,
    ),
    DatasetConfig(
        name="cifar10", num_classes=10, input_shape=(3, 32, 32),
        mean=(0.4914, 0.4822, 0.4465), std=(0.2023, 0.1994, 0.2010), max_samples=500,
    ),
    DatasetConfig(
        name="imdb", num_classes=2, vocab_size=30000, max_seq_length=512,
        input_shape=(512,), max_samples=500,
    ),
    DatasetConfig(
        name="ag_news", num_classes=4, vocab_size=30000, max_seq_length=256,
        input_shape=(256,), max_samples=500,
    ),
)

config = ExperimentConfig(
    experiment_name="veriunlearn_phase2_complete",
    seeds=SeedConfig(global_seed=42, numpy_seed=42, torch_seed=42),
    datasets=DATASETS,
    model=ModelConfig(name="logistic_regression"),
    training=TrainingConfig(batch_size=128, learning_rate=1e-3, num_epochs=2),
    unlearning=UnlearningConfig(
        algorithms=ALGORITHMS,
        forget_ratios=FORGET_RATIOS,
        num_runs=NUM_RUNS,
        seed_start=SEED_START,
    ),
    privacy=PrivacyConfig(mia_num_samples=200),
    output=OutputConfig(output_dir=PHASE2_DIR),
)

logger.info("=" * 60)
logger.info("PHASE 2 SCIENTIFIC VALIDATION — COMPLETE BENCHMARK")
logger.info(f"Datasets: {[d.name for d in config.datasets]}")
logger.info(f"Algorithms: {config.unlearning.algorithms}")
logger.info(f"Forget ratios: {config.unlearning.forget_ratios}")
logger.info(f"Runs per config: {config.unlearning.num_runs} (seeds %s-%s)" % (
    config.unlearning.seed_start,
    config.unlearning.seed_start + config.unlearning.num_runs - 1,
))
total = len(config.datasets) * len(config.unlearning.algorithms) * len(config.unlearning.forget_ratios) * config.unlearning.num_runs
logger.info(f"Total runs: {total}")
logger.info("=" * 60)

runner = ExperimentRunner(config)
results = runner.run_all()

succeeded = [r for r in results.runs if r.error is None]
failed = [r for r in results.runs if r.error is not None]
logger.info("=" * 60)
logger.info(f"RESULTS: {len(succeeded)} succeeded, {len(failed)} failed")
if failed:
    for r in failed:
        logger.info(f"  FAIL: {r.algorithm:>24s} / {r.dataset:>8s} / fr={r.forget_ratio:.2f} / seed={r.seed}  {r.error}")
logger.info("=" * 60)

# Generate exports and report via run_all
print(f"\nBenchmark complete: {len(succeeded)}/{total} runs succeeded")
print(f"Results saved to {PHASE2_DIR}/")
