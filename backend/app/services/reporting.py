"""Research Report Generator (Phase 6).

Exports experiment / benchmark / attack results as CSV, Excel (.xlsx via
openpyxl), and JSON — ready for inclusion in a paper's supplementary material.
PDF rendering of IEEE tables is available through the metrics calculator's
LaTeX output; the dashboard exposes download endpoints that reuse these
serialisers.
"""
from __future__ import annotations

import io
import json
from typing import Any

import pandas as pd

from app.db.models import AttackResult, BenchmarkResult, PrivacyScore


class ResearchReportGenerator:
    @staticmethod
    def benchmark_dataframe(rows: list[BenchmarkResult]) -> pd.DataFrame:
        flat: list[dict[str, Any]] = []
        for r in rows:
            flat.append(
                {
                    "benchmark_row_id": r.id,
                    "experiment_id": r.experiment_id,
                    "dataset_id": r.dataset_id,
                    "model_id": r.model_id,
                    "method": r.method,
                    "deleted_records": r.deleted_records,
                    "eval_records": r.eval_records,
                    **r.metrics,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
            )
        return pd.DataFrame(flat)

    @staticmethod
    def attack_dataframe(rows: list[AttackResult]) -> pd.DataFrame:
        flat: list[dict[str, Any]] = []
        for r in rows:
            flat.append(
                {
                    "attack_result_id": r.id,
                    "experiment_id": r.experiment_id,
                    "model_id": r.model_id,
                    "attack_type": r.attack_type,
                    "stage": r.stage,
                    **r.metrics,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
            )
        return pd.DataFrame(flat)

    @staticmethod
    def scores_dataframe(rows: list[PrivacyScore]) -> pd.DataFrame:
        flat: list[dict[str, Any]] = []
        for r in rows:
            flat.append({"experiment_id": r.experiment_id, "method": r.method, **r.scores})
        return pd.DataFrame(flat)

    # ------------------------------------------------------------- exports

    @staticmethod
    def to_csv(df: pd.DataFrame) -> bytes:
        return df.to_csv(index=False).encode("utf-8")

    @staticmethod
    def to_json(df: pd.DataFrame) -> bytes:
        return json.dumps({"rows": df.to_dict(orient="records")}, indent=2).encode("utf-8")

    @staticmethod
    def to_excel(df: pd.DataFrame) -> bytes:
        """Excel workbook (needs openpyxl); falls back to CSV if unavailable."""
        buffer = io.BytesIO()
        try:
            import openpyxl  # noqa: F401 - ensures the writer is available

            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="results")
        except ImportError:  # pragma: no cover - openpyxl is a declared dep
            return df.to_csv(index=False).encode("utf-8")
        return buffer.getvalue()

    @staticmethod
    def workbook_exports(
        benchmarks: list[BenchmarkResult] | None = None,
        attacks: list[AttackResult] | None = None,
        scores: list[PrivacyScore] | None = None,
    ) -> dict[str, bytes]:
        """Multi-sheet Excel workbook with all available dataframes."""
        buffer = io.BytesIO()
        try:
            import openpyxl  # noqa: F401

            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                if benchmarks:
                    ResearchReportGenerator.benchmark_dataframe(benchmarks).to_excel(
                        writer, index=False, sheet_name="benchmarks"
                    )
                if attacks:
                    ResearchReportGenerator.attack_dataframe(attacks).to_excel(
                        writer, index=False, sheet_name="attacks"
                    )
                if scores:
                    ResearchReportGenerator.scores_dataframe(scores).to_excel(
                        writer, index=False, sheet_name="privacy_scores"
                    )
        except ImportError:  # pragma: no cover
            parts = []
            if benchmarks:
                parts.append(ResearchReportGenerator.to_csv(ResearchReportGenerator.benchmark_dataframe(benchmarks)))
            if attacks:
                parts.append(ResearchReportGenerator.to_csv(ResearchReportGenerator.attack_dataframe(attacks)))
            if scores:
                parts.append(ResearchReportGenerator.to_csv(ResearchReportGenerator.scores_dataframe(scores)))
            return {"application/octet-stream": b"\n\n".join(parts)}
        return {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": buffer.getvalue()}
