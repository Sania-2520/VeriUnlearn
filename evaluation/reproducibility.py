"""Reproducibility package generator for VeriUnlearn experiments."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
import zipfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evaluation.config import ExperimentConfig, get_hardware_info, get_git_info, get_package_versions
from evaluation.export import ExperimentResults


class ReproducibilityPackage:
    """Generate complete reproducibility packages for experiments."""

    def generate_snapshot(self, config: ExperimentConfig, results: ExperimentResults) -> dict[str, Any]:
        """Capture a complete experiment snapshot for later comparison."""
        config_fingerprint = config.fingerprint()
        hardware = get_hardware_info()
        git_info = get_git_info()
        packages = get_package_versions()
        timestamp = datetime.now(timezone.utc).isoformat()

        completed_runs = [r for r in results.runs if r.success]
        failed_runs = [r for r in results.runs if not r.success]

        metric_summary: dict[str, dict[str, float]] = {}
        if completed_runs:
            flat = results.summary_flat()
            for algo, metrics in flat.items():
                metric_summary[algo] = {}
                for metric_name, stats in metrics.items():
                    metric_summary[algo][metric_name] = stats["mean"]

        snapshot: dict[str, Any] = {
            "config_fingerprint": config_fingerprint,
            "config": config.to_dict(),
            "timestamp": timestamp,
            "seeds": {
                "global_seed": config.seeds.global_seed,
                "numpy_seed": config.seeds.numpy_seed,
                "torch_seed": config.seeds.torch_seed,
                "cuda_seed": config.seeds.cuda_seed,
                "python_hash_seed": config.seeds.python_hash_seed,
            },
            "git": git_info,
            "environment": {
                "hardware": hardware,
                "python_version": platform.python_version(),
                "python_executable": sys.executable,
                "packages": packages,
            },
            "datasets": [
                {
                    "name": ds.name,
                    "hash": self._dataset_hash(ds),
                    "num_classes": ds.num_classes,
                    "input_shape": list(ds.input_shape),
                }
                for ds in config.datasets
            ],
            "results_summary": {
                "total_runs": results.num_runs,
                "completed_runs": len(completed_runs),
                "failed_runs": len(failed_runs),
                "algorithms": results.algorithm_names,
                "datasets": results.dataset_names,
                "metric_summary": metric_summary,
            },
        }
        return snapshot

    def create_reproducibility_zip(
        self,
        results: ExperimentResults,
        output_dir: str | Path,
    ) -> str:
        """Create a ZIP archive containing everything needed to reproduce."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        config = self._config_from_dict(results.config) if results.config else ExperimentConfig()
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        zip_name = f"reproducibility_{config.fingerprint()}_{timestamp_str}.zip"
        zip_path = output_dir / zip_name

        manifest: dict[str, str] = {}

        config_json = config.to_dict()
        config_content = json.dumps(config_json, indent=2, default=str)
        manifest["config.json"] = config_content

        results_dict = {
            "config": results.config,
            "algorithms": results.algorithm_names,
            "datasets": results.dataset_names,
            "metrics": results.metric_names,
            "num_runs": results.num_runs,
            "runs": [asdict(r) for r in results.runs],
        }
        results_content = json.dumps(results_dict, indent=2, default=str)
        manifest["results.json"] = results_content

        env_data = {
            "hardware": get_hardware_info(),
            "git": get_git_info(),
            "packages": get_package_versions(),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }
        manifest["environment.json"] = json.dumps(env_data, indent=2, default=str)

        requirements = self._generate_requirements_lock()
        manifest["requirements-lock.txt"] = requirements

        reproduce_sh = self._generate_reproduce_script(config)
        manifest["reproduce.sh"] = reproduce_sh

        reproduce_bat = self._generate_reproduce_batch(config)
        manifest["reproduce.bat"] = reproduce_bat

        readme = self._generate_readme(config, results, env_data)
        manifest["README.md"] = readme

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for filename, content in manifest.items():
                zf.writestr(filename, content)

        return str(zip_path)

    def verify_reproducibility(
        self,
        snapshot1: dict[str, Any],
        snapshot2: dict[str, Any],
    ) -> dict[str, Any]:
        """Check if two experiment runs are comparable.

        Returns a dict with match status for each category and overall verdict.
        """
        config_match = snapshot1.get("config_fingerprint") == snapshot2.get("config_fingerprint")

        seeds_match = snapshot1.get("seeds", {}) == snapshot2.get("seeds", {})

        env1 = snapshot1.get("environment", {})
        env2 = snapshot2.get("environment", {})
        packages_match = env1.get("packages", {}) == env2.get("packages", {})
        hw_match = _hardware_compatible(env1.get("hardware", {}), env2.get("hardware", {}))

        datasets1 = {d["name"]: d["hash"] for d in snapshot1.get("datasets", [])}
        datasets2 = {d["name"]: d["hash"] for d in snapshot2.get("datasets", [])}
        datasets_match = datasets1 == datasets2

        git1 = snapshot1.get("git", {})
        git2 = snapshot2.get("git", {})
        git_match = git1.get("commit") == git2.get("commit")

        results1 = snapshot1.get("results_summary", {})
        results2 = snapshot2.get("results_summary", {})
        num_runs_match = results1.get("completed_runs") == results2.get("completed_runs")

        overall = "fully_reproducible" if (
            config_match and seeds_match and packages_match and datasets_match
        ) else "partially_reproducible"

        return {
            "overall": overall,
            "config_match": config_match,
            "seeds_match": seeds_match,
            "environment": {
                "packages_match": packages_match,
                "hardware_compatible": hw_match,
            },
            "git_match": git_match,
            "datasets_match": datasets_match,
            "results": {
                "num_runs_match": num_runs_match,
                "snapshot1_completed": results1.get("completed_runs", 0),
                "snapshot2_completed": results2.get("completed_runs", 0),
            },
            "details": {
                "snapshot1_fingerprint": snapshot1.get("config_fingerprint"),
                "snapshot2_fingerprint": snapshot2.get("config_fingerprint"),
                "snapshot1_timestamp": snapshot1.get("timestamp"),
                "snapshot2_timestamp": snapshot2.get("timestamp"),
            },
        }

    @staticmethod
    def _config_from_dict(data: dict[str, Any]) -> ExperimentConfig:
        """Build an ExperimentConfig from a plain dict, converting nested dicts to dataclasses."""
        from evaluation.config import (
            SeedConfig, DatasetConfig, ModelConfig, TrainingConfig,
            UnlearningConfig, PrivacyConfig, OutputConfig,
        )

        data = dict(data)

        def _to_dc(cls, val):
            if isinstance(val, cls):
                return val
            if isinstance(val, dict):
                return cls(**val)
            return cls()

        data["seeds"] = _to_dc(SeedConfig, data.get("seeds", {}))
        data["model"] = _to_dc(ModelConfig, data.get("model", {}))
        data["training"] = _to_dc(TrainingConfig, data.get("training", {}))
        data["unlearning"] = _to_dc(UnlearningConfig, data.get("unlearning", {}))
        data["privacy"] = _to_dc(PrivacyConfig, data.get("privacy", {}))
        data["output"] = _to_dc(OutputConfig, data.get("output", {}))

        raw_datasets = data.get("datasets", [])
        if isinstance(raw_datasets, (list, tuple)):
            data["datasets"] = tuple(
                _to_dc(DatasetConfig, ds) if not isinstance(ds, DatasetConfig) else ds
                for ds in raw_datasets
            )

        return ExperimentConfig(**data)

    def generate_reproduce_script(self, config: ExperimentConfig) -> str:
        """Generate a bash script to reproduce the experiment."""
        return self._generate_reproduce_script(config)

    def _generate_reproduce_script(self, config: ExperimentConfig) -> str:
        """Internal bash script generator."""
        fp = config.fingerprint()
        lines = [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            f"# VeriUnlearn Reproducibility Script",
            f"# Config fingerprint: {fp}",
            f"# Generated: {datetime.now(timezone.utc).isoformat()}",
            "",
            'REPO_DIR="$(cd "$(dirname "$0")" && pwd)"',
            'cd "$REPO_DIR"',
            "",
            "echo '=== VeriUnlearn Experiment Reproduction ==='",
            f"echo 'Config fingerprint: {fp}'",
            "",
            "# Step 1: Create virtual environment",
            "if [ ! -d '.venv' ]; then",
            "    echo 'Creating virtual environment...'",
            "    python3 -m venv .venv",
            "fi",
            "",
            "# Step 2: Activate and install dependencies",
            'echo "Installing dependencies..."',
            "source .venv/bin/activate",
            "pip install --upgrade pip > /dev/null 2>&1",
            "if [ -f 'requirements-lock.txt' ]; then",
            "    pip install -r requirements-lock.txt > /dev/null 2>&1",
            "elif [ -f 'requirements.txt' ]; then",
            "    pip install -r requirements.txt > /dev/null 2>&1",
            "fi",
            "",
            "# Step 3: Set deterministic seeds",
            f"export PYTHONHASHSEED={config.seeds.python_hash_seed}",
            "",
            "# Step 4: Run experiment",
            "echo 'Running experiment...'",
            "python -m evaluation.run_all \\",
            "    --config config.json \\",
            "    --output-dir results/",
            "",
            "# Step 5: Verify results",
            "echo 'Experiment complete. Results saved to results/'",
            "echo '=== Done ==='",
            "",
        ]
        return "\n".join(lines)

    def _generate_reproduce_batch(self, config: ExperimentConfig) -> str:
        """Generate a Windows batch script to reproduce the experiment."""
        fp = config.fingerprint()
        lines = [
            "@echo off",
            "setlocal enabledelayedexpansion",
            f"REM VeriUnlearn Reproducibility Script",
            f"REM Config fingerprint: {fp}",
            f"REM Generated: {datetime.now(timezone.utc).isoformat()}",
            "",
            'set "REPO_DIR=%~dp0"',
            'cd /d "%REPO_DIR%"',
            "",
            "echo === VeriUnlearn Experiment Reproduction ===",
            f"echo Config fingerprint: {fp}",
            "",
            "REM Step 1: Create virtual environment",
            "if not exist .venv (",
            "    echo Creating virtual environment...",
            "    python -m venv .venv",
            ")",
            "",
            "REM Step 2: Activate and install dependencies",
            "echo Installing dependencies...",
            "call .venv\\Scripts\\activate.bat",
            "pip install --upgrade pip >nul 2>&1",
            "if exist requirements-lock.txt (",
            "    pip install -r requirements-lock.txt >nul 2>&1",
            ") else if exist requirements.txt (",
            "    pip install -r requirements.txt >nul 2>&1",
            ")",
            "",
            f"REM Step 3: Set deterministic seeds",
            f"set PYTHONHASHSEED={config.seeds.python_hash_seed}",
            "",
            "REM Step 4: Run experiment",
            "echo Running experiment...",
            "python -m evaluation.run_all --config config.json --output-dir results\\",
            "",
            "REM Step 5: Verify results",
            "echo Experiment complete. Results saved to results\\",
            "echo === Done ===",
            "",
        ]
        return "\n".join(lines)

    def _generate_readme(
        self,
        config: ExperimentConfig,
        results: ExperimentResults,
        env_data: dict,
    ) -> str:
        """Generate a README with reproduction instructions."""
        hw = env_data.get("hardware", {})
        git = env_data.get("git", {})
        pkgs = env_data.get("packages", {})

        completed = sum(1 for r in results.runs if r.success)
        total = results.num_runs

        lines = [
            "# VeriUnlearn Reproducibility Package",
            "",
            "## Experiment Details",
            "",
            f"- **Experiment Name**: {config.experiment_name}",
            f"- **Description**: {config.description}",
            f"- **Config Fingerprint**: `{config.fingerprint()}`",
            f"- **Timestamp**: {env_data.get('captured_at', 'unknown')}",
            "",
            "## Environment",
            "",
            f"- **Platform**: {hw.get('platform', 'unknown')}",
            f"- **Python**: {env_data.get('python_version', 'unknown')}",
            f"- **Git Commit**: `{git.get('commit', 'unknown')}`",
            f"- **Git Branch**: {git.get('branch', 'unknown')}",
            f"- **Git Dirty**: {git.get('dirty', 'unknown')}",
            "",
            "### Key Package Versions",
            "",
        ]
        for pkg, ver in pkgs.items():
            if ver != "not installed":
                lines.append(f"- **{pkg}**: {ver}")
        lines.extend([
            "",
            "## Results Summary",
            "",
            f"- **Algorithms**: {', '.join(results.algorithm_names)}",
            f"- **Datasets**: {', '.join(results.dataset_names)}",
            f"- **Metrics**: {', '.join(results.metric_names)}",
            f"- **Completed Runs**: {completed}/{total}",
            "",
            "## Files in this Package",
            "",
            "| File | Description |",
            "|------|-------------|",
            "| `config.json` | Full experiment configuration |",
            "| `results.json` | Complete experiment results |",
            "| `environment.json` | Hardware and software environment |",
            "| `requirements-lock.txt` | Exact package versions |",
            "| `reproduce.sh` | Linux/macOS reproduction script |",
            "| `reproduce.bat` | Windows reproduction script |",
            "",
            "## How to Reproduce",
            "",
            "### Linux/macOS",
            "```bash",
            "chmod +x reproduce.sh",
            "./reproduce.sh",
            "```",
            "",
            "### Windows",
            "```cmd",
            "reproduce.bat",
            "```",
            "",
            "### Manual Steps",
            "",
            "1. Create a virtual environment: `python -m venv .venv`",
            "2. Activate it: `source .venv/bin/activate` (Linux) or `.venv\\Scripts\\activate` (Windows)",
            "3. Install dependencies: `pip install -r requirements-lock.txt`",
            "4. Set seed: `export PYTHONHASHSEED=" + str(config.seeds.python_hash_seed) + "`",
            "5. Run: `python -m evaluation.run_all --config config.json`",
            "",
            "## Seeding",
            "",
            f"- Global seed: {config.seeds.global_seed}",
            f"- NumPy seed: {config.seeds.numpy_seed}",
            f"- PyTorch seed: {config.seeds.torch_seed}",
            f"- CUDA seed: {config.seeds.cuda_seed}",
            f"- PYTHONHASHSEED: {config.seeds.python_hash_seed}",
            "",
        ])
        return "\n".join(lines)

    def _generate_requirements_lock(self) -> str:
        """Generate an exact-version requirements file from the current environment."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "freeze"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        pkgs = get_package_versions()
        lines = [f"{pkg}=={ver}" for pkg, ver in pkgs.items() if ver != "not installed"]
        return "\n".join(lines)

    @staticmethod
    def _dataset_hash(dataset_config: Any) -> str:
        """Generate a deterministic hash for a dataset configuration."""
        if hasattr(dataset_config, "__dict__"):
            data = json.dumps(vars(dataset_config), sort_keys=True, default=str)
        else:
            data = json.dumps(dataset_config, sort_keys=True, default=str)
        return hashlib.sha256(data.encode()).hexdigest()[:16]


def _hardware_compatible(hw1: dict, hw2: dict) -> bool:
    """Check if two hardware environments are broadly compatible.

    We only require same architecture and GPU model — speed differences
    are expected across different CPU/GPU generations.
    """
    if hw1.get("architecture") != hw2.get("architecture"):
        return False
    gpu1 = hw1.get("gpu_name", "")
    gpu2 = hw2.get("gpu_name", "")
    if gpu1 and gpu2:
        return gpu1 == gpu2
    return True
