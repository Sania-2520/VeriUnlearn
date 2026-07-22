#!/usr/bin/env python3
"""Unit tests for evaluation.reproducibility — config, determinism, snapshots."""
from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import pytest

from evaluation.config import (
    ExperimentConfig,
    SeedConfig,
    DatasetConfig,
    ModelConfig,
    TrainingConfig,
    UnlearningConfig,
    PrivacyConfig,
    OutputConfig,
)
from evaluation.reproducibility import ReproducibilityPackage


# ═══════════════════════════════════════════════════════════════════════════
# 1. ExperimentConfig
# ═══════════════════════════════════════════════════════════════════════════


class TestExperimentConfig:
    def test_default_creation(self):
        config = ExperimentConfig()
        assert config.experiment_name == "veriunlearn_benchmark"
        assert config.seeds.global_seed == 42
        assert len(config.datasets) > 0

    def test_custom_creation(self):
        config = ExperimentConfig(
            experiment_name="test_exp",
            seeds=SeedConfig(global_seed=99, numpy_seed=99),
            datasets=(DatasetConfig(name="mnist", max_samples=100),),
            model=ModelConfig(name="mlp"),
            training=TrainingConfig(num_epochs=5),
        )
        assert config.experiment_name == "test_exp"
        assert config.seeds.global_seed == 99
        assert config.datasets[0].name == "mnist"
        assert config.model.name == "mlp"
        assert config.training.num_epochs == 5

    def test_fingerprint_deterministic(self):
        config = ExperimentConfig(experiment_name="fp_test")
        fp1 = config.fingerprint()
        fp2 = config.fingerprint()
        assert fp1 == fp2
        assert isinstance(fp1, str)
        assert len(fp1) == 16

    def test_fingerprint_differs_for_different_configs(self):
        a = ExperimentConfig(experiment_name="a")
        b = ExperimentConfig(experiment_name="b")
        assert a.fingerprint() != b.fingerprint()

    def test_to_dict_roundtrip(self):
        config = ExperimentConfig(experiment_name="roundtrip")
        d = config.to_dict()
        assert isinstance(d, dict)
        assert d["experiment_name"] == "roundtrip"
        assert isinstance(d["seeds"], dict)

    def test_save_and_load(self):
        config = ExperimentConfig(
            experiment_name="save_test",
            seeds=SeedConfig(global_seed=77),
            datasets=(DatasetConfig(name="mnist", max_samples=50),),
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            config.save(path)
            assert path.exists()
            loaded = ExperimentConfig.load(path)
            assert loaded.experiment_name == "save_test"
            assert loaded.seeds.global_seed == 77
            assert loaded.datasets[0].max_samples == 50

    def test_fingerprint_changes_with_dataset(self):
        a = ExperimentConfig(
            datasets=(DatasetConfig(name="mnist"),),
        )
        b = ExperimentConfig(
            datasets=(DatasetConfig(name="cifar10"),),
        )
        assert a.fingerprint() != b.fingerprint()


# ═══════════════════════════════════════════════════════════════════════════
# 2. SeedConfig
# ═══════════════════════════════════════════════════════════════════════════


class TestSeedConfig:
    def test_defaults(self):
        s = SeedConfig()
        assert s.global_seed == 42
        assert s.numpy_seed == 42
        assert s.torch_seed == 42
        assert s.cuda_seed == 42
        assert s.python_hash_seed == 42

    def test_custom_seeds(self):
        s = SeedConfig(global_seed=123, numpy_seed=456)
        assert s.global_seed == 123
        assert s.numpy_seed == 456


# ═══════════════════════════════════════════════════════════════════════════
# 3. Deterministic execution
# ═══════════════════════════════════════════════════════════════════════════


class TestDeterministicExecution:
    def test_numpy_same_seed_same_results(self):
        np.random.seed(42)
        a = np.random.rand(100)
        np.random.seed(42)
        b = np.random.rand(100)
        np.testing.assert_array_equal(a, b)

    def test_numpy_different_seed_different_results(self):
        np.random.seed(42)
        a = np.random.rand(100)
        np.random.seed(99)
        b = np.random.rand(100)
        assert not np.array_equal(a, b)

    def test_config_deterministic_fingerprint(self):
        """Same config objects always produce the same fingerprint."""
        configs = [
            ExperimentConfig(
                experiment_name="det_test",
                seeds=SeedConfig(global_seed=42),
                datasets=(DatasetConfig(name="mnist"),),
            )
            for _ in range(5)
        ]
        fingerprints = [c.fingerprint() for c in configs]
        assert len(set(fingerprints)) == 1


# ═══════════════════════════════════════════════════════════════════════════
# 4. ReproducibilityPackage — snapshot & verification
# ═══════════════════════════════════════════════════════════════════════════


def _make_mock_results():
    """Build a minimal ExperimentResults-like object for testing."""
    from evaluation.export import ExperimentResults, RunResult

    runs = [
        RunResult(
            run_id=0, algorithm="retrain", dataset="mnist", forget_ratio=0.10, seed=42,
            metrics={
                "accuracy": 0.88, "precision": 0.87, "recall": 0.86, "f1_score": 0.86,
                "forget_quality": 0.70, "utility_loss": 0.03, "knowledge_retention": 0.97,
                "mia_success_before": 0.65, "mia_success_after": 0.50,
                "privacy_leakage": 0.15, "trust_score": 75.0,
            },
            timing={"training_time": 10.0, "unlearning_time": 5.0, "speedup": 2.0},
            success=True,
        ),
    ]
    return ExperimentResults(
        config={"experiment_name": "test"},
        algorithm_names=["retrain"],
        dataset_names=["mnist"],
        metric_names=["accuracy"],
        runs=runs,
    )


class TestReproducibilityPackage:
    def test_generate_snapshot_structure(self):
        pkg = ReproducibilityPackage()
        config = ExperimentConfig(
            experiment_name="snap_test",
            seeds=SeedConfig(global_seed=42),
            datasets=(DatasetConfig(name="mnist", max_samples=100),),
        )
        results = _make_mock_results()
        snapshot = pkg.generate_snapshot(config, results)

        assert "config_fingerprint" in snapshot
        assert "seeds" in snapshot
        assert "environment" in snapshot
        assert "datasets" in snapshot
        assert "results_summary" in snapshot
        assert snapshot["seeds"]["global_seed"] == 42

    def test_snapshot_fingerprint_matches_config(self):
        pkg = ReproducibilityPackage()
        config = ExperimentConfig(
            experiment_name="fp_match",
            datasets=(DatasetConfig(name="mnist", max_samples=100),),
        )
        results = _make_mock_results()
        snapshot = pkg.generate_snapshot(config, results)
        assert snapshot["config_fingerprint"] == config.fingerprint()

    def test_verify_reproducibility_identical(self):
        pkg = ReproducibilityPackage()
        config = ExperimentConfig(
            experiment_name="verify_test",
            seeds=SeedConfig(global_seed=42),
            datasets=(DatasetConfig(name="mnist", max_samples=100),),
        )
        results = _make_mock_results()
        s1 = pkg.generate_snapshot(config, results)
        s2 = pkg.generate_snapshot(config, results)
        verdict = pkg.verify_reproducibility(s1, s2)
        assert verdict["overall"] == "fully_reproducible"
        assert verdict["config_match"] is True
        assert verdict["seeds_match"] is True

    def test_verify_reproducibility_different_configs(self):
        pkg = ReproducibilityPackage()
        c1 = ExperimentConfig(
            experiment_name="exp_a",
            seeds=SeedConfig(global_seed=42),
            datasets=(DatasetConfig(name="mnist", max_samples=100),),
        )
        c2 = ExperimentConfig(
            experiment_name="exp_b",
            seeds=SeedConfig(global_seed=42),
            datasets=(DatasetConfig(name="mnist", max_samples=100),),
        )
        results = _make_mock_results()
        s1 = pkg.generate_snapshot(c1, results)
        s2 = pkg.generate_snapshot(c2, results)
        verdict = pkg.verify_reproducibility(s1, s2)
        assert verdict["overall"] == "partially_reproducible"
        assert verdict["config_match"] is False

    def test_verify_different_seeds(self):
        pkg = ReproducibilityPackage()
        c1 = ExperimentConfig(seeds=SeedConfig(global_seed=42))
        c2 = ExperimentConfig(seeds=SeedConfig(global_seed=99))
        results = _make_mock_results()
        s1 = pkg.generate_snapshot(c1, results)
        s2 = pkg.generate_snapshot(c2, results)
        verdict = pkg.verify_reproducibility(s1, s2)
        assert verdict["seeds_match"] is False

    def test_config_from_dict_roundtrip(self):
        pkg = ReproducibilityPackage()
        original = ExperimentConfig(
            experiment_name="dict_test",
            seeds=SeedConfig(global_seed=77),
            datasets=(DatasetConfig(name="mnist", max_samples=100),),
        )
        d = original.to_dict()
        rebuilt = pkg._config_from_dict(d)
        assert rebuilt.experiment_name == "dict_test"
        assert rebuilt.seeds.global_seed == 77
        assert rebuilt.datasets[0].name == "mnist"


# ═══════════════════════════════════════════════════════════════════════════
# 5. Zip creation
# ═══════════════════════════════════════════════════════════════════════════


class TestReproducibilityZip:
    def test_zip_created_and_contents(self):
        pkg = ReproducibilityPackage()
        results = _make_mock_results()
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = pkg.create_reproducibility_zip(results, tmp)
            assert Path(zip_path).exists()
            with zipfile.ZipFile(zip_path, "r") as zf:
                names = zf.namelist()
                assert "config.json" in names
                assert "results.json" in names
                assert "environment.json" in names
                assert "README.md" in names
                assert "reproduce.sh" in names
                assert "reproduce.bat" in names

    def test_zip_config_json_valid(self):
        pkg = ReproducibilityPackage()
        results = _make_mock_results()
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = pkg.create_reproducibility_zip(results, tmp)
            with zipfile.ZipFile(zip_path, "r") as zf:
                config_data = json.loads(zf.read("config.json"))
                assert "experiment_name" in config_data
                assert "seeds" in config_data

    def test_reproduce_script_contains_fingerprint(self):
        pkg = ReproducibilityPackage()
        config = ExperimentConfig(
            experiment_name="script_test",
            datasets=(DatasetConfig(name="mnist", max_samples=100),),
        )
        script = pkg.generate_reproduce_script(config)
        assert config.fingerprint() in script
        assert "PYTHONHASHSEED" in script
