import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.chdir(os.path.join(os.path.dirname(__file__), '..'))

import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("smoke_test")

from evaluation.config import (
    DatasetConfig,
    ExperimentConfig,
    ModelConfig,
    OutputConfig,
    PrivacyConfig,
    SeedConfig,
    TrainingConfig,
    UnlearningConfig,
    get_git_info,
    get_hardware_info,
    get_package_versions,
)

logger.info("=== MILESTONE 1: Experimental Environment ===")
hw = get_hardware_info()
git = get_git_info()
pkgs = get_package_versions()
logger.info(f"Hardware: {json.dumps(hw, indent=2)}")
logger.info(f"Git: {json.dumps(git, indent=2)}")
logger.info(f"Packages: {json.dumps(pkgs, indent=2)}")

config = ExperimentConfig(
    experiment_name="veriunlearn_validation",
    seeds=SeedConfig(global_seed=42, numpy_seed=42, torch_seed=42),
    datasets=(DatasetConfig(
        name="mnist", num_classes=10, input_shape=(1, 28, 28),
        mean=(0.1307,), std=(0.3081,), max_samples=500,
    ),),
    model=ModelConfig(name="logistic_regression"),
    training=TrainingConfig(batch_size=128, learning_rate=1e-3, num_epochs=2),
    unlearning=UnlearningConfig(
        algorithms=("retrain", "scrub"),
        forget_ratios=(0.10,),
        num_runs=1, seed_start=42,
    ),
    privacy=PrivacyConfig(mia_num_samples=200),
    output=OutputConfig(output_dir="evaluation/results/smoke_test"),
)

logger.info(f"Config: {config.experiment_name}")
logger.info(f"Datasets: {[d.name for d in config.datasets]}")
logger.info(f"Algorithms: {config.unlearning.algorithms}")
logger.info(f"Forget ratios: {config.unlearning.forget_ratios}")

from evaluation.runner import ExperimentRunner

runner = ExperimentRunner(config)
results = runner.run_all()

# ``run_all()`` returns an ``ExperimentResults`` container; per-run records live
# in its ``runs`` attribute (a list of typed ``RunResult`` dataclasses).
logger.info("Experiment complete. Runs: %d", len(results.runs))

for r in results.runs:
    status = "OK" if r.error is None else f"FAILED: {r.error}"
    logger.info(
        "  %s/%s fr=%.2f seed=%s status=%s acc_after=%.4f",
        r.dataset,
        r.algorithm,
        r.forget_ratio,
        r.seed,
        status,
        r.accuracy_after,
    )

logger.info("=== SMOKE TEST COMPLETE ===")
