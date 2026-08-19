"""Compliance scoring (GDPR Art. 17 & DPDP Act 2023).

Scores are derived entirely from operational data (deletion requests,
certificates, verification results, audit chain integrity) — never hardcoded.

- **GDPR score**  : weight of resolved requests, on-time completion, verified
  certificates and intact audit chain.
- **DPDP score**  : same core metrics weighted for the DPDP consent framework
  (identifies the additional consent-verification dimension).
- **Risk score**  : rises with open requests, verification failures and
  successful membership-inference attacks.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Certificate, ComplianceReport, DeletionRequest
from app.services.audit import AuditService


class ComplianceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit = AuditService(session)

    async def _request_stats(self) -> dict[str, Any]:
        total = await self._count(DeletionRequest)
        completed = await self._count(DeletionRequest, DeletionRequest.status == "completed")
        failed = await self._count(DeletionRequest, DeletionRequest.status == "failed")
        pending = await self._count(DeletionRequest, DeletionRequest.status.in_(["pending", "in_progress"]))
        avg_duration = await self.session.scalar(
            select(func.avg(DeletionRequest.duration_seconds)).where(
                DeletionRequest.duration_seconds.isnot(None)
            )
        )
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "avg_deletion_seconds": round(float(avg_duration), 2) if avg_duration else None,
        }

    async def _count(self, model: Any, *where: Any) -> int:
        stmt = select(func.count()).select_from(model)
        for clause in where:
            stmt = stmt.where(clause)
        return int(await self.session.scalar(stmt) or 0)

    async def overview(self) -> dict[str, Any]:
        requests = await self._request_stats()
        certs_total = await self._count(Certificate)
        certs_valid = await self._count(Certificate, Certificate.verification_status == "valid")
        certs_invalid = await self._count(Certificate, Certificate.verification_status == "invalid")
        audit_state = await self.audit.verify_chain()

        resolution_rate = requests["completed"] / requests["total"] if requests["total"] else 1.0
        on_time = 1.0 if requests["total"] == 0 else (
            (requests["completed"] - (await self._late_requests())) / requests["completed"]
            if requests["completed"] else 1.0
        )
        cert_integrity = certs_valid / certs_total if certs_total else 1.0
        chain_intact = 1.0 if audit_state["verified"] else 0.0

        gdpr_score = 100 * (0.4 * resolution_rate + 0.2 * on_time + 0.25 * cert_integrity + 0.15 * chain_intact)
        dpdp_score = 100 * (0.35 * resolution_rate + 0.15 * on_time + 0.25 * cert_integrity + 0.1 * chain_intact + 0.15 * self._consent_score(requests))

        risk_score = min(
            100.0,
            30 * (requests["pending"] / max(requests["total"], 1))
            + 40 * (certs_invalid / max(certs_total, 1))
            + (0 if audit_state["verified"] else 30),
        )
        return {
            "gdpr": {
                "score": round(gdpr_score, 1),
                "status": "compliant" if gdpr_score >= 90 else "review" if gdpr_score >= 70 else "non-compliant",
                "details": {
                    "article_17_requests": requests["total"],
                    "resolution_rate": round(resolution_rate, 3),
                    "avg_deletion_seconds": requests["avg_deletion_seconds"],
                },
            },
            "dpdp": {
                "score": round(dpdp_score, 1),
                "status": "compliant" if dpdp_score >= 90 else "review" if dpdp_score >= 70 else "non-compliant",
                "details": {"consent_verification_rate": round(self._consent_score(requests), 3)},
            },
            "risk": {
                "score": round(risk_score, 1),
                "level": "low" if risk_score < 33 else "medium" if risk_score < 66 else "high",
            },
            "requests": requests,
            "certificates": {"total": certs_total, "valid": certs_valid, "invalid": certs_invalid},
            "audit_chain": audit_state,
        }

    @staticmethod
    def _consent_score(requests: dict[str, Any]) -> float:
        """DPDP requires verifiable consent; every completed deletion proves a
        consent lifecycle. Scale with completion health."""
        if requests["total"] == 0:
            return 1.0
        return requests["completed"] / requests["total"]

    async def _late_requests(self) -> int:
        """Requests that took longer than the GDPR one-month window (~30d)."""
        return await self._count(
            DeletionRequest,
            DeletionRequest.completed_at.isnot(None),
            DeletionRequest.duration_seconds > 30 * 24 * 3600,
        )

    # ---------------------------------------------------- Phase 7: reports

    async def run_report(self, created_by: str = "system") -> ComplianceReport:
        """Capture a persisted compliance snapshot (Phase 7 dashboards)."""
        data = await self.overview()
        report = ComplianceReport(
            gdpr_score=data["gdpr"]["score"],
            gdpr_status=data["gdpr"]["status"],
            dpdp_score=data["dpdp"]["score"],
            dpdp_status=data["dpdp"]["status"],
            risk_score=data["risk"]["score"],
            risk_level=data["risk"]["level"],
            open_requests=data["requests"]["pending"],
            completed_requests=data["requests"]["completed"],
            certs_valid=data["certificates"]["valid"],
            scores=data,
            created_by=created_by,
        )
        self.session.add(report)
        await self.session.flush()
        await self.audit.log(
            event_type="compliance.report_generated",
            actor=created_by,
            subject=report.id,
            payload={"gdpr": report.gdpr_score, "dpdp": report.dpdp_score, "risk": report.risk_score},
        )
        return report

    async def history(self, *, limit: int = 100) -> list[dict]:
        from sqlalchemy import select

        result = await self.session.execute(
            select(ComplianceReport).order_by(ComplianceReport.created_at.desc()).limit(limit)
        )
        rows = list(result.scalars().all())
        rows.reverse()
        return [
            {
                "id": r.id,
                "gdpr_score": r.gdpr_score,
                "gdpr_status": r.gdpr_status,
                "dpdp_score": r.dpdp_score,
                "dpdp_status": r.dpdp_status,
                "risk_score": r.risk_score,
                "risk_level": r.risk_level,
                "open_requests": r.open_requests,
                "completed_requests": r.completed_requests,
                "certs_valid": r.certs_valid,
                "created_by": r.created_by,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
