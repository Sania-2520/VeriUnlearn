"""Experiment configurations with full reproducibility support."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal


@dataclass
class SeedConfig:
    """Deterministic seed configuration for reproducibility."""
    global_seed: int = 42
    numpy_seed: int = 42
    torch_seed: int = 42
    cuda_seed: int = 42
    python_hash_seed: int = 42

    def apply(self) -> None:
        """Apply all seeds for full determinism."""
        import random

        import numpy as np
        import torch

        os.environ["PYTHONHASHSEED"] = str(self.python_hash_seed)
        random.seed(self.global_seed)
        np.random.seed(self.numpy_seed)
        torch.manual_seed(self.torch_seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(self.cuda_seed)
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False


@dataclass
class DatasetConfig:
    """Dataset configuration."""
    name: Literal["mnist", "cifar10", "imdb", "ag_news"]
    root: str = "evaluation/data"
    max_samples: int | None = None
    train_split: float = 0.8
    val_split: float = 0.1
    test_split: float = 0.1
    num_classes: int = 10
    input_shape: tuple[int, ...] = (1, 28, 28)
    vocab_size: int = 30000
    max_seq_length: int = 512

    normalize: bool = True
    mean: tuple[float, ...] = (0.1307,)
    std: tuple[float, ...] = (0.3081,)


@dataclass
class ModelConfig:
    """Model architecture configuration."""
    name: str = "logistic_regression"
    hidden_dim: int = 128
    num_layers: int = 2
    dropout: float = 0.1
    lora_r: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.1
    lora_target_modules: tuple[str, ...] = ("q_proj", "v_proj")


@dataclass
class TrainingConfig:
    """Training hyperparameters."""
    batch_size: int = 128
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    num_epochs: int = 10
    warmup_steps: int = 100
    max_grad_norm: float = 1.0
    optimizer: str = "adamw"
    scheduler: str = "cosine"
    early_stopping_patience: int = 5
    eval_every: int = 1


@dataclass
class UnlearningConfig:
    """Unlearning experiment configuration."""
    algorithms: tuple[str, ...] = (
        "retrain", "sisa", "scrub", "influence_functions", "fine_tune_forgetting"
    )
    forget_ratios: tuple[float, ...] = (0.01, 0.05, 0.10, 0.20, 0.50)
    num_runs: int = 5
    seed_start: int = 42


@dataclass
class PrivacyConfig:
    """Privacy attack configuration."""
    mia_num_samples: int = 1000
    mia_threshold_percentile: float = 50.0
    membership_leakage_bins: int = 50
    attack_confidence_level: float = 0.95


@dataclass
class OutputConfig:
    """Output and export configuration."""
    output_dir: str = "evaluation/results"
    export_csv: bool = True
    export_json: bool = True
    export_latex: bool = True
    export_figures: bool = True
    figure_format: str = "pdf"
    figure_dpi: int = 300
    latex_font_size: str = "small"
    journal_style: bool = True


@dataclass
class ExperimentConfig:
    """Master configuration for a complete experiment."""
    experiment_name: str = "veriunlearn_benchmark"
    description: str = "VeriUnlearn unlearning algorithm benchmark"
    seeds: SeedConfig = field(default_factory=SeedConfig)
    datasets: tuple[DatasetConfig, ...] = field(default_factory=lambda: (
        DatasetConfig(name="mnist", num_classes=10, input_shape=(1, 28, 28),
                      mean=(0.1307,), std=(0.3081,)),
        DatasetConfig(name="cifar10", num_classes=10, input_shape=(3, 32, 32),
                      mean=(0.4914, 0.4822, 0.4465), std=(0.2023, 0.1994, 0.2010)),
        DatasetConfig(name="imdb", num_classes=2, vocab_size=30000, max_seq_length=512,
                      input_shape=(512,)),
        DatasetConfig(name="ag_news", num_classes=4, vocab_size=30000, max_seq_length=256,
                      input_shape=(256,)),
    ))
    model: ModelConfig = field(default_factory=ModelConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    unlearning: UnlearningConfig = field(default_factory=UnlearningConfig)
    privacy: PrivacyConfig = field(default_factory=PrivacyConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    def fingerprint(self) -> str:
        """Generate a deterministic fingerprint of this configuration."""
        config_str = json.dumps(asdict(self), sort_keys=True, default=str)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return asdict(self)

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, default=str))

    @classmethod
    def load(cls, path: str | Path) -> ExperimentConfig:
        data = json.loads(Path(path).read_text())
        data["seeds"] = SeedConfig(**data.get("seeds", {}))
        data["model"] = ModelConfig(**data.get("model", {}))
        data["training"] = TrainingConfig(**data.get("training", {}))
        data["unlearning"] = UnlearningConfig(**data.get("unlearning", {}))
        data["privacy"] = PrivacyConfig(**data.get("privacy", {}))
        data["output"] = OutputConfig(**data.get("output", {}))
        data["datasets"] = tuple(DatasetConfig(**d) for d in data.get("datasets", ()))
        return cls(**data)


def get_hardware_info() -> dict:
    """Capture hardware configuration for reproducibility."""
    info: dict[str, Any] = {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "architecture": platform.architecture()[0],
        "machine": platform.machine(),
        "hostname": platform.node(),
    }
    try:
        import torch
        info["torch_version"] = torch.__version__
        info["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            info["cuda_version"] = torch.version.cuda
            info["gpu_name"] = torch.cuda.get_device_name(0)
            # ``total_memory`` is the modern torch attribute; fall back to the
            # older ``total_mem`` alias for compatibility with older releases.
            props = torch.cuda.get_device_properties(0)
            total_mem = getattr(props, "total_memory", getattr(props, "total_mem", 0))
            info["gpu_memory_gb"] = round(float(total_mem) / 1e9, 2)
    except ImportError:
        info["torch_version"] = "not installed"

    try:
        import numpy as np
        info["numpy_version"] = np.__version__
    except ImportError:
        pass

    try:
        import sklearn
        info["sklearn_version"] = sklearn.__version__
    except ImportError:
        pass

    try:
        import scipy
        info["scipy_version"] = scipy.__version__
    except ImportError:
        pass

    return info


def get_git_info() -> dict:
    """Capture git state for reproducibility."""
    info = {"commit": "unknown", "branch": "unknown", "dirty": False}
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            info["commit"] = result.stdout.strip()[:12]
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            info["branch"] = result.stdout.strip()
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            info["dirty"] = bool(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return info


def get_package_versions() -> dict[str, str]:
    """Get versions of key packages."""
    packages = {}
    for pkg in ["torch", "numpy", "scipy", "sklearn", "transformers",
                 "peft", "datasets", "pandas", "matplotlib", "seaborn"]:
        try:
            mod = __import__(pkg if pkg != "sklearn" else "sklearn")
            packages[pkg] = getattr(mod, "__version__", "unknown")
        except ImportError:
            packages[pkg] = "not installed"
    return packages
