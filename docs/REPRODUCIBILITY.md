# VeriUnlearn Reproducibility Guide

## Overview

VeriUnlearn provides a comprehensive reproducibility framework for all
benchmark experiments. Every experiment captures:

- **Deterministic seeding** across all random number generators
- **Environment pinning** with exact package versions
- **Hardware recording** (CPU, GPU, RAM, platform)
- **Git commit hash** capture at time of experiment
- **Config fingerprinting** — SHA-256 hash of the full experiment config
- **Automatic reproducibility ZIP packages**

The framework supports three levels of reproducibility verification:
`fully_reproducible`, `partially_reproducible`, and `not_reproducible`.

---

## Deterministic Seeding

Seeds are applied at multiple levels to ensure bitwise reproducibility:

| Seed field       | Source              | Default | Applies to                            |
|------------------|---------------------|---------|---------------------------------------|
| `global_seed`    | Python `random`     | 42      | All Python-level randomness           |
| `numpy_seed`     | NumPy               | 42      | Array shuffling, sampling, noise      |
| `torch_seed`     | PyTorch CPU         | 42      | Weight init, dropout, data loading    |
| `cuda_seed`      | PyTorch CUDA        | 42      | GPU operations, cuDNN determinism     |
| `python_hash_seed` | `PYTHONHASHSEED`  | 42      | Hash randomization of dicts/sets      |

When CUDA is available, `cudnn.deterministic = True` and
`cudnn.benchmark = False` are enforced.

```python
from evaluation.config import SeedConfig

seeds = SeedConfig(
    global_seed=42,
    numpy_seed=42,
    torch_seed=42,
    cuda_seed=42,
    python_hash_seed=42,
)
seeds.apply()  # Sets all seeds and CUDA flags
```

---

## Environment Pinning

### Python Version

Requires **Python >= 3.12** (enforced by `pyproject.toml`).

### Package Versions

- **`requirements.lock.txt`** — pinned versions of all dependencies for
  exact reproduction. Generated from the combined requirements of all
  packages and the root project.
- **`environment.yml`** — Conda environment definition that includes
  PyTorch from the `pytorch` channel and all pip dependencies.
- **Snapshots** automatically capture `pip freeze` output at experiment
  time and include a `requirements-lock.txt` inside the reproducibility ZIP.

### Virtual Environment Setup

```bash
# pip + venv
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate    # Windows
pip install -r requirements.lock.txt

# Conda/Mamba
conda env create -f environment.yml
conda activate veriunlearn
```

---

## Hardware Recording

Every experiment snapshot captures:

| Field               | Source                          |
|---------------------|---------------------------------|
| `platform`          | `platform.platform()`           |
| `processor`         | `platform.processor()`          |
| `architecture`      | `platform.architecture()`       |
| `machine`           | `platform.machine()`            |
| `python_version`    | `platform.python_version()`     |
| `torch_version`     | `torch.__version__`             |
| `cuda_available`    | `torch.cuda.is_available()`     |
| `cuda_version`      | `torch.version.cuda`            |
| `gpu_name`          | `torch.cuda.get_device_name()`  |
| `gpu_memory_gb`     | `torch.cuda.get_device_properties()` |
| `numpy_version`     | `numpy.__version__`             |
| `sklearn_version`   | `sklearn.__version__`           |

The `_hardware_compatible()` check only requires matching architecture and
GPU model — exact CPU/RAM equivalence is not enforced.

---

## Git Commit Hash Capture

The `get_git_info()` function (in `evaluation/config.py`) captures:

- **commit**: short SHA (12 chars) via `git rev-parse HEAD`
- **branch**: via `git rev-parse --abbrev-ref HEAD`
- **dirty**: `True` if there are uncommitted changes (`git status --porcelain`)

This information is embedded in every snapshot and reproducibility package.

---

## Config Fingerprinting

Each `ExperimentConfig` object produces a deterministic SHA-256 fingerprint
(truncated to 16 hex characters):

```python
config = ExperimentConfig(experiment_name="veriunlearn_phase2_complete")
fp = config.fingerprint()
# e.g., "9493d7469abde546"
```

The fingerprint changes when any config field is modified. Two experiments
with the same fingerprint have identical configurations.

---

## Full Phase 2 Benchmark

The Phase 2 benchmark runs:

- **4 datasets**: MNIST, CIFAR-10, IMDB, AG News
- **5 algorithms**: Retrain, SISA, SCRUB, Influence Functions, Fine-Tune Forgetting
- **3 forget ratios**: 5%, 10%, 25%
- **5 seeds per configuration** (42, 43, 44, 45, 46)
- **Total: 4 × 5 × 3 × 5 = 300 runs**

### Run the Full Benchmark

```bash
# Using the run_all entry point
python -m evaluation.run_all \
    --datasets mnist cifar10 imdb ag_news \
    --algorithms retrain sisa scrub influence_functions fine_tune_forgetting \
    --forget-ratios 0.05 0.10 0.25 \
    --num-runs 5 \
    --seed 42 \
    --output-dir evaluation/results/phase2_complete
```

