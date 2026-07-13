import logging
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from training.ewc import ElasticWeightConsolidation
from training.replay_buffer import ReplayBuffer, ReplayBufferConfig
from training.drift_detector import DriftDetector, DriftConfig, DriftAlert

logger = logging.getLogger(__name__)


@dataclass
class ContinualLearningConfig:
    ewc_lambda: float = 0.4
    ewc_online: bool = True
    ewc_gamma: float = 0.9
    replay_capacity: int = 10000
    replay_strategy: str = "uniform"
    drift_window: int = 100
    drift_warning_threshold: float = 2.0
    drift_threshold: float = 3.0
    auto_ewc: bool = True
    auto_replay: bool = True


class ContinualLearningManager:
    def __init__(self, config: Optional[ContinualLearningConfig] = None) -> None:
        self._config = config or ContinualLearningConfig()
        self._lock = threading.RLock()
        self._model: Any = None
        self._ewc: Optional[ElasticWeightConsolidation] = None
        self._replay_buffer: Optional[ReplayBuffer] = None
        self._drift_detector: Optional[DriftDetector] = None
        self._tasks: dict[str, dict[str, Any]] = {}
        self._init_components()

    def _init_components(self) -> None:
        replay_config = ReplayBufferConfig(
            capacity=self._config.replay_capacity,
            sampling_strategy=self._config.replay_strategy,
        )
        self._replay_buffer = ReplayBuffer(replay_config)

        drift_config = DriftConfig(
            window_size=self._config.drift_window,
            warning_threshold=self._config.drift_warning_threshold,
            drift_threshold=self._config.drift_threshold,
        )
        self._drift_detector = DriftDetector(drift_config)
        self._drift_detector.register_callback(self._on_drift_alert)

    def register_model(self, model: Any) -> None:
        with self._lock:
            self._model = model
            self._ewc = ElasticWeightConsolidation(
                model,
                ewc_lambda=self._config.ewc_lambda,
                online=self._config.ewc_online,
                gamma=self._config.ewc_gamma,
            )
            logger.info("Model registered with EWC (lambda=%.2f, online=%s)", self._config.ewc_lambda, self._config.ewc_online)

    def add_task(self, task_id: str, metadata: Optional[dict] = None) -> dict[str, Any]:
        with self._lock:
            if task_id in self._tasks:
                return self._tasks[task_id]
            task = {
                "task_id": task_id,
                "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
                "samples_added": 0,
                "ewc_estimated": False,
                "drift_alerts": 0,
                "metadata": metadata or {},
            }
            self._tasks[task_id] = task
            logger.info("Continual learning task added: %s", task_id)
            return task

    def record_sample(
        self,
        input_data: list[float],
        target: Any = None,
        task_id: str = "default",
        importance: float = 0.5,
        confidence: float = 0.0,
        loss: float = 0.0,
        metadata: Optional[dict] = None,
    ) -> None:
        with self._lock:
            if task_id not in self._tasks:
                self.add_task(task_id)
            self._tasks[task_id]["samples_added"] += 1
            if self._config.auto_replay:
                self._replay_buffer.add(
                    input_data=input_data,
                    target=target,
                    task_id=task_id,
                    importance=importance,
                    metadata=metadata,
                )
            if confidence > 0:
                self._drift_detector.record("confidence", confidence)
            if loss > 0:
                self._drift_detector.record("loss", loss)

    def estimate_ewc(self, task_id: str, dataset: Any, num_samples: int = 200) -> dict[str, Any]:
        with self._lock:
            if self._ewc is None:
                return {"error": "No model registered"}
            self._ewc.estimate_fisher(dataset, num_samples=num_samples)
            if task_id in self._tasks:
                self._tasks[task_id]["ewc_estimated"] = True
            return {
                "task_id": task_id,
                "status": "estimated",
                "importance_scores": self._ewc.get_importance_scores(),
                "ewc_state": self._ewc.get_state(),
            }

    def sample_replay(self, n: int = 32, task_id: Optional[str] = None) -> list[dict[str, Any]]:
        with self._lock:
            samples = self._replay_buffer.sample(n, task_id=task_id)
            return [
                {
                    "sample_id": s.sample_id,
                    "input_data": s.input_data,
                    "target": s.target,
                    "task_id": s.task_id,
                    "importance": s.importance,
                }
                for s in samples
            ]

    def detect_drift(self, metric_name: str = "confidence", value: float = 0.0) -> dict[str, Any]:
        with self._lock:
            self._drift_detector.record(metric_name, value)
            return self._drift_detector.get_current_state(metric_name)

    def _on_drift_alert(self, alert: DriftAlert) -> None:
        for task in self._tasks.values():
            if alert.severity == "drift":
                task["drift_alerts"] = task.get("drift_alerts", 0) + 1

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            ewc_state = self._ewc.get_state() if self._ewc else {}
            replay_stats = self._replay_buffer.get_stats() if self._replay_buffer else {}
            drift_stats = self._drift_detector.get_stats() if self._drift_detector else {}
            return {
                "config": {
                    "ewc_lambda": self._config.ewc_lambda,
                    "replay_capacity": self._config.replay_capacity,
                    "drift_window": self._config.drift_window,
                },
                "ewc": ewc_state,
                "replay_buffer": replay_stats,
                "drift_detector": drift_stats,
                "tasks": list(self._tasks.keys()),
                "task_count": len(self._tasks),
                "total_samples": sum(t["samples_added"] for t in self._tasks.values()),
            }

    def get_task(self, task_id: str) -> Optional[dict[str, Any]]:
        return self._tasks.get(task_id)

    def get_drift_alerts(self, n: int = 10) -> list[dict[str, Any]]:
        return self._drift_detector.get_recent_alerts(n) if self._drift_detector else []

    def get_drift_state(self, metric_name: str = "confidence") -> dict[str, Any]:
        return self._drift_detector.get_current_state(metric_name) if self._drift_detector else {"available": False}
