from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AlgorithmDecision:
    name: str
    estimated_cost: float
    estimated_latency: float
    guarantees: str
    privacy_score: float = 0.0
    utility_retention: float = 0.0
    implementation_status: str = "available"


class AdaptiveController:
    def select_algorithm(
        self,
        dataset_size: int,
        num_deleted: int,
        sensitivity: str = "medium",
        latency_budget: float = 300.0,
        model_type: str = "lora",
    ) -> str:
        deletion_ratio = num_deleted / max(dataset_size, 1)

        if sensitivity == "high" and deletion_ratio > 0.05:
            return "sisa"

        if latency_budget < 60 and deletion_ratio <= 0.05:
            return "bad_teacher"

        if deletion_ratio <= 0.01 and dataset_size <= 1000:
            return "relu_erasure"

        if num_deleted <= 10:
            return "certified_removal"

        if deletion_ratio <= 0.1:
            return "influence_functions"

        if deletion_ratio <= 0.2:
            return "catastrophic_forgetting"

        return "sisa"

    def estimate_cost(
        self,
        algorithm: str,
        dataset_size: int,
        num_deleted: int,
    ) -> AlgorithmDecision:
        costs = {
            "sisa": {
                "cost": dataset_size * 0.5,
                "latency": dataset_size * 0.01,
                "guarantees": "exact_unlearning",
                "privacy_score": 0.96,
                "utility_retention": 0.88,
                "implementation_status": "exact_lora_retrain",
            },
            "influence_functions": {
                "cost": dataset_size * 0.1,
                "latency": dataset_size * 0.005,
                "guarantees": "approximate",
                "privacy_score": 0.82,
                "utility_retention": 0.94,
                "implementation_status": "approximate_correction",
            },
            "certified_removal": {
                "cost": num_deleted * 1.0,
                "latency": num_deleted * 0.1,
                "guarantees": "certified",
                "privacy_score": 0.74,
                "utility_retention": 0.98,
                "implementation_status": "certified_metadata",
            },
            "gradient_ascent": {
                "cost": max(num_deleted, 1) * 2.5,
                "latency": max(num_deleted, 1) * 0.25,
                "guarantees": "approximate_forgetting",
                "privacy_score": 0.86,
                "utility_retention": 0.91,
                "implementation_status": "targeted_negative_update",
            },
            "bad_teacher": {
                "cost": max(num_deleted, 1) * 2.5,
                "latency": max(num_deleted, 1) * 0.25,
                "guarantees": "approximate_forgetting",
                "privacy_score": 0.85,
                "utility_retention": 0.90,
                "implementation_status": "targeted_negative_update",
            },
            "catastrophic_forgetting": {
                "cost": dataset_size * 0.05,
                "latency": dataset_size * 0.002,
                "guarantees": "approximate_forgetting",
                "privacy_score": 0.78,
                "utility_retention": 0.80,
                "implementation_status": "weight_perturbation",
            },
            "relu_erasure": {
                "cost": num_deleted * 2.0,
                "latency": num_deleted * 0.15,
                "guarantees": "representation_erasure",
                "privacy_score": 0.72,
                "utility_retention": 0.93,
                "implementation_status": "layer_correction",
            },
        }

        info = costs.get(algorithm, costs["sisa"])
        return AlgorithmDecision(
            name=algorithm,
            estimated_cost=info["cost"],
            estimated_latency=info["latency"],
            guarantees=info["guarantees"],
            privacy_score=info["privacy_score"],
            utility_retention=info["utility_retention"],
            implementation_status=info["implementation_status"],
        )

    def supported_algorithms(self) -> list[str]:
        return [
            "bad_teacher", "catastrophic_forgetting", "certified_removal",
            "gradient_ascent", "influence_functions", "relu_erasure", "sisa",
        ]
