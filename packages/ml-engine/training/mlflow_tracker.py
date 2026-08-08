import json
import logging
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Generator, Optional

logger = logging.getLogger(__name__)

try:
    import mlflow
    import mlflow.pytorch
    import mlflow.sklearn
    from mlflow.tracking import MlflowClient

    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False

try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


@dataclass
class MLflowConfig:
    tracking_uri: str = "http://localhost:5000"
    experiment_name: str = "veriunlearn"
    artifact_location: str = "./mlflow_artifacts"
    auto_log: bool = True
    log_model_params: bool = True
    log_gpu_metrics: bool = True
    log_checkpoints: bool = True
    nested_runs: bool = True


class GPUTracker:
    def __init__(self) -> None:
        self._snapshots: list[dict] = []

    def snapshot(self) -> dict:
        if not TORCH_AVAILABLE or not torch.cuda.is_available():
            snap = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "available": False,
                "memory_used_mb": 0,
                "memory_total_mb": 0,
                "utilization_pct": 0,
                "temperature_c": 0,
            }
        else:
            device = torch.cuda.current_device()
            mem_used = torch.cuda.memory_allocated(device) / (1024**2)
            mem_total = torch.cuda.get_device_properties(device).total_memory / (1024**2)
            util = 0
            gpu_temp_c = 0
            try:
                import pynvml

                pynvml.nvmlInit()
                handle = pynvml.nvmlDeviceGetHandleByIndex(device)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
                gpu_temp_c = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            except Exception:
                logger.debug("pynvml GPU stats unavailable", exc_info=True)
            snap = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "available": True,
                "device": torch.cuda.get_device_name(device),
                "device_index": device,
                "memory_used_mb": round(mem_used, 2),
                "memory_total_mb": round(mem_total, 2),
                "memory_used_pct": round(100.0 * mem_used / mem_total, 2) if mem_total > 0 else 0,
                "utilization_pct": util,
                "temperature_c": gpu_temp_c,
            }
        self._snapshots.append(snap)
        return snap

    def get_peak_memory(self) -> dict:
        if not self._snapshots:
            return {"peak_memory_used_mb": 0, "peak_memory_pct": 0, "snapshot_count": 0}
        gpu_snaps = [s for s in self._snapshots if s.get("available", False)]
        if not gpu_snaps:
            return {"peak_memory_used_mb": 0, "peak_memory_pct": 0, "snapshot_count": len(self._snapshots)}
        peak_used = max(s["memory_used_mb"] for s in gpu_snaps)
        peak_pct = max(s.get("memory_used_pct", 0) for s in gpu_snaps)
        return {
            "peak_memory_used_mb": peak_used,
            "peak_memory_pct": peak_pct,
            "snapshot_count": len(self._snapshots),
            "gpu_available": True,
        }

    def get_avg_utilization(self) -> float:
        gpu_snaps = [s for s in self._snapshots if s.get("available", False)]
        if not gpu_snaps:
            return 0.0
        return sum(s["utilization_pct"] for s in gpu_snaps) / len(gpu_snaps)

    def get_timeline(self) -> list[dict]:
        return list(self._snapshots)


