from __future__ import annotations

import time
from typing import Any

from loguru import logger


class MLflowTracker:
    """MLflow experiment tracking integration.

    Tracks training runs, unlearning operations, and model metrics
    using MLflow. Falls back to local logging if MLflow server
    is not available.
    """

    def __init__(self, tracking_uri: str | None = None) -> None:
        self.tracking_uri = tracking_uri
        self._client = None
        self._experiment_id = None
        self._run_id = None

    def _ensure_client(self) -> bool:
        if self._client is not None:
            return True
        try:
            import mlflow
            if self.tracking_uri:
                mlflow.set_tracking_uri(self.tracking_uri)
            self._client = mlflow
            return True
        except ImportError:
            logger.info("MLflow not installed, using local logging")
            return False
        except Exception as e:
            logger.warning(f"MLflow connection failed: {e}")
            return False

    def create_experiment(self, name: str, tags: dict[str, str] | None = None) -> str | None:
        if not self._ensure_client():
            return None
        try:
            mlflow = self._client
            experiment = mlflow.set_experiment(name)
            self._experiment_id = experiment.experiment_id
            return self._experiment_id
        except Exception as e:
            logger.warning(f"MLflow experiment creation failed: {e}")
            return None

    def start_run(self, run_name: str | None = None, tags: dict[str, str] | None = None) -> str | None:
        if not self._ensure_client():
            return None
        try:
            mlflow = self._client
            run = mlflow.start_run(run_name=run_name, tags=tags)
            self._run_id = run.info.run_id
            return self._run_id
        except Exception as e:
            logger.warning(f"MLflow run start failed: {e}")
            return None

    def log_params(self, params: dict[str, Any]) -> None:
        if not self._ensure_client() or not self._run_id:
            return
        try:
            mlflow = self._client
            for key, value in params.items():
                mlflow.log_param(key, str(value))
        except Exception as e:
            logger.warning(f"MLflow param logging failed: {e}")

    def log_metrics(self, metrics: dict[str, float], step: int | None = None) -> None:
        if not self._ensure_client() or not self._run_id:
            return
        try:
            mlflow = self._client
            for key, value in metrics.items():
                mlflow.log_metric(key, value, step=step)
        except Exception as e:
            logger.warning(f"MLflow metric logging failed: {e}")

    def log_artifact(self, local_path: str) -> None:
        if not self._ensure_client() or not self._run_id:
            return
        try:
            mlflow = self._client
            mlflow.log_artifact(local_path)
        except Exception as e:
            logger.warning(f"MLflow artifact logging failed: {e}")

    def log_model(self, model, artifact_path: str) -> None:
        if not self._ensure_client() or not self._run_id:
            return
        try:
            mlflow = self._client
            mlflow.pytorch.log_model(model, artifact_path)
        except Exception as e:
            logger.warning(f"MLflow model logging failed: {e}")

    def end_run(self, status: str = "COMPLETED") -> None:
        if not self._ensure_client() or not self._run_id:
            return
        try:
            mlflow = self._client
            mlflow.end_run(status=status)
            self._run_id = None
        except Exception as e:
            logger.warning(f"MLflow run end failed: {e}")

    def track_training(
        self,
        experiment_name: str,
        run_name: str,
        params: dict[str, Any],
        metrics: dict[str, float],
        model=None,
        artifacts: list[str] | None = None,
    ) -> str | None:
        self.create_experiment(experiment_name)
        run_id = self.start_run(run_name)
        if not run_id:
            return None

        self.log_params(params)
        self.log_metrics(metrics)

        if model:
            self.log_model(model, "model")

        if artifacts:
            for path in artifacts:
                self.log_artifact(path)

        self.end_run()
        return run_id

    def track_unlearning(
        self,
        algorithm: str,
        num_deleted: int,
        params: dict[str, Any],
        metrics: dict[str, float],
    ) -> str | None:
        return self.track_training(
            experiment_name="unlearning",
            run_name=f"{algorithm}_{int(time.time())}",
            params={"algorithm": algorithm, "num_deleted": num_deleted, **params},
            metrics=metrics,
        )


mlflow_tracker = MLflowTracker()
