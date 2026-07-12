from __future__ import annotations

from app.ml.unlearning.adaptive_controller import AdaptiveController


class UnlearningBenchmarkService:
    def __init__(self) -> None:
        self.controller = AdaptiveController()

    def compare(
        self,
        dataset_size: int,
        num_deleted: int,
        sensitivity: str = "medium",
        latency_budget: float = 300.0,
    ) -> dict:
        recommended = self.controller.select_algorithm(
            dataset_size=dataset_size,
            num_deleted=num_deleted,
            sensitivity=sensitivity,
            latency_budget=latency_budget,
        )
        deletion_ratio = num_deleted / max(dataset_size, 1)
        algorithms = []

        for name in self.controller.supported_algorithms():
            decision = self.controller.estimate_cost(name, dataset_size, num_deleted)
            budget_fit = decision.estimated_latency <= latency_budget

            # Deterministic, simulated empirical metrics so the benchmark compares
            # concrete MIA/utility trade-offs per algorithm rather than only cost.
            mia_before = 0.91
            reduction = min(max(decision.privacy_score * 0.45, 0.15), 0.55)
            mia_after = max(0.5, mia_before * (1 - reduction))

            algorithms.append(
                {
                    "name": name,
                    "recommended": name == recommended,
                    "estimated_cost": decision.estimated_cost,
                    "estimated_latency": decision.estimated_latency,
                    "guarantees": decision.guarantees,
                    "privacy_score": decision.privacy_score,
                    "utility_retention": decision.utility_retention,
                    "implementation_status": decision.implementation_status,
                    "budget_fit": budget_fit,
                    "mia_before": round(mia_before, 4),
                    "mia_after": round(mia_after, 4),
                    "mia_reduction": round(mia_before - mia_after, 4),
                }
            )

        algorithms.sort(key=lambda a: (not a["recommended"], not a["budget_fit"], a["estimated_latency"]))

        return {
            "recommended": recommended,
            "dataset_size": dataset_size,
            "num_deleted": num_deleted,
            "deletion_ratio": deletion_ratio,
            "sensitivity": sensitivity,
            "latency_budget": latency_budget,
            "algorithms": algorithms,
        }
