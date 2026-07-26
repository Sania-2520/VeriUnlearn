import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.chdir(os.path.join(os.path.dirname(__file__), '..'))

import json, time, logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("smoke_test")

from evaluation.config import (
    ExperimentConfig, SeedConfig, DatasetConfig, ModelConfig,
    TrainingConfig, UnlearningConfig, PrivacyConfig, OutputConfig,
    get_hardware_info, get_git_info, get_package_versions,
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
logger.info(f"Experiment complete. Entries: {len(results)}")

for r in results:
    m = r.get("metrics", {})
    s = r.get("status", "?")
    logger.info(f"  {r.get('dataset')}/{r.get('algorithm')} fr={r.get('forget_ratio')} "
                 f"seed={r.get('seed')} status={s} "
                 f"acc={m.get('test_accuracy', 'N/A'):.4f}" if isinstance(m.get('test_accuracy'), (int, float)) else
                 f"acc={m.get('test_accuracy', 'N/A')}")

logger.info("=== SMOKE TEST COMPLETE ===")
