import logging
import math
import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DriftConfig:
    window_size: int = 100
    warning_threshold: float = 2.0
    drift_threshold: float = 3.0
    min_samples: int = 30
    metric_names: list[str] = field(default_factory=lambda: ["confidence", "loss", "accuracy", "feature_importance"])
    reference_update_interval: int = 500


@dataclass
class DriftAlert:
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metric_name: str = ""
    drift_score: float = 0.0
    severity: str = "warning"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    details: dict = field(default_factory=dict)


class StatisticalDriftDetector:
    def _ks_test(self, reference: np.ndarray, current: np.ndarray) -> float:
        combined = np.concatenate([reference, current])
        sorted_combined = np.sort(combined)
        n1, n2 = len(reference), len(current)
        max_diff = 0.0
        i, j = 0, 0
        while i < n1 and j < n2:
            if reference[i] < current[j]:
                d = abs((i + 1) / n1 - j / n2)
                i += 1
            else:
                d = abs(i / n1 - (j + 1) / n2)
                j += 1
            max_diff = max(max_diff, d)
        return max_diff * math.sqrt((n1 * n2) / (n1 + n2))

    def _wasserstein_distance(self, reference: np.ndarray, current: np.ndarray) -> float:
        combined = np.sort(np.concatenate([reference, current]))
        ref_cdf = np.searchsorted(np.sort(reference), combined, side="right") / len(reference)
        cur_cdf = np.searchsorted(np.sort(current), combined, side="right") / len(current)
        return float(np.trapz(np.abs(ref_cdf - cur_cdf), combined))

    def detect(self, reference: np.ndarray, current: np.ndarray, method: str = "ks") -> float:
        if method == "ks":
            return self._ks_test(reference, current)
        elif method == "wasserstein":
            return self._wasserstein_distance(reference, current)
        else:
            return self._ks_test(reference, current)


class DriftDetector:
    def __init__(self, config: Optional[DriftConfig] = None) -> None:
        self._config = config or DriftConfig()
        self._lock = threading.RLock()
        self._stat_detector = StatisticalDriftDetector()
        self._reference: dict[str, deque] = {}
        self._current: dict[str, deque] = {}
        self._alerts: deque[DriftAlert] = deque(maxlen=1000)
        self._callbacks: list[Callable] = []
        self._total_samples = 0
        self._drift_events: dict[str, int] = {}
        self._init_metrics()

    def _init_metrics(self) -> None:
        for name in self._config.metric_names:
            self._reference[name] = deque(maxlen=self._config.window_size)
            self._current[name] = deque(maxlen=self._config.window_size)

    def register_callback(self, callback: Callable) -> None:
        self._callbacks.append(callback)

    def record(self, metric_name: str, value: float, is_reference: bool = False) -> None:
        with self._lock:
            if metric_name not in self._reference:
                return
            if is_reference or self._total_samples < self._config.min_samples:
                self._reference[metric_name].append(value)
            else:
                self._current[metric_name].append(value)

            if not is_reference:
                self._total_samples += 1
                self._check_drift(metric_name)

            if self._total_samples % self._config.reference_update_interval == 0:
                self._update_reference()

    def _check_drift(self, metric_name: str) -> None:
        ref = self._reference.get(metric_name)
        cur = self._current.get(metric_name)
        if ref is None or cur is None:
            return
        if len(ref) < self._config.min_samples or len(cur) < self._config.min_samples:
            return

        ref_arr = np.array(ref)
        cur_arr = np.array(cur)
        score = self._stat_detector.detect(ref_arr, cur_arr)

        severity = "normal"
        if score >= self._config.drift_threshold:
            severity = "drift"
        elif score >= self._config.warning_threshold:
            severity = "warning"

        if severity != "normal":
            alert = DriftAlert(
                metric_name=metric_name,
                drift_score=round(score, 4),
                severity=severity,
                details={
                    "reference_mean": float(np.mean(ref_arr)),
                    "current_mean": float(np.mean(cur_arr)),
                    "reference_std": float(np.std(ref_arr)),
                    "current_std": float(np.std(cur_arr)),
                    "sample_count": len(cur_arr),
                },
            )
            self._alerts.append(alert)
            self._drift_events[metric_name] = self._drift_events.get(metric_name, 0) + 1
            logger.warning("Drift detected on '%s': score=%.4f severity=%s", metric_name, score, severity)
            for cb in self._callbacks:
                try:
                    cb(alert)
                except Exception:
                    logger.exception("Drift callback failed")

    def _update_reference(self) -> None:
        for name in self._config.metric_names:
            cur = self._current.get(name)
            if cur and len(cur) >= self._config.min_samples:
                self._reference[name].extend(list(cur))
                self._current[name].clear()

    def get_recent_alerts(self, n: int = 10) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {
                    "alert_id": a.alert_id,
                    "metric_name": a.metric_name,
                    "drift_score": a.drift_score,
                    "severity": a.severity,
                    "timestamp": a.timestamp,
                    "details": a.details,
                }
                for a in list(self._alerts)[-n:]
            ]

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_samples": self._total_samples,
                "window_size": self._config.window_size,
                "warning_threshold": self._config.warning_threshold,
                "drift_threshold": self._config.drift_threshold,
                "alerts_total": len(self._alerts),
                "drift_events": dict(self._drift_events),
                "metric_states": {
                    name: {
                        "reference_samples": len(self._reference.get(name, [])),
                        "current_samples": len(self._current.get(name, [])),
                    }
                    for name in self._config.metric_names
                },
            }

    def get_current_state(self, metric_name: str) -> dict[str, Any]:
        ref = self._reference.get(metric_name)
        cur = self._current.get(metric_name)
        if ref is None or cur is None:
            return {"metric": metric_name, "available": False}
        ref_arr = np.array(ref) if ref else np.array([])
        cur_arr = np.array(cur) if cur else np.array([])
        score = 0.0
        if len(ref_arr) >= self._config.min_samples and len(cur_arr) >= self._config.min_samples:
            score = self._stat_detector.detect(ref_arr, cur_arr)
        return {
            "metric": metric_name,
            "available": len(ref_arr) >= self._config.min_samples and len(cur_arr) >= self._config.min_samples,
            "drift_score": round(score, 4),
            "reference_mean": float(np.mean(ref_arr)) if len(ref_arr) > 0 else 0.0,
            "current_mean": float(np.mean(cur_arr)) if len(cur_arr) > 0 else 0.0,
            "reference_std": float(np.std(ref_arr)) if len(ref_arr) > 0 else 0.0,
            "current_std": float(np.std(cur_arr)) if len(cur_arr) > 0 else 0.0,
            "reference_size": len(ref_arr),
            "current_size": len(cur_arr),
        }
