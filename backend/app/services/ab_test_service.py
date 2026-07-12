from __future__ import annotations

import hashlib
import time
from typing import Any

from loguru import logger
from pydantic import BaseModel


class Experiment(BaseModel):
    id: str
    name: str
    description: str = ""
    variants: list[dict[str, Any]]
    traffic_percentage: float = 1.0
    enabled: bool = True
    created_at: float = 0.0


class ExperimentResult(BaseModel):
    experiment_id: str
    variant: str
    user_hash: str


class ABTestService:
    def __init__(self) -> None:
        self._experiments: dict[str, Experiment] = {}
        self._assignments: dict[str, dict[str, str]] = {}
        self._events: list[dict] = []

    def create_experiment(self, experiment: Experiment) -> Experiment:
        experiment.created_at = time.time()
        self._experiments[experiment.id] = experiment
        logger.info(f"Experiment created: {experiment.id}")
        return experiment

    def get_experiment(self, experiment_id: str) -> Experiment | None:
        return self._experiments.get(experiment_id)

    def list_experiments(self) -> list[Experiment]:
        return list(self._experiments.values())

    def assign_variant(self, experiment_id: str, user_id: str) -> str | None:
        experiment = self._experiments.get(experiment_id)
        if not experiment or not experiment.enabled:
            return None

        user_hash = hashlib.sha256(f"{experiment_id}:{user_id}".encode()).hexdigest()
        hash_int = int(user_hash[:8], 16)
        if (hash_int % 100) / 100 > experiment.traffic_percentage:
            return None

        variant_index = hash_int % len(experiment.variants)
        variant = experiment.variants[variant_index]["name"]

        if experiment_id not in self._assignments:
            self._assignments[experiment_id] = {}
        self._assignments[experiment_id][user_id] = variant

        return variant

    def get_assignment(self, experiment_id: str, user_id: str) -> str | None:
        return self._assignments.get(experiment_id, {}).get(user_id)

    def track_event(self, experiment_id: str, user_id: str, event: str, value: float = 0.0) -> None:
        variant = self.get_assignment(experiment_id, user_id)
        if variant:
            self._events.append({
                "experiment_id": experiment_id,
                "user_id": user_id,
                "variant": variant,
                "event": event,
                "value": value,
                "timestamp": time.time(),
            })

    def get_results(self, experiment_id: str) -> dict[str, Any]:
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return {"error": "Experiment not found"}

        variant_events: dict[str, list[dict]] = {}
        for e in self._events:
            if e["experiment_id"] == experiment_id:
                variant = e["variant"]
                if variant not in variant_events:
                    variant_events[variant] = []
                variant_events[variant].append(e)

        results = {}
        for variant in experiment.variants:
            name = variant["name"]
            events = variant_events.get(name, [])
            total_value = sum(e["value"] for e in events)
            results[name] = {
                "assignments": len(self._assignments.get(experiment_id, {}).get(name, [])),
                "events": len(events),
                "total_value": total_value,
                "mean_value": total_value / len(events) if events else 0,
            }

        return {"experiment_id": experiment_id, "variants": results}


ab_test_service = ABTestService()
