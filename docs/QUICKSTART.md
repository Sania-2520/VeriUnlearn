# VeriUnlearn Quick Start

```text
Verifiable Machine Unlearning Framework
with Cryptographic Proofs for GDPR-Compliant AI Systems
```

---

## Prerequisites

- **Python >= 3.12**
- **pip** (latest: `python -m pip install --upgrade pip`)
- **Git** (for commit tracking)
- Optional: **Docker & Docker Compose v2** (for containerized setup)
- Optional: **NVIDIA GPU + CUDA** (for GPU-accelerated benchmarks)

---

## Installation

### Option 1: pip + venv (Recommended)

```bash
# Clone the repository
git clone https://github.com/veriunlearn/veriunlearn.git
cd veriunlearn

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate     # Windows

# Install with pinned dependencies
pip install -r requirements.lock.txt
```

### Option 2: Conda / Mamba

```bash
conda env create -f environment.yml
conda activate veriunlearn
```

### Option 3: Docker

```bash
# Build and start all services
cp .env.example .env
docker compose up -d --build

# Verify health
docker compose ps
curl http://localhost:8000/health
```

### Option 4: From Source (Development)

```bash
pip install -e .
pip install -r packages/backend/requirements.txt
pip install -r packages/ml-engine/requirements.txt
```

---

## Running the Benchmark

### Quick Smoke Test (~1 minute)

```bash
make benchmark-quick
# or
python -m evaluation.run_all --quick
```

This runs: 1 dataset (MNIST) x 3 algorithms x 1 forget ratio x 1 seed = 3 runs.

### Phase 2 Validation (~12 minutes)

```bash
make benchmark-phase2
# or
python evaluation/_run_benchmark.py
```

This runs: 2 datasets (MNIST, CIFAR-10) x 5 algorithms x 3 forget ratios x 3 seeds = 90 runs.

### Full Phase 2 Benchmark (~40 minutes)

```bash
make benchmark-full
# or
python evaluation/_phase2_benchmark.py
```

This runs: 4 datasets x 5 algorithms x 3 forget ratios x 5 seeds = 300 runs.

### Custom Benchmark

```bash
python -m evaluation.run_all \
    --datasets mnist cifar10 \
    --algorithms retrain scrub \
    --forget-ratios 0.05 0.10 \
    --num-runs 3 \
    --seed 42 \
    --output-dir evaluation/results/my_experiment
```

---

## Viewing Results

### Output Directory Structure

After a benchmark completes, results are organized as:

```
evaluation/results/<experiment_name>_<timestamp>/
├── config.json                  # Experiment configuration
├── results.json                 # Raw results
├── runs.json                    # Per-run details
├── summary.json                 # Aggregated summaries
├── reproducibility_snapshot.json # Full snapshot for verification
├── report.md                    # Publication-ready report
├── figures/                     # Publication-quality figures (PDF)
│   ├── accuracy_comparison.pdf
│   ├── privacy_comparison.pdf
│   ├── efficiency_comparison.pdf
│   ├── scalability.pdf
│   └── radar_chart.pdf
├── exports/                     # Data exports
│   ├── results.csv
│   ├── detailed.csv
│   ├── comparison.csv
│   ├── results.json
│   ├── config.json
│   ├── summary.json
│   ├── benchmark_table.tex
│   ├── metrics_table.tex
│   └── significance_table.tex
├── report/                      # Full report assets
└── reproducibility_*.zip        # Portable reproducibility package
```

### Generate Figures Only

```bash
make figures
# or
python -c "
from evaluation.visualization import PublicationVisualizer
from evaluation.export import ResultsExporter, ExperimentResults
import json

results = ExperimentResults(**json.load(open('evaluation/results/results.json')))
viz = PublicationVisualizer()
viz.generate_all_figures(results, 'evaluation/results/figures')
"
```

### Generate Report Only

```bash
make report
# or
python -c "
from evaluation.report import PublicationReport
from evaluation.export import ExperimentResults
import json

results = ExperimentResults(**json.load(open('evaluation/results/results.json')))
report = PublicationReport()
report.generate_report(results, figures=[], output_dir='evaluation/results')
"
```

---

## Common Workflows

### Verify Reproducibility

```bash
make verify
```

Checks Python version, package versions, runs smoke tests, and verifies
results match the reference snapshot.

### Run All Tests

```bash
make test          # All tests (backend + evaluation)
make test-evaluation  # Evaluation-specific tests
```

### Lint and Type Check

```bash
make lint         # ruff check
make typecheck    # mypy check
```

### Clean Build Artifacts

```bash
make clean
```

Removes `__pycache__`, `.pytest_cache`, `.coverage`, `htmlcov`, etc.

---

## Make Targets Reference

| Target               | Description                              |
|----------------------|------------------------------------------|
| `help`               | Show available targets                   |
| `install`            | Install all dependencies                 |
| `install-dev`        | Install dev dependencies                 |
| `lint`               | Run ruff linter                          |
| `typecheck`          | Run mypy type checker                    |
| `test`               | Run all tests                            |
| `test-evaluation`    | Run evaluation-specific tests            |
| `benchmark-phase2`   | Run Phase 2 validation (90 runs)         |
| `benchmark-quick`    | Run quick smoke test (3 runs)            |
| `benchmark-full`     | Run full Phase 2 benchmark (300 runs)    |
| `figures`            | Generate publication figures             |
| `report`             | Generate publication report              |
| `docker-build`       | Build Docker images                      |
| `docker-up`          | Start Docker services                    |
| `docker-down`        | Stop Docker services                     |
| `clean`              | Clean temporary files                    |
| `verify`             | Verify reproducibility                   |

---

## Configuration

Environment variables are documented in `.env.example`. Key settings:

| Variable              | Default              | Description                    |
|-----------------------|----------------------|--------------------------------|
| `BASE_MODEL_NAME`     | `Qwen/Qwen2.5-1.5B` | Base model for LLM unlearning  |
| `ML_DEVICE`           | `cpu`                | `cpu` or `cuda`                |
| `QUANTIZATION_BITS`   | `4`                  | Bits for model quantization    |
| `JWT_SECRET_KEY`      | —                    | JWT signing secret             |
| `DATABASE_URL`        | —                    | PostgreSQL connection string   |

---

## Getting Help

- **Documentation**: https://docs.veriunlearn.com
- **Repository**: https://github.com/veriunlearn/veriunlearn
- **Issues**: https://github.com/veriunlearn/veriunlearn/issues
- **Make help**: `make help`
