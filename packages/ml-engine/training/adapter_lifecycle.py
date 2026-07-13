import json
import logging
import os
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class AdapterStatus(str, Enum):
    PENDING = "pending"
    LOADING = "loading"
    ACTIVE = "active"
    QUIESCING = "quiescing"
    INACTIVE = "inactive"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    DEPRECATED = "deprecated"


class RoutingStrategy(str, Enum):
    SINGLE = "single"
    CANARY = "canary"
    BLUE_GREEN = "blue_green"
    WEIGHTED = "weighted"
    LATENCY_BASED = "latency_based"


@dataclass
class AdapterVersion:
    version_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    adapter_name: str = ""
    version_number: int = 1
    adapter_path: str = ""
    base_model_name: str = ""
    status: AdapterStatus = AdapterStatus.PENDING
    routing_weight: float = 1.0
    config: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    tags: dict = field(default_factory=dict)
    parent_version_id: Optional[str] = None
    deployed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_used_at: Optional[str] = None
    error_count: int = 0
    total_requests: int = 0
    avg_latency_ms: float = 0.0
    memory_mb: float = 0.0
    is_active: bool = False


@dataclass
class LifecycleConfig:
    max_versions_per_adapter: int = 10
    auto_quiesce_after_seconds: int = 86400
    health_check_interval_seconds: int = 60
    canary_traffic_pct: float = 10.0
    rollback_on_error_threshold: int = 5
    metrics_window_size: int = 100
    persist_path: str = "./adapter_registry"


@dataclass
class RoutingRule:
    strategy: RoutingStrategy = RoutingStrategy.SINGLE
    primary_version_id: str = ""
    secondary_version_id: Optional[str] = None
    weights: dict[str, float] = field(default_factory=dict)


