import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class HPOResult:
    study_id: str
    best_params: dict[str, Any]
    best_value: float
    num_trials: int
    trials: list[dict] = field(default_factory=list)
    status: str = "completed"


class HPOptimizer:
    def __init__(
        self,
        storage_dir: str = "./hpo_studies",
        n_trials: int = 20,
        timeout_seconds: Optional[int] = None,
        direction: str = "maximize",
    ):
        self.storage_dir = storage_dir
        self.n_trials = n_trials
        self.timeout_seconds = timeout_seconds
        self.direction = direction
        os.makedirs(storage_dir, exist_ok=True)

    def optimize(
        self,
        param_space: dict[str, Any],
        objective_fn: Callable[[dict[str, Any]], float],
        study_name: Optional[str] = None,
    ) -> HPOResult:
        try:
            import optuna
        except ImportError:
            logger.warning("Optuna not installed. Falling back to random search.")
            return self._random_search(param_space, objective_fn, study_name)

        study_name = study_name or f"study_{uuid.uuid4().hex[:8]}"
        storage_path = os.path.join(self.storage_dir, f"{study_name}.db")
        storage = f"sqlite:///{storage_path}"

        study = optuna.create_study(
            study_name=study_name,
            direction=self.direction,
            storage=storage,
            load_if_exists=True,
        )

        def wrapped_objective(trial: optuna.Trial) -> float:
            params = {}
            for name, spec in param_space.items():
                params[name] = self._sample_param(trial, spec)
            return objective_fn(params)

        study.optimize(
            wrapped_objective,
            n_trials=self.n_trials,
            timeout=self.timeout_seconds,
            show_progress_bar=False,
        )

        trials_data = []
        for t in study.trials:
            trials_data.append({
                "number": t.number,
                "params": t.params,
                "value": t.value,
                "state": str(t.state),
                "datetime_start": t.datetime_start.isoformat() if t.datetime_start else None,
                "datetime_complete": t.datetime_complete.isoformat() if t.datetime_complete else None,
            })

        return HPOResult(
            study_id=study_name,
            best_params=study.best_params,
            best_value=study.best_value,
            num_trials=len(study.trials),
            trials=trials_data,
        )

    def _random_search(
        self,
        param_space: dict[str, Any],
        objective_fn: Callable[[dict[str, Any]], float],
        study_name: Optional[str] = None,
    ) -> HPOResult:
        import random
        import math

        study_name = study_name or f"random_{uuid.uuid4().hex[:8]}"
        best_value = -math.inf if self.direction == "maximize" else math.inf
        best_params: dict[str, Any] = {}
        trials_data: list[dict] = []

        for i in range(self.n_trials):
            params = {}
            for name, spec in param_space.items():
                params[name] = self._random_sample(spec)
            try:
                value = objective_fn(params)
            except Exception as e:
                logger.warning(f"Trial {i} failed: {e}")
                continue

            better = value > best_value if self.direction == "maximize" else value < best_value
            if better:
                best_value = value
                best_params = params

            trials_data.append({
                "number": i,
                "params": params,
                "value": value,
                "state": "completed",
            })

        return HPOResult(
            study_id=study_name,
            best_params=best_params,
            best_value=best_value if best_params else 0.0,
            num_trials=len(trials_data),
            trials=trials_data,
        )

    def _sample_param(self, trial, spec: dict) -> Any:
        ptype = spec.get("type", "float")
        if ptype == "float":
            return trial.suggest_float(
                spec.get("name", "param"),
                spec.get("low", 0.0),
                spec.get("high", 1.0),
                log=spec.get("log", False),
            )
        elif ptype == "int":
            return trial.suggest_int(
                spec.get("name", "param"),
                spec.get("low", 1),
                spec.get("high", 100),
                log=spec.get("log", False),
            )
        elif ptype == "categorical":
            return trial.suggest_categorical(
                spec.get("name", "param"),
                spec.get("choices", []),
            )
        return spec.get("default")

    def _random_sample(self, spec: dict) -> Any:
        import random
        ptype = spec.get("type", "float")
        if ptype == "float":
            low, high = spec.get("low", 0.0), spec.get("high", 1.0)
            if spec.get("log", False):
                import math
                return math.exp(random.uniform(math.log(low), math.log(high)))
            return random.uniform(low, high)
        elif ptype == "int":
            return random.randint(spec.get("low", 1), spec.get("high", 100))
        elif ptype == "categorical":
            choices = spec.get("choices", [])
            return random.choice(choices) if choices else None
        return spec.get("default")


def create_default_param_space() -> dict[str, Any]:
    return {
        "learning_rate": {
            "type": "float",
            "low": 1e-5,
            "high": 1e-1,
            "log": True,
        },
        "batch_size": {
            "type": "int",
            "low": 8,
            "high": 128,
            "log": True,
        },
        "num_epochs": {
            "type": "int",
            "low": 10,
            "high": 200,
        },
        "hidden_dim": {
            "type": "int",
            "low": 16,
            "high": 256,
            "log": True,
        },
        "l1_reg": {
            "type": "float",
            "low": 1e-6,
            "high": 1e-2,
            "log": True,
        },
        "l2_reg": {
            "type": "float",
            "low": 1e-6,
            "high": 1e-2,
            "log": True,
        },
    }
