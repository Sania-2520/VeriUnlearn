"""Full scientific benchmark for VeriUnlearn Phase 2 validation.
Runs 2 image datasets x 5 algorithms x 3 forget ratios x 3 seeds = 90 runs.
Text datasets (IMDB, AG News) are blocked by HuggingFace datasets v5 API incompatibility.
"""
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("benchmark")

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

ALGORITHMS = ("retrain", "scrub", "sisa", "influence_functions", "fine_tune_forgetting")
FORGET_RATIOS = (0.05, 0.10, 0.25)
NUM_RUNS = 3
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
)

config = ExperimentConfig(
    experiment_name="veriunlearn_validation_phase2",
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
    output=OutputConfig(output_dir="evaluation/results/phase2_validation"),
)

logger.info("=" * 60)
logger.info("Phase 2 Scientific Validation Benchmark")
logger.info(f"Datasets: {[d.name for d in config.datasets]}")
logger.info(f"Algorithms: {config.unlearning.algorithms}")
logger.info(f"Forget ratios: {config.unlearning.forget_ratios}")
logger.info(f"Runs per config: {config.unlearning.num_runs}")
total = len(config.datasets) * len(config.unlearning.algorithms) * len(config.unlearning.forget_ratios) * config.unlearning.num_runs
logger.info(f"Total runs: {total}")
logger.info("=" * 60)

runner = ExperimentRunner(config)
results = runner.run_all()

# Print summary
succeeded = [r for r in results.runs if r.error is None]
failed = [r for r in results.runs if r.error is not None]
logger.info("=" * 60)
logger.info(f"RESULTS: {len(succeeded)} succeeded, {len(failed)} failed")
for r in succeeded:
    logger.info(f"  {r.algorithm:>24s} / {r.dataset:>8s} / fr={r.forget_ratio:.2f} / seed={r.seed}  "
                 f"acc={r.accuracy_before:.4f}->{r.accuracy_after:.4f}  "
                 f"forget_acc={r.forget_accuracy:.4f}  mia={r.mia_success_after:.4f}")
for r in failed:
    logger.info(f"  FAIL: {r.algorithm:>24s} / {r.dataset:>8s} / fr={r.forget_ratio:.2f} / seed={r.seed}  {r.error}")
logger.info("=" * 60)
