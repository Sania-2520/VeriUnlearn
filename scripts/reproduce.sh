#!/usr/bin/env bash
# =============================================================================
# VeriUnlearn Automated Reproduction Script
#
# Usage:
#   ./scripts/reproduce.sh              # Run full Phase 2 benchmark
#   ./scripts/reproduce.sh --quick      # Run quick smoke test
#   ./scripts/reproduce.sh --validate   # Run validation (90 runs)
#
# This script will:
#   1. Check prerequisites (Python, pip, git)
#   2. Create and activate a virtual environment
#   3. Install pinned dependencies
#   4. Run the specified benchmark
#   5. Verify results match the reference snapshot
#   6. Generate figures and report
#   7. Print a summary
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

MODE="${1:-full}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
VENV_DIR="$ROOT_DIR/.venv_reproduce"
RESULTS_DIR="$ROOT_DIR/evaluation/results/reproduce_$TIMESTAMP"

echo "========================================================================"
echo "  VeriUnlearn — Automated Reproducibility Script"
echo "  Mode: $MODE"
echo "  Timestamp: $TIMESTAMP"
echo "========================================================================"

# ─── Step 0: Prerequisites ──────────────────────────────────────────────────
echo ""
echo "[1/7] Checking prerequisites..."

command -v python >/dev/null 2>&1 || { echo "✗ Python is required but not installed."; exit 1; }
command -v pip >/dev/null 2>&1 || { echo "✗ pip is required but not installed."; exit 1; }
command -v git >/dev/null 2>&1 || { echo "✗ git is required but not installed."; exit 1; }

PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo "  Python: $PYTHON_VERSION"
echo "  pip: $(pip --version 2>&1 | awk '{print $2}')"
echo "  git: $(git --version 2>&1 | awk '{print $3}')"

# Compare Python version
PYTHON_MAJOR=$(python -c "import sys; print(sys.version_info.major)")
PYTHON_MINOR=$(python -c "import sys; print(sys.version_info.minor)")
if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 12 ]; }; then
    echo "✗ Python >= 3.12 required (found $PYTHON_VERSION)"
    exit 1
fi

# ─── Step 1: Create virtual environment ─────────────────────────────────────
echo ""
echo "[2/7] Creating virtual environment..."

if [ -d "$VENV_DIR" ]; then
    echo "  Removing existing virtual environment..."
    rm -rf "$VENV_DIR"
fi

python -m venv "$VENV_DIR"
echo "  Virtual environment created at $VENV_DIR"

# ─── Step 2: Activate and install dependencies ──────────────────────────────
echo ""
echo "[3/7] Installing dependencies..."

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

pip install --upgrade pip -q

if [ -f "$ROOT_DIR/requirements.lock.txt" ]; then
    echo "  Installing from requirements.lock.txt..."
    pip install -r "$ROOT_DIR/requirements.lock.txt" -q
elif [ -f "$ROOT_DIR/requirements.txt" ]; then
    echo "  Installing from requirements.txt (no lock file found)..."
    pip install -r "$ROOT_DIR/requirements.txt" -q
    pip install -r "$ROOT_DIR/packages/backend/requirements.txt" -q
    pip install -r "$ROOT_DIR/packages/ml-engine/requirements.txt" -q
fi

echo "  Dependencies installed successfully."

# ─── Step 3: Capture environment snapshot ───────────────────────────────────
echo ""
echo "[4/7] Capturing environment snapshot..."

mkdir -p "$RESULTS_DIR"

python -c "
import json, os
from evaluation.config import get_hardware_info, get_git_info, get_package_versions

snapshot = {
    'timestamp': '$(date -u +%Y-%m-%dT%H:%M:%SZ)',
    'hardware': get_hardware_info(),
    'git': get_git_info(),
    'packages': get_package_versions(),
}
os.makedirs('$RESULTS_DIR', exist_ok=True)
json.dump(snapshot, open('$RESULTS_DIR/environment_snapshot.json', 'w'), indent=2)
print('  Environment snapshot saved.')
"

# ─── Step 4: Run benchmark ──────────────────────────────────────────────────
echo ""
echo "[5/7] Running benchmark..."

case "$MODE" in
    --quick|-q|quick)
        echo "  Mode: Quick smoke test"
        python -m evaluation.run_all --quick --output-dir "$RESULTS_DIR"
        ;;
    --validate|-v|validate|phase2)
        echo "  Mode: Phase 2 validation (90 runs)"
        python -c "
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname('$ROOT_DIR'), '..'))
os.chdir('$ROOT_DIR')
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
from evaluation._run_benchmark import *
" 2>&1 || python "$ROOT_DIR/evaluation/_run_benchmark.py"
        # Copy results if they went to default location
        if [ -d "$ROOT_DIR/evaluation/results/phase2_validation" ]; then
            cp -r "$ROOT_DIR/evaluation/results/phase2_validation" "$RESULTS_DIR/"
        fi
        ;;
    --full|-f|full|*)
        echo "  Mode: Full Phase 2 benchmark (300 runs)"
        echo "  Estimated time: ~40 minutes"
        python -c "
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname('$ROOT_DIR'), '..'))
os.chdir('$ROOT_DIR')
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
from evaluation._phase2_benchmark import *
" 2>&1 || python "$ROOT_DIR/evaluation/_phase2_benchmark.py"
        # Copy results if they went to default location
        if [ -d "$ROOT_DIR/evaluation/results/phase2_complete" ]; then
            cp -r "$ROOT_DIR/evaluation/results/phase2_complete" "$RESULTS_DIR/"
        fi
        ;;