class MLflowExperimentTracker:
    def __init__(self, config: Optional[MLflowConfig] = None) -> None:
        self.config = config or MLflowConfig()
        self.client: Optional[MlflowClient] = None
        self.gpu_tracker = GPUTracker()
        self._active_run_id: Optional[str] = None
        self._run_start_time: float = 0.0
        if MLFLOW_AVAILABLE:
            self.client = MlflowClient()

    def setup(self) -> bool:
        if not MLFLOW_AVAILABLE:
            logger.warning("MLflow not installed — tracker disabled")
            return False
        try:
            mlflow.set_tracking_uri(self.config.tracking_uri)
            experiment = mlflow.get_experiment_by_name(self.config.experiment_name)
            if experiment is None:
                mlflow.create_experiment(
                    self.config.experiment_name,
                    artifact_location=self.config.artifact_location,
                )
                logger.info(
                    "Created MLflow experiment: %s", self.config.experiment_name
                )
            else:
                mlflow.set_experiment(self.config.experiment_name)
                logger.info(
                    "Using MLflow experiment: %s (id=%s)",
                    self.config.experiment_name,
                    experiment.experiment_id,
                )
            return True
        except Exception as exc:
            logger.error("MLflow setup failed: %s", exc)
            return False

    def start_training_run(
        self,
        model_name: str,
        config: dict,
        tags: Optional[dict] = None,
    ) -> Optional[str]:
        if not MLFLOW_AVAILABLE:
            return None
        try:
            run_name = f"train_{model_name}_{int(time.time())}"
            run_tags = {"model_name": model_name, "run_type": "training"}
            if tags:
                run_tags.update(tags)
            run = mlflow.start_run(run_name=run_name, nested=False)
            self._active_run_id = run.info.run_id
            self._run_start_time = time.time()
            for k, v in config.items():
                mlflow.log_param(k, v)
            mlflow.set_tags(run_tags)
            self._log_env_info()
            if self.config.log_gpu_metrics:
                self.gpu_tracker.snapshot()
                self.log_gpu_metrics()
            logger.info("Started training run: %s", self._active_run_id)
            return self._active_run_id
        except Exception as exc:
            logger.error("Failed to start training run: %s", exc)
            return None

    def log_training_metrics(
        self, metrics: dict, step: Optional[int] = None
    ) -> None:
        if not MLFLOW_AVAILABLE or self._active_run_id is None:
            return
        try:
            mlflow.log_metrics(metrics, step=step)
        except Exception as exc:
            logger.warning("Failed to log training metrics: %s", exc)

    def log_eval_metrics(
        self, metrics: dict, step: Optional[int] = None
    ) -> None:
        if not MLFLOW_AVAILABLE or self._active_run_id is None:
            return
        try:
            prefixed = {f"eval_{k}" if not k.startswith("eval_") else k: v for k, v in metrics.items()}
            mlflow.log_metrics(prefixed, step=step)
        except Exception as exc:
            logger.warning("Failed to log eval metrics: %s", exc)

    def log_model_artifact(
        self,
        model_path: str,
        artifact_name: str = "model",
        metadata: Optional[dict] = None,
    ) -> None:
        if not MLFLOW_AVAILABLE or self._active_run_id is None:
            return
        if not self.config.log_checkpoints:
            return
        try:
            if os.path.isdir(model_path):
                mlflow.log_artifacts(model_path, artifact_path=artifact_name)
            elif os.path.isfile(model_path):
                mlflow.log_artifact(model_path, artifact_path=artifact_name)
            if metadata:
                meta_path = os.path.join(
                    self.config.artifact_location, f"{artifact_name}_metadata.json"
                )
                os.makedirs(os.path.dirname(meta_path), exist_ok=True)
                with open(meta_path, "w") as f:
                    json.dump(metadata, f, indent=2, default=str)
                mlflow.log_artifact(meta_path, artifact_path=artifact_name)
            logger.info("Logged artifact '%s' from %s", artifact_name, model_path)
        except Exception as exc:
            logger.warning("Failed to log model artifact: %s", exc)

    def log_adapter_config(self, adapter_config: dict) -> None:
        if not MLFLOW_AVAILABLE or self._active_run_id is None:
            return
        if not self.config.log_model_params:
            return
        try:
            flat: dict[str, Any] = {}
            for k, v in adapter_config.items():
                if isinstance(v, (list, dict)):
                    flat[k] = json.dumps(v)
                else:
                    flat[k] = v
            mlflow.log_params(flat)
        except Exception as exc:
            logger.warning("Failed to log adapter config: %s", exc)

    def log_dataset_info(
        self, dataset_hash: str, dataset_size: int, features: int
    ) -> None:
        if not MLFLOW_AVAILABLE or self._active_run_id is None:
            return
        try:
            mlflow.log_params(
                {
                    "dataset_hash": dataset_hash,
                    "dataset_size": dataset_size,
                    "dataset_features": features,
                }
            )
        except Exception as exc:
            logger.warning("Failed to log dataset info: %s", exc)

    def log_gpu_metrics(self) -> None:
        if not MLFLOW_AVAILABLE or self._active_run_id is None:
            return
        if not self.config.log_gpu_metrics:
            return
        try:
            snap = self.gpu_tracker.snapshot()
            mlflow.log_metrics(
                {
                    "gpu_memory_used_mb": snap.get("memory_used_mb", 0),
                    "gpu_memory_total_mb": snap.get("memory_total_mb", 0),
                    "gpu_memory_pct": snap.get("memory_used_pct", 0),
                    "gpu_utilization_pct": snap.get("utilization_pct", 0),
                    "gpu_temperature_c": snap.get("temperature_c", 0),
                }
            )
        except Exception as exc:
            logger.warning("Failed to log GPU metrics: %s", exc)

    def log_training_curves(self, history: list[dict]) -> None:
        if not MLFLOW_AVAILABLE or self._active_run_id is None:
            return
        try:
            for entry in history:
                step = entry.get("step") or entry.get("global_step")
                metrics: dict[str, float] = {}
                for key in ("train_loss", "eval_loss", "learning_rate", "grad_norm"):
                    if key in entry and entry[key] is not None:
                        metrics[key] = float(entry[key])
                if "eval_perplexity" in entry and entry["eval_perplexity"] is not None:
                    metrics["eval_perplexity"] = float(entry["eval_perplexity"])
                if "train_samples_per_second" in entry:
                    metrics["samples_per_second"] = float(entry["train_samples_per_second"])
                if metrics:
                    mlflow.log_metrics(metrics, step=step)
        except Exception as exc:
            logger.warning("Failed to log training curves: %s", exc)

    def end_training_run(self, status: str = "COMPLETED") -> None:
        if not MLFLOW_AVAILABLE or self._active_run_id is None:
            return
        try:
            total_time = time.time() - self._run_start_time if self._run_start_time > 0 else 0
            mlflow.log_metric("total_training_time_seconds", total_time)
            if self.config.log_gpu_metrics:
                peak = self.gpu_tracker.get_peak_memory()
                avg_util = self.gpu_tracker.get_avg_utilization()
                mlflow.log_metrics(
                    {
                        "peak_gpu_memory_mb": peak.get("peak_memory_used_mb", 0),
                        "avg_gpu_utilization": avg_util,
                    }
                )
            mlflow.end_run(status=status)
            logger.info(
                "Ended run %s with status %s (%.1fs)",
                self._active_run_id,
                status,
                total_time,
            )
        except Exception as exc:
            logger.warning("Failed to end run: %s", exc)
        finally:
            self._active_run_id = None
            self._run_start_time = 0.0
            self.gpu_tracker = GPUTracker()

    def start_unlearning_run(
        self, algorithm: str, context: dict
    ) -> Optional[str]:
        if not MLFLOW_AVAILABLE or not self.config.nested_runs:
            return None
        try:
            run_name = f"unlearn_{algorithm}_{int(time.time())}"
            run = mlflow.start_run(
                run_name=run_name, nested=True, parent_run_id=self._active_run_id
            )
            mlflow.log_param("unlearning_algorithm", algorithm)
            mlflow.log_param("run_type", "unlearning")
            for k, v in context.items():
                if isinstance(v, (list, dict)):
                    mlflow.log_param(k, json.dumps(v))
                else:
                    mlflow.log_param(k, v)
            if self.config.log_gpu_metrics:
                self.gpu_tracker.snapshot()
                self.log_gpu_metrics()
            return run.info.run_id
        except Exception as exc:
            logger.warning("Failed to start unlearning run: %s", exc)
            return None

    def log_unlearning_result(self, result: dict) -> None:
        if not MLFLOW_AVAILABLE or self._active_run_id is None:
            return
        try:
            metrics: dict[str, float] = {}
            for k, v in result.items():
                if isinstance(v, (int, float)):
                    metrics[k] = float(v)
            if metrics:
                mlflow.log_metrics(metrics)
            for k, v in result.items():
                if isinstance(v, str):
                    mlflow.log_param(f"result_{k}", v)
        except Exception as exc:
            logger.warning("Failed to log unlearning result: %s", exc)

    def start_evaluation_run(
        self, eval_type: str, config: dict
    ) -> Optional[str]:
        if not MLFLOW_AVAILABLE:
            return None
        try:
            run_name = f"eval_{eval_type}_{int(time.time())}"
            parent_id = self._active_run_id
            run = mlflow.start_run(
                run_name=run_name, nested=(parent_id is not None and self.config.nested_runs),
                parent_run_id=parent_id if parent_id else None,
            )
            mlflow.log_param("eval_type", eval_type)
            mlflow.log_param("run_type", "evaluation")
            for k, v in config.items():
                if isinstance(v, (list, dict)):
                    mlflow.log_param(k, json.dumps(v))
                else:
                    mlflow.log_param(k, v)
            return run.info.run_id
        except Exception as exc:
            logger.warning("Failed to start evaluation run: %s", exc)
            return None

    def log_evaluation_result(self, results: dict) -> None:
        if not MLFLOW_AVAILABLE or self._active_run_id is None:
            return
        try:
            metrics: dict[str, float] = {}
            for k, v in results.items():
                if isinstance(v, (int, float)):
                    metrics[k] = float(v)
            if metrics:
                mlflow.log_metrics(metrics)
            nested_keys = {}
            for k, v in results.items():
                if isinstance(v, dict):
                    nested_keys[k] = v
            for k, v in nested_keys.items():
                for sub_k, sub_v in v.items():
                    if isinstance(sub_v, (int, float)):
                        metrics[f"{k}_{sub_k}"] = float(sub_v)
            if metrics:
                mlflow.log_metrics(metrics)
            for k, v in results.items():
                if isinstance(v, str):
                    mlflow.log_param(f"result_{k}", v)
        except Exception as exc:
            logger.warning("Failed to log evaluation result: %s", exc)

    def compare_runs(self, run_ids: list[str]) -> dict:
        if not MLFLOW_AVAILABLE or self.client is None:
            return {"error": "MLflow not available"}
        comparison: dict[str, Any] = {"runs": {}, "metric_comparison": {}}
        all_metrics: dict[str, list[tuple[str, float]]] = {}
        for rid in run_ids:
            try:
                run = self.client.get_run(rid)
                comparison["runs"][rid] = {
                    "status": run.info.status,
                    "start_time": run.info.start_time,
                    "run_name": run.data.tags.get("mlflow.runName", ""),
                }
                for mk, mv in run.data.metrics.items():
                    all_metrics.setdefault(mk, []).append((rid, float(mv)))
            except Exception as exc:
                comparison["runs"][rid] = {"error": str(exc)}
        for metric_name, values in all_metrics.items():
            numeric = [v for _, v in values]
            comparison["metric_comparison"][metric_name] = {
                rid: val for rid, val in values
            }
            if numeric:
                comparison["metric_comparison"][metric_name]["min"] = min(numeric)
                comparison["metric_comparison"][metric_name]["max"] = max(numeric)
                comparison["metric_comparison"][metric_name]["mean"] = sum(numeric) / len(numeric)
        return comparison

    def get_experiment_runs(self, max_results: int = 100) -> list[dict]:
        if not MLFLOW_AVAILABLE or self.client is None:
            return []
        try:
            experiment = mlflow.get_experiment_by_name(self.config.experiment_name)
            if experiment is None:
                return []
            runs = self.client.search_runs(
                experiment_ids=[experiment.experiment_id],
                max_results=max_results,
                order_by=["start_time DESC"],
            )
            return [
                {
                    "run_id": r.info.run_id,
                    "run_name": r.data.tags.get("mlflow.runName", ""),
                    "status": r.info.status,
                    "start_time": r.info.start_time,
                    "end_time": r.info.end_time,
                    "metrics": dict(r.data.metrics),
                    "params": dict(r.data.params),
                    "tags": {k: v for k, v in r.data.tags.items()},
                }
                for r in runs
            ]
        except Exception as exc:
            logger.warning("Failed to get experiment runs: %s", exc)
            return []

    def get_run_details(self, run_id: str) -> dict:
        if not MLFLOW_AVAILABLE or self.client is None:
            return {"error": "MLflow not available"}
        try:
            run = self.client.get_run(run_id)
            return {
                "run_id": run.info.run_id,
                "run_name": run.data.tags.get("mlflow.runName", ""),
                "status": run.info.status,
                "start_time": run.info.start_time,
                "end_time": run.info.end_time,
                "metrics": dict(run.data.metrics),
                "params": dict(run.data.params),
                "tags": dict(run.data.tags),
            }
        except Exception as exc:
            return {"error": str(exc)}

    def search_best_run(
        self, metric: str = "eval_loss", order: str = "asc"
    ) -> Optional[dict]:
        if not MLFLOW_AVAILABLE or self.client is None:
            return None
        try:
            experiment = mlflow.get_experiment_by_name(self.config.experiment_name)
            if experiment is None:
                return None
            ascending = order.lower() == "asc"
            runs = self.client.search_runs(
                experiment_ids=[experiment.experiment_id],
                order_by=[f"metrics.{metric} {'ASC' if ascending else 'DESC'}"],
                max_results=1,
            )
            if not runs:
                return None
            best = runs[0]
            return {
                "run_id": best.info.run_id,
                "run_name": best.data.tags.get("mlflow.runName", ""),
                "status": best.info.status,
                "best_metric": {metric: best.data.metrics.get(metric)},
                "metrics": dict(best.data.metrics),
                "params": dict(best.data.params),
            }
        except Exception as exc:
            logger.warning("Failed to search best run: %s", exc)
            return None

    def get_training_curves_data(self, run_id: str) -> dict:
        if not MLFLOW_AVAILABLE or self.client is None:
            return {"error": "MLflow not available"}
        try:
            run = self.client.get_run(run_id)
            metrics = run.data.metrics
            history = self.client.get_metric_history(run_id, "train_loss")
            curve_data: dict[str, Any] = {
                "train_loss": [{"step": m.step, "value": m.value, "timestamp": m.timestamp} for m in history],
            }
            for metric_name in ("eval_loss", "learning_rate", "grad_norm", "eval_perplexity"):
                mhist = self.client.get_metric_history(run_id, metric_name)
                if mhist:
                    curve_data[metric_name] = [
                        {"step": m.step, "value": m.value, "timestamp": m.timestamp}
                        for m in mhist
                    ]
            curve_data["summary"] = metrics
            return curve_data
        except Exception as exc:
            return {"error": str(exc)}

    def _get_gpu_info(self) -> dict:
        if not TORCH_AVAILABLE or not torch.cuda.is_available():
            return {"available": False}
        try:
            device = torch.cuda.get_device_properties(0)
            return {
                "available": True,
                "name": device.name,
                "total_memory_mb": round(device.total_memory / (1024**2), 2),
                "compute_capability": f"{device.major}.{device.minor}",
                "cuda_version": torch.version.cuda,
                "device_count": torch.cuda.device_count(),
            }
        except Exception:
            return {"available": False}

    def _log_env_info(self) -> None:
        if not MLFLOW_AVAILABLE:
            return
        try:
            env_info: dict[str, str] = {
                "pytorch_version": getattr(torch, "__version__", "N/A") if TORCH_AVAILABLE else "N/A",
            }
            if TORCH_AVAILABLE and torch.cuda.is_available():
                env_info["cuda_available"] = "true"
                env_info["cuda_version"] = str(torch.version.cuda)
                env_info["gpu_name"] = torch.cuda.get_device_name(0)
                gpu_info = self._get_gpu_info()
                env_info["gpu_memory_total_mb"] = str(gpu_info.get("total_memory_mb", ""))
            else:
                env_info["cuda_available"] = "false"
            import sys

            env_info["python_version"] = sys.version
            env_info["platform"] = sys.platform
            mlflow.log_params({f"env_{k}": v for k, v in env_info.items()})
        except Exception as exc:
            logger.warning("Failed to log env info: %s", exc)

    def get_experiment_stats(self) -> dict:
        if not MLFLOW_AVAILABLE or self.client is None:
            return {"error": "MLflow not available"}
        try:
            experiment = mlflow.get_experiment_by_name(self.config.experiment_name)
            if experiment is None:
                return {"error": "Experiment not found"}
            runs = self.client.search_runs(
                experiment_ids=[experiment.experiment_id],
                max_results=10000,
            )
            total_runs = len(runs)
            status_counts: dict[str, int] = {}
            all_metrics: dict[str, list[float]] = {}
            total_time = 0.0
            for r in runs:
                status = r.info.status
                status_counts[status] = status_counts.get(status, 0) + 1
                for mk, mv in r.data.metrics.items():
                    all_metrics.setdefault(mk, []).append(float(mv))
                if r.info.start_time and r.info.end_time:
                    total_time += (r.info.end_time - r.info.start_time) / 1000.0
            metric_stats: dict[str, Any] = {}
            for mk, vals in all_metrics.items():
                if vals:
                    metric_stats[mk] = {
                        "min": min(vals),
                        "max": max(vals),
                        "mean": sum(vals) / len(vals),
                        "count": len(vals),
                    }
            return {
                "experiment_name": self.config.experiment_name,
                "experiment_id": experiment.experiment_id,
                "total_runs": total_runs,
                "status_distribution": status_counts,
                "metric_summary": metric_stats,
                "total_time_seconds": round(total_time, 2),
                "total_time_hours": round(total_time / 3600, 2),
                "artifact_location": experiment.artifact_location,
            }
        except Exception as exc:
            return {"error": str(exc)}

    @contextmanager
    def track_run(
        self,
        model_name: str,
        config: dict,
        tags: Optional[dict] = None,
    ) -> Generator[Optional[str], None, None]:
        run_id = self.start_training_run(model_name, config, tags)
        try:
            yield run_id
        finally:
            self.end_training_run()
