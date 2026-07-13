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
        from app.infrastructure.database.repositories.audit import (
            SQLAlchemyAuditEventRepository,
        )
        from app.domain.audit.services import AuditService

        repo = SQLAlchemyAuditEventRepository.__new__(SQLAlchemyAuditEventRepository)
        repo._session = session

        audit_svc = AuditService(repo=repo)

        import asyncio

        tenant_ids = asyncio.run(repo.get_all_tenant_ids())
        if not tenant_ids:
            logger.info("No tenants found to anchor")
            return {"status": "completed", "anchored": 0, "failed": 0}

        for tid in tenant_ids:
            try:
                result = asyncio.run(audit_svc.anchor_chain(tid))
                if result.get("anchored"):
                    anchored += 1
                    logger.info("Anchored chain for tenant %s: tx=%s", tid[:16], result.get("tx_hash", "")[:16])
                else:
                    logger.info("Skipped anchor for tenant %s: %s", tid[:16], result.get("reason", "unknown"))
            except Exception as e:
                failed += 1
                logger.error("Failed to anchor chain for tenant %s: %s", tid[:16], str(e))

    return {"status": "completed", "anchored": anchored, "failed": failed}