esac

echo "  Benchmark complete."

# ─── Step 5: Verify results ─────────────────────────────────────────────────
echo ""
echo "[6/7] Verifying results..."

python -c "
import json, os, sys
sys.path.insert(0, '$ROOT_DIR')

from evaluation.reproducibility import ReproducibilityPackage

# Look for reference snapshot
ref_path = '$ROOT_DIR/evaluation/results/phase2_complete/reproducibility_snapshot.json'
new_snapshots = list(filter(lambda f: f.endswith('.json') and 'snapshot' in f,
                           [os.path.join(dp, f) for dp, dn, filenames in os.walk('$RESULTS_DIR') for f in filenames]))

if os.path.exists(ref_path) and new_snapshots:
    pkg = ReproducibilityPackage()
    ref = json.load(open(ref_path))
    new = json.load(open(new_snapshots[0]))
    verdict = pkg.verify_reproducibility(ref, new)
    print(json.dumps(verdict, indent=2))

    if verdict['overall'] == 'fully_reproducible':
        print('  ✅ Results are FULLY REPRODUCIBLE')
    elif verdict['overall'] == 'partially_reproducible':
        print('  ⚠️  Results are PARTIALLY REPRODUCIBLE')
        for k, v in verdict.items():
            if isinstance(v, dict):
                for kk, vv in v.items():
                    if not vv:
                        print(f'     Mismatch: {k}.{kk}')
            elif not v:
                print(f'     Mismatch: {k}')
    else:
        print('  ❌ Results are NOT REPRODUCIBLE')
else:
    if not os.path.exists(ref_path):
        print('  ⚠️  No reference snapshot found at $ref_path')
    if not new_snapshots:
        print('  ⚠️  No new snapshot found in results')
        # Try a broader search
        all_json = list(filter(lambda f: f.endswith('.json'),
            [os.path.join(dp, f) for dp, dn, filenames in os.walk('$RESULTS_DIR') for f in filenames]))
        print(f'     Files in results: {all_json}')
"

# ─── Step 6: Generate figures and report ────────────────────────────────────
echo ""
echo "[7/7] Generating figures and report..."

python -c "
import json, os, sys, glob
sys.path.insert(0, '$ROOT_DIR')
os.chdir('$ROOT_DIR')

from evaluation.visualization import PublicationVisualizer
from evaluation.report import PublicationReport
from evaluation.export import ExperimentResults
from evaluation.config import ExperimentConfig

# Find the latest results file
results_files = glob.glob('$RESULTS_DIR/**/results.json', recursive=True)
if not results_files:
    results_files = glob.glob('$RESULTS_DIR/**/summary.json', recursive=True)
if not results_files:
    results_files = glob.glob('evaluation/results/phase2_complete/results.json', recursive=True)

if results_files:
    latest = results_files[0]
    print(f'  Using results: {latest}')
    results = ExperimentResults(**json.load(open(latest)))

    # Generate figures
    viz = PublicationVisualizer()
    fig_dir = os.path.join(os.path.dirname(latest), 'figures')
    os.makedirs(fig_dir, exist_ok=True)
    try:
        figure_paths = viz.generate_all_figures(results, fig_dir)
        print(f'  Generated {len(figure_paths)} figures in {fig_dir}')
    except Exception as e:
        print(f'  Figure generation failed (may need matplotlib): {e}')
        figure_paths = []

    # Generate report
    report = PublicationReport()
    config_path = os.path.join(os.path.dirname(latest), 'config.json')
    if os.path.exists(config_path):
        try:
            report.config = ExperimentConfig(**json.load(open(config_path)))
        except Exception:
            pass
    report_path = os.path.join(os.path.dirname(latest), 'report.md')
    report.generate_report(results, figure_paths, str(os.path.dirname(latest)))
    print(f'  Report saved: {report_path}')
else:
    print('  No results found for figure/report generation.')
    print(f'  Searched in: $RESULTS_DIR')
"

# ─── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo "========================================================================"
echo "  REPRODUCTION COMPLETE"
echo "========================================================================"
echo "  Mode:       $MODE"
echo "  Results:    $RESULTS_DIR"
echo "  Python:     $PYTHON_VERSION"
echo "  Working directory: $ROOT_DIR"
echo ""
echo "  To view results:"
echo "    ls -la $RESULTS_DIR/"
echo ""
echo "  To verify manually:"
echo "    source $VENV_DIR/bin/activate"
echo "    python -m evaluation.run_all --config $RESULTS_DIR/config.json"
echo ""
echo "========================================================================"
