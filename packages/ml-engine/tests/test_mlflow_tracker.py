import json
import os
import tempfile

import pytest

from training.mlflow_tracker import (
    GPUTracker,
    MLflowConfig,
    MLflowExperimentTracker,
)


class TestMLflowConfig:
    def test_default_config(self):
        config = MLflowConfig()
        assert config.tracking_uri == "http://localhost:5000"
        assert config.experiment_name == "veriunlearn"
        assert config.auto_log is True
        assert config.log_model_params is True
        assert config.log_gpu_metrics is True
        assert config.log_checkpoints is True
        assert config.nested_runs is True

    def test_custom_config(self):
        config = MLflowConfig(
            tracking_uri="http://custom:5001",
            experiment_name="my_experiment",
            auto_log=False,
        )
        assert config.tracking_uri == "http://custom:5001"
        assert config.experiment_name == "my_experiment"
        assert config.auto_log is False


class TestGPUTracker:
    def test_snapshot(self):
        tracker = GPUTracker()
        snap = tracker.snapshot()
        assert "timestamp" in snap
        assert "available" in snap
        assert "memory_used_mb" in snap
        assert "utilization_pct" in snap

    def test_snapshot_no_gpu(self):
        tracker = GPUTracker()
        snap = tracker.snapshot()
        if not snap.get("available", False):
            assert snap["memory_used_mb"] == 0
            assert snap["memory_total_mb"] == 0

    def test_multiple_snapshots(self):
        tracker = GPUTracker()
        tracker.snapshot()
        tracker.snapshot()
        tracker.snapshot()
        timeline = tracker.get_timeline()
        assert len(timeline) == 3

    def test_get_peak_memory_empty(self):
        tracker = GPUTracker()
        peak = tracker.get_peak_memory()
        assert peak["peak_memory_used_mb"] == 0
        assert peak["snapshot_count"] == 0

    def test_get_peak_memory_with_snapshots(self):
        tracker = GPUTracker()
        tracker.snapshot()
        peak = tracker.get_peak_memory()
        assert peak["snapshot_count"] == 1

    def test_get_avg_utilization_empty(self):
        tracker = GPUTracker()
        avg = tracker.get_avg_utilization()
        assert avg == 0.0

    def test_get_avg_utilization_with_snapshots(self):
        tracker = GPUTracker()
        tracker.snapshot()
        avg = tracker.get_avg_utilization()
        assert isinstance(avg, float)

    def test_timeline_returns_list(self):
        tracker = GPUTracker()
        tracker.snapshot()
        timeline = tracker.get_timeline()
        assert isinstance(timeline, list)
        assert len(timeline) == 1


class TestMLflowExperimentTracker:
    def test_init(self):
        tracker = MLflowExperimentTracker()
        assert tracker.config is not None
        assert tracker.config.experiment_name == "veriunlearn"
        assert tracker.gpu_tracker is not None

    def test_init_custom_config(self):
        config = MLflowConfig(experiment_name="custom")
        tracker = MLflowExperimentTracker(config)
        assert tracker.config.experiment_name == "custom"

    def test_setup_graceful(self):
        tracker = MLflowExperimentTracker()
        result = tracker.setup()
        assert isinstance(result, bool)

    def test_start_training_run_no_mlflow(self):
        tracker = MLflowExperimentTracker()
        result = tracker.start_training_run("test-model", {"lr": 0.001})
        from training.mlflow_tracker import MLFLOW_AVAILABLE
        if not MLFLOW_AVAILABLE:
            assert result is None

    def test_log_training_metrics_no_run(self):
        tracker = MLflowExperimentTracker()
        tracker.log_training_metrics({"loss": 0.5}, step=1)
        # Should not raise

    def test_log_eval_metrics_no_run(self):
        tracker = MLflowExperimentTracker()
        tracker.log_eval_metrics({"accuracy": 0.9}, step=1)
        # Should not raise

    def test_log_gpu_metrics_no_run(self):
        tracker = MLflowExperimentTracker()
        tracker.log_gpu_metrics()
        # Should not raise

    def test_log_training_curves_no_run(self):
        tracker = MLflowExperimentTracker()
        tracker.log_training_curves([
            {"step": 1, "train_loss": 0.5, "eval_loss": 0.6},
            {"step": 2, "train_loss": 0.4, "eval_loss": 0.5},
        ])
        # Should not raise

    def test_end_training_run_no_run(self):
        tracker = MLflowExperimentTracker()
        tracker.end_training_run()
        # Should not raise

    def test_compare_runs_no_mlflow(self):
        tracker = MLflowExperimentTracker()
        result = tracker.compare_runs(["run1", "run2"])
        from training.mlflow_tracker import MLFLOW_AVAILABLE
        if not MLFLOW_AVAILABLE:
            assert "error" in result

    def test_get_experiment_runs_no_mlflow(self):
        tracker = MLflowExperimentTracker()
        result = tracker.get_experiment_runs()
        assert isinstance(result, list)

    def test_get_run_details_no_mlflow(self):
        tracker = MLflowExperimentTracker()
        result = tracker.get_run_details("nonexistent")
        from training.mlflow_tracker import MLFLOW_AVAILABLE
        if not MLFLOW_AVAILABLE:
            assert "error" in result

    def test_search_best_run_no_mlflow(self):
        tracker = MLflowExperimentTracker()
        result = tracker.search_best_run()
        from training.mlflow_tracker import MLFLOW_AVAILABLE
        if not MLFLOW_AVAILABLE:
            assert result is None

    def test_get_experiment_stats_no_mlflow(self):
        tracker = MLflowExperimentTracker()
        result = tracker.get_experiment_stats()
        from training.mlflow_tracker import MLFLOW_AVAILABLE
        if not MLFLOW_AVAILABLE:
            assert "error" in result

    def test_get_gpu_info(self):
        tracker = MLflowExperimentTracker()
        info = tracker._get_gpu_info()
        assert "available" in info

    def test_track_run_context_manager(self):
        tracker = MLflowExperimentTracker()
        from training.mlflow_tracker import MLFLOW_AVAILABLE
        with tracker.track_run("test-model", {"lr": 0.01}) as run_id:
            if MLFLOW_AVAILABLE:
                assert run_id is not None
            else:
                assert run_id is None

    def test_log_model_artifact_no_run(self):
        tracker = MLflowExperimentTracker()
        tracker.log_model_artifact("/nonexistent/path", "test_model")
        # Should not raise

    def test_log_adapter_config_no_run(self):
        tracker = MLflowExperimentTracker()
        tracker.log_adapter_config({"r": 16, "alpha": 32})
        # Should not raise

    def test_log_dataset_info_no_run(self):
        tracker = MLflowExperimentTracker()
        tracker.log_dataset_info("abc123", 1000, 20)
        # Should not raise