class AdapterLifecycleManager:
    def __init__(self, config: Optional[LifecycleConfig] = None) -> None:
        self._config = config or LifecycleConfig()
        self._adapters: dict[str, list[AdapterVersion]] = defaultdict(list)
        self._current_version: dict[str, str] = {}
        self._routing_rules: dict[str, RoutingRule] = {}
        self._latency_history: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self._config.metrics_window_size)
        )
        self._lock = threading.RLock()
        self._load_fn: Optional[Callable] = None
        self._unload_fn: Optional[Callable] = None
        self._ensure_persist_dir()

    def register_load_fn(self, fn: Callable) -> None:
        self._load_fn = fn

    def register_unload_fn(self, fn: Callable) -> None:
        self._unload_fn = fn

    def _ensure_persist_dir(self) -> None:
        os.makedirs(self._config.persist_path, exist_ok=True)

    def register_adapter(
        self,
        adapter_name: str,
        adapter_path: str,
        base_model_name: str = "",
        config: Optional[dict] = None,
        tags: Optional[dict] = None,
    ) -> AdapterVersion:
        with self._lock:
            versions = self._adapters[adapter_name]
            version_number = len(versions) + 1
            parent_id = self._current_version.get(adapter_name)

            version = AdapterVersion(
                adapter_name=adapter_name,
                version_number=version_number,
                adapter_path=adapter_path,
                base_model_name=base_model_name,
                status=AdapterStatus.PENDING,
                config=config or {},
                tags=tags or {},
                parent_version_id=parent_id,
            )

            if parent_id:
                parent = self._get_version(adapter_name, parent_id)
                if parent:
                    parent.status = AdapterStatus.QUIESCING

            versions.append(version)
            self._current_version[adapter_name] = version.version_id
            self._routing_rules[adapter_name] = RoutingRule(
                strategy=RoutingStrategy.SINGLE,
                primary_version_id=version.version_id,
            )
            self._persist()
            logger.info("Registered adapter '%s' version %d (%s)", adapter_name, version_number, version.version_id)
            return version

    def activate_version(self, adapter_name: str, version_id: str) -> bool:
        with self._lock:
            version = self._get_version(adapter_name, version_id)
            if version is None:
                logger.error("Version %s not found for adapter '%s'", version_id, adapter_name)
                return False

            if version.status == AdapterStatus.FAILED:
                logger.warning("Cannot activate failed version %s", version_id)
                return False

            old_id = self._current_version.get(adapter_name)
            if old_id and old_id != version_id:
                old_version = self._get_version(adapter_name, old_id)
                if old_version:
                    old_version.status = AdapterStatus.QUIESCING
                    old_version.is_active = False

            version.status = AdapterStatus.ACTIVE
            version.is_active = True
            version.deployed_at = datetime.now(timezone.utc).isoformat()
            self._current_version[adapter_name] = version_id
            self._routing_rules[adapter_name].primary_version_id = version_id
            self._persist()
            logger.info("Activated version %s for adapter '%s'", version_id, adapter_name)
            return True

    def deactivate_version(self, adapter_name: str, version_id: str) -> bool:
        with self._lock:
            version = self._get_version(adapter_name, version_id)
            if version is None:
                return False
            version.status = AdapterStatus.INACTIVE
            version.is_active = False
            self._persist()
            return True

    def mark_failed(self, adapter_name: str, version_id: str, error: str = "") -> bool:
        with self._lock:
            version = self._get_version(adapter_name, version_id)
            if version is None:
                return False
            version.status = AdapterStatus.FAILED
            version.error_count += 1
            version.metrics["last_error"] = error
            version.metrics["last_error_at"] = datetime.now(timezone.utc).isoformat()

            threshold = self._config.rollback_on_error_threshold
            if version.error_count >= threshold:
                self._auto_rollback(adapter_name, version_id)
            self._persist()
            return True

    def record_request(
        self, adapter_name: str, version_id: str, latency_ms: float, success: bool
    ) -> None:
        with self._lock:
            version = self._get_version(adapter_name, version_id)
            if version is None:
                return
            version.total_requests += 1
            version.last_used_at = datetime.now(timezone.utc).isoformat()
            n = version.total_requests
            version.avg_latency_ms = ((version.avg_latency_ms * (n - 1)) + latency_ms) / n
            self._latency_history[adapter_name].append(latency_ms)
            if not success:
                version.error_count += 1
                threshold = self._config.rollback_on_error_threshold
                if version.error_count >= threshold:
                    self._auto_rollback(adapter_name, version_id)

    def _auto_rollback(self, adapter_name: str, failed_version_id: str) -> bool:
        versions = self._adapters.get(adapter_name, [])
        sorted_versions = sorted(versions, key=lambda v: v.version_number, reverse=True)
        for version in sorted_versions:
            if version.version_id != failed_version_id and version.status not in (
                AdapterStatus.FAILED, AdapterStatus.DEPRECATED
            ):
                logger.info(
                    "Auto-rolling back '%s' from version %s to version %s",
                    adapter_name, failed_version_id, version.version_id,
                )
                version.status = AdapterStatus.ACTIVE
                version.is_active = True
                self._current_version[adapter_name] = version.version_id
                self._routing_rules[adapter_name].primary_version_id = version.version_id
                self._persist()
                return True
        return False

    def rollback(self, adapter_name: str, target_version_id: Optional[str] = None) -> Optional[AdapterVersion]:
        with self._lock:
            versions = self._adapters.get(adapter_name, [])
            current_id = self._current_version.get(adapter_name)

            if not current_id:
                return None

            current = self._get_version(adapter_name, current_id)
            if current:
                current.status = AdapterStatus.ROLLED_BACK
                current.is_active = False

            if target_version_id:
                target = self._get_version(adapter_name, target_version_id)
            else:
                sorted_v = sorted(
                    [v for v in versions if v.version_id != current_id and v.status != AdapterStatus.FAILED],
                    key=lambda v: v.version_number,
                    reverse=True,
                )
                target = sorted_v[0] if sorted_v else None

            if target is None:
                logger.error("No valid rollback target for '%s'", adapter_name)
                return None

            target.status = AdapterStatus.ACTIVE
            target.is_active = True
            self._current_version[adapter_name] = target.version_id
            self._routing_rules[adapter_name].primary_version_id = target.version_id
            self._persist()
            logger.info("Rolled back '%s' to version %s", adapter_name, target.version_id)
            return target

    def setup_canary(
        self,
        adapter_name: str,
        stable_version_id: str,
        canary_version_id: str,
        canary_traffic_pct: Optional[float] = None,
    ) -> None:
        with self._lock:
            pct = canary_traffic_pct or self._config.canary_traffic_pct
            self._routing_rules[adapter_name] = RoutingRule(
                strategy=RoutingStrategy.CANARY,
                primary_version_id=stable_version_id,
                secondary_version_id=canary_version_id,
                weights={stable_version_id: 100.0 - pct, canary_version_id: pct},
            )
            self._persist()
            logger.info("Canary setup for '%s': stable=%s (%.1f%%), canary=%s (%.1f%%)",
                        adapter_name, stable_version_id, 100 - pct, canary_version_id, pct)

    def promote_canary(self, adapter_name: str) -> Optional[AdapterVersion]:
        with self._lock:
            rule = self._routing_rules.get(adapter_name)
            if rule is None or rule.strategy != RoutingStrategy.CANARY:
                return None
            canary_id = rule.secondary_version_id
            if canary_id is None:
                return None
            self.activate_version(adapter_name, canary_id)
            self._routing_rules[adapter_name] = RoutingRule(
                strategy=RoutingStrategy.SINGLE, primary_version_id=canary_id
            )
            self._persist()
            return self._get_version(adapter_name, canary_id)

    def get_active_version(self, adapter_name: str) -> Optional[AdapterVersion]:
        with self._lock:
            version_id = self._current_version.get(adapter_name)
            if version_id is None:
                return None
            return self._get_version(adapter_name, version_id)

    def get_versions(self, adapter_name: str) -> list[dict[str, Any]]:
        with self._lock:
            versions = self._adapters.get(adapter_name, [])
            return [asdict(v) for v in sorted(versions, key=lambda x: x.version_number)]

    def list_adapters(self) -> list[dict[str, Any]]:
        with self._lock:
            result = []
            for name, versions in self._adapters.items():
                active = self.get_active_version(name)
                result.append({
                    "adapter_name": name,
                    "version_count": len(versions),
                    "active_version_id": active.version_id if active else None,
                    "active_version_number": active.version_number if active else None,
                    "status": active.status.value if active else "none",
                    "total_requests": sum(v.total_requests for v in versions),
                    "avg_latency_ms": active.avg_latency_ms if active else 0.0,
                })
            return result

    def get_routing_rule(self, adapter_name: str) -> Optional[dict[str, Any]]:
        with self._lock:
            rule = self._routing_rules.get(adapter_name)
            if rule is None:
                return None
            return asdict(rule)

    def get_latency_stats(self, adapter_name: str) -> dict[str, Any]:
        with self._lock:
            history = list(self._latency_history.get(adapter_name, []))
            if not history:
                return {"avg_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0, "samples": 0}
            sorted_hist = sorted(history)
            n = len(sorted_hist)
            return {
                "avg_ms": sum(sorted_hist) / n,
                "p50_ms": sorted_hist[int(n * 0.5)],
                "p95_ms": sorted_hist[int(n * 0.95)],
                "p99_ms": sorted_hist[int(n * 0.99)],
                "samples": n,
            }

    def get_adapter_health(self, adapter_name: str) -> dict[str, Any]:
        with self._lock:
            active = self.get_active_version(adapter_name)
            if active is None:
                return {"status": "unregistered", "healthy": False}
            return {
                "adapter_name": adapter_name,
                "status": active.status.value,
                "healthy": active.status == AdapterStatus.ACTIVE,
                "version_number": active.version_number,
                "version_id": active.version_id,
                "total_requests": active.total_requests,
                "error_count": active.error_count,
                "avg_latency_ms": active.avg_latency_ms,
                "last_used_at": active.last_used_at,
                "memory_mb": active.memory_mb,
            }

    def _get_version(self, adapter_name: str, version_id: str) -> Optional[AdapterVersion]:
        for v in self._adapters.get(adapter_name, []):
            if v.version_id == version_id:
                return v
        return None

    def _persist(self) -> None:
        try:
            data = {
                "adapters": {
                    name: [asdict(v) for v in versions]
                    for name, versions in self._adapters.items()
                },
                "current": self._current_version,
                "routing": {k: asdict(v) for k, v in self._routing_rules.items()},
            }
            path = os.path.join(self._config.persist_path, "adapter_lifecycle.json")
            with open(path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception:
            logger.exception("Failed to persist adapter lifecycle state")

    def load_state(self) -> None:
        path = os.path.join(self._config.persist_path, "adapter_lifecycle.json")
        if not os.path.exists(path):
            return
        try:
            with open(path) as f:
                data = json.load(f)
            for name, versions_data in data.get("adapters", {}).items():
                versions = []
                for vd in versions_data:
                    v = AdapterVersion(**vd)
                    v.status = AdapterStatus(v.status) if isinstance(v.status, str) else v.status
                    versions.append(v)
                self._adapters[name] = versions
            self._current_version.update(data.get("current", {}))
            for k, rd in data.get("routing", {}).items():
                rr = RoutingRule(**rd)
                rr.strategy = RoutingStrategy(rr.strategy) if isinstance(rr.strategy, str) else rr.strategy
                self._routing_rules[k] = rr
            logger.info("Loaded adapter lifecycle state from %s", path)
        except Exception:
            logger.exception("Failed to load adapter lifecycle state")