Or using the dedicated script:

```bash
python evaluation/_phase2_benchmark.py
```

Or using Make:

```bash
make benchmark-full
```

### Expected Runtime

| Configuration      | Estimated Time |
|-------------------|----------------|
| Full Phase 2 (300 runs) | ~40 minutes (CPU) |
| Quick test (6 runs)     | ~1 minute         |
| Validation (90 runs)    | ~12 minutes        |

Times are approximate and depend on hardware. GPU acceleration will
significantly reduce runtimes.

### Expected Results

After the benchmark completes, results are saved to
`evaluation/results/phase2_complete/`:

```
evaluation/results/phase2_complete/
├── config.json
├── results.json
├── runs.json
├── summary.json
├── reproducibility_snapshot.json
├── figures/
├── exports/
├── report.md
└── reproducibility_*.zip
```

The reference snapshot is at
`evaluation/results/phase2_complete/reproducibility_snapshot.json`.

---

## Verification Commands

### Verify Against Reference Snapshot

```python
from evaluation.reproducibility import ReproducibilityPackage
import json

pkg = ReproducibilityPackage()
snapshot_ref = json.load(open("evaluation/results/phase2_complete/reproducibility_snapshot.json"))
snapshot_new = json.load(open("evaluation/results/phase2_new/reproducibility_snapshot.json"))
verdict = pkg.verify_reproducibility(snapshot_ref, snapshot_new)
print(verdict["overall"])  # "fully_reproducible" or "partially_reproducible"
```

### Smoke Test

```bash
make test-evaluation
# or
python evaluation/smoke_test.py
```

### Unit Tests

```bash
make test
# or
pytest evaluation/tests/
```

### Verify Environment

```bash
make verify
# or
python -c "from evaluation.config import get_hardware_info, get_git_info, get_package_versions; import json; print(json.dumps({'hardware': get_hardware_info(), 'git': get_git_info(), 'packages': get_package_versions()}, indent=2))"
```

---

## Container-Based Reproduction (Docker)

### Build and Run

```bash
# Build all images
docker compose build

# Start full stack (requires .env file)
cp .env.example .env
docker compose up -d

# Run benchmark inside the backend container
docker compose exec backend python -m evaluation.run_all --quick

# Pull logs
docker compose logs -f backend
```

### Docker Compose Profiles

```bash
# Core services only (default)
docker compose up -d

# With monitoring (Prometheus, Grafana, Loki)
docker compose --profile monitoring up -d
```

### Production Reproducibility

For fully isolated reproduction:

```bash
# Build with no cache to ensure clean state
docker compose build --no-cache

# Run with deterministic environment
docker compose run --rm backend python -m evaluation._phase2_benchmark

# Extract results
docker compose cp backend:/app/evaluation/results ./results_from_docker
```

---

## Reproducibility ZIP Package

Every experiment run via `run_all.py` automatically generates a
reproducibility ZIP containing:

| File                 | Description                                    |
|----------------------|------------------------------------------------|
| `config.json`        | Full experiment configuration                  |
| `results.json`       | Complete experiment results                    |
| `environment.json`   | Hardware, git, and package versions            |
| `requirements-lock.txt` | Exact pip freeze output                    |
| `reproduce.sh`       | Linux/macOS auto-reproduction script           |
| `reproduce.bat`      | Windows auto-reproduction script               |
| `README.md`          | Reproduction instructions for this experiment  |

---

## Verification Levels

The `verify_reproducibility()` method returns:

```python
{
    "overall": "fully_reproducible",  # or "partially_reproducible"
    "config_match": True,
    "seeds_match": True,
    "environment": {
        "packages_match": True,
        "hardware_compatible": True,
    },
    "git_match": True,
    "datasets_match": True,
    "results": {
        "num_runs_match": True,
        "snapshot1_completed": 300,
        "snapshot2_completed": 300,
    },
}
```

Criteria for `fully_reproducible`:
- Same config fingerprint
- Same seeds
- Same package versions
- Same dataset hashes

Hardware and git commit are not required for full reproducibility (git
dirty state and different CPUs are acceptable).

---

## Troubleshooting

### Non-Deterministic Results

1. Verify `PYTHONHASHSEED` is set: `echo $PYTHONHASHSEED`
2. Check CUDA determinism flags: `torch.backends.cudnn.deterministic`
3. Ensure no multi-threading races: set `torch.set_num_threads(1)`
4. Verify all seeds are applied before any data loading

### Package Version Mismatch

1. Install from `requirements.lock.txt`: `pip install -r requirements.lock.txt`
2. Or use Conda: `conda env create -f environment.yml`
3. Check with `make verify`

### Snapshot Verification Fails

1. Compare config fingerprints first: they must match
2. Check for uncommitted git changes (`git status`)
3. Verify the same datasets and max_samples are configured
4. Run `python evaluation/smoke_test.py` to isolate issues
