"""Research Metrics Calculator (Phase 6).

Computes the publication-ready metrics of the VeriUnlearn framework from
operational data (benchmark rows, attack results, verification reports,
deletion requests):

- **Forget Quality Score** (0–1): how completely the model stopped relying on
  deleted records — 1 − detection rate of deleted records under MIA.
- **Privacy Gain**: reduction in membership-inference AUC before vs after
  unlearning.
- **Knowledge Retention** (0–1): fraction of holdout utility preserved.
- **Accuracy Drop**: absolute utility loss on the holdout after unlearning.
- **Utility Loss**: relative utility loss (accuracy drop / original accuracy).
- **Deletion Efficiency**: records deleted per second.
- **Verification Overhead**: verification + certificate time as a fraction of
  total deletion pipeline time.
- **Compliance Readiness** (0–100): composite of resolution rate, certificate
  integrity, audit-chain integrity, and verification health.

Also renders IEEE-ready LaTeX tables and CSV dumps of metric matrices.
"""
from __future__ import annotations

import csv
import io
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    BenchmarkResult,
    Certificate,
    DeletionRequest,
    VerificationReport,
)


class ResearchMetricsCalculator:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------- primitives

    @staticmethod
    def forget_quality(mia_auc_after: float) -> float:
        """1 − post-unlearning MIA AUC; 1.0 = perfectly forgotten."""
        return round(max(0.0, min(1.0, 1.0 - mia_auc_after)), 4)

    @staticmethod
    def privacy_gain(mia_auc_before: float, mia_auc_after: float) -> float:
        return round(max(0.0, mia_auc_before - mia_auc_after), 4)

    @staticmethod
    def knowledge_retention(acc_after: float, acc_original: float) -> float:
        if acc_original <= 0:
            return 0.0
        return round(max(0.0, min(1.0, acc_after / acc_original)), 4)

    @staticmethod
    def accuracy_drop(acc_original: float, acc_after: float) -> float:
        return round(max(0.0, acc_original - acc_after), 4)

    @staticmethod
    def utility_loss(acc_original: float, acc_after: float) -> float:
        if acc_original <= 0:
            return 0.0
        return round(max(0.0, (acc_original - acc_after) / acc_original), 4)

    @staticmethod
    def deletion_efficiency(records: int, seconds: float) -> float:
        if seconds <= 0:
            return 0.0
        return round(records / seconds, 2)

    @staticmethod
    def verification_overhead(verify_seconds: float, deletion_seconds: float) -> float:
        total = verify_seconds + deletion_seconds
        if total <= 0:
            return 0.0
        return round(verify_seconds / total, 4)

    # -------------------------------------------------------------- composite

    async def compliance_readiness(self) -> dict[str, Any]:
        """0–100 composite from operational data (never hardcoded)."""
        total_requests = int(
            await self.session.scalar(select(func.count()).select_from(DeletionRequest)) or 0
        )
        completed = int(
            await self.session.scalar(
                select(func.count())
                .select_from(DeletionRequest)
                .where(DeletionRequest.status == "completed")
            )
            or 0
        )
        certs_total = int(
            await self.session.scalar(select(func.count()).select_from(Certificate)) or 0
        )
        certs_valid = int(
            await self.session.scalar(
                select(func.count())
                .select_from(Certificate)
                .where(Certificate.verification_status == "valid")
            )
            or 0
        )
        reports_total = int(
            await self.session.scalar(select(func.count()).select_from(VerificationReport)) or 0
        )
        reports_valid = int(
            await self.session.scalar(
                select(func.count())
                .select_from(VerificationReport)
                .where(VerificationReport.verdict == "valid")
            )
            or 0
        )

        resolution = completed / total_requests if total_requests else 1.0
        cert_integrity = certs_valid / certs_total if certs_total else 1.0
        verification_health = reports_valid / reports_total if reports_total else 1.0

        from app.services.audit import AuditService

        chain = await AuditService(self.session).verify_chain()
        chain_intact = 1.0 if chain["verified"] else 0.0

        score = round(
            100 * (0.35 * resolution + 0.25 * cert_integrity + 0.25 * verification_health + 0.15 * chain_intact),
            1,
        )
        return {
            "score": score,
            "level": "ready" if score >= 85 else "partial" if score >= 60 else "not-ready",
            "details": {
                "resolution_rate": round(resolution, 3),
                "certificate_integrity": round(cert_integrity, 3),
                "verification_health": round(verification_health, 3),
                "audit_chain_intact": chain_intact == 1.0,
            },
        }

    # ------------------------------------------------------------ per-method

    async def scores_for_method(self, method: str) -> dict[str, Any]:
        """Full metric vector for one unlearning method from persisted data."""
        rows = (
            await self.session.execute(
                select(BenchmarkResult).where(BenchmarkResult.method == method).order_by(BenchmarkResult.created_at.desc())
            )
        ).scalars().all()
        if not rows:
            return {"method": method, "available": False}

        latest = rows[0].metrics
        acc_original = latest.get("accuracy_original", 1.0)
        acc_after = latest.get("accuracy", acc_original)
        mia_before = latest.get("mia_auc_before", 0.5)
        mia_after = latest.get("mia_auc_after", 0.5)
        deletion_s = latest.get("deletion_seconds", 0.0)
        records = latest.get("deleted_records", rows[0].deleted_records)
        verify_s = latest.get("verification_seconds", 0.0)

        return {
            "method": method,
            "available": True,
            "scores": {
                "forget_quality_score": ResearchMetricsCalculator.forget_quality(mia_after),
                "privacy_gain": ResearchMetricsCalculator.privacy_gain(mia_before, mia_after),
                "knowledge_retention": ResearchMetricsCalculator.knowledge_retention(acc_after, acc_original),
                "accuracy_drop": ResearchMetricsCalculator.accuracy_drop(acc_original, acc_after),
                "utility_loss": ResearchMetricsCalculator.utility_loss(acc_original, acc_after),
                "deletion_efficiency": ResearchMetricsCalculator.deletion_efficiency(records, deletion_s),
                "verification_overhead": ResearchMetricsCalculator.verification_overhead(verify_s, deletion_s),
            },
            "compliance_readiness": await self.compliance_readiness(),
            "source": {
                "benchmark_row_id": rows[0].id,
                "accuracy_original": acc_original,
                "accuracy_after": acc_after,
                "mia_auc_before": mia_before,
                "mia_auc_after": mia_after,
                "deleted_records": records,
                "deletion_seconds": deletion_s,
            },
        }

    async def comparison_matrix(self, methods: list[str] | None = None) -> dict[str, Any]:
        """IEEE-ready table of all requested methods across all metrics."""
        methods = methods or ["original", "full_retrain", "sisa", "influence", "certified", "veriunlearn"]
        per_method = [await self.scores_for_method(m) for m in methods]
        metric_keys = [
            "forget_quality_score", "privacy_gain", "knowledge_retention", "accuracy_drop",
            "utility_loss", "deletion_efficiency", "verification_overhead",
        ]
        rows = []
        for entry in per_method:
            if not entry["available"]:
                continue
            row = {"method": entry["method"]}
            for k in metric_keys:
                row[k] = entry["scores"].get(k)
            rows.append(row)
        return {"metrics": metric_keys, "rows": rows, "compliance": await self.compliance_readiness()}

    # ------------------------------------------------------------------ ieee

    def to_latex_table(self, matrix: dict[str, Any]) -> str:
        """Render the comparison matrix as a LaTeX table for a paper."""
        lines = [
            r"\begin{table}[ht]",
            r"\centering",
            r"\caption{VeriUnlearn benchmark: unlearning methods across utility, privacy and cost metrics}",
            r"\label{tab:benchmark}",
            r"\begin{tabular}{l" + "c" * len(matrix["metrics"]) + "}",
            r"\toprule",
            "Method & " + " & ".join(m.replace("_", "\\_") for m in matrix["metrics"]) + r" \\",
            r"\midrule",
        ]
        for row in matrix["rows"]:
            cells = [row["method"]]
            for k in matrix["metrics"]:
                v = row.get(k)
                cells.append(f"{v:.4f}" if isinstance(v, (int, float)) else "—")
            lines.append(" & ".join(cells) + r" \\")
        lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
        return "\n".join(lines)

    def to_csv(self, matrix: dict[str, Any]) -> str:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["method"] + matrix["metrics"])
        writer.writeheader()
        for row in matrix["rows"]:
            writer.writerow(row)
        return buf.getvalue()
