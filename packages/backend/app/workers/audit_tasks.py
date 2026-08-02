from app.core.logging import get_logger
from app.workers.celery_app import celery_app
from app.workers.session import worker_session

logger = get_logger(__name__)


@celery_app.task(bind=True, name="audit.anchor_chains")
def anchor_all_chains(self) -> dict:
    """Anchor all tenant audit chains to the blockchain."""
    logger.info("Starting periodic blockchain anchoring for all tenants")
    anchored = 0
    failed = 0

    with worker_session() as session:
        from app.domain.audit.services import AuditService
        from app.infrastructure.database.repositories.audit import (
            SQLAlchemyAuditEventRepository,
        )

        repo = SQLAlchemyAuditEventRepository(session=session)
        audit_svc = AuditService(repo=repo)

        import asyncio

        async def _run():
            tenant_ids = await repo.get_all_tenant_ids()
            if not tenant_ids:
                return None
            results = []
            for tid in tenant_ids:
                result = await audit_svc.anchor_chain(tid)
                results.append((tid, result))
            return results

        try:
            results = asyncio.run(_run())
        except Exception:
            logger.exception("Failed to run audit anchoring")
            return {"status": "completed", "anchored": 0, "failed": 0}

        if results is None:
            logger.info("No tenants found to anchor")
            return {"status": "completed", "anchored": 0, "failed": 0}

        for tid, result in results:
            if result.get("anchored"):
                anchored += 1
                logger.info("Anchored chain for tenant %s: tx=%s", tid[:16], result.get("tx_hash", "")[:16])
            else:
                logger.info("Skipped anchor for tenant %s: %s", tid[:16], result.get("reason", "unknown"))

    return {"status": "completed", "anchored": anchored, "failed": failed}
