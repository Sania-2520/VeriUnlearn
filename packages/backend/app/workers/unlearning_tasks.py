import uuid
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.infrastructure.database.models import UnlearningJobModel, UnlearningRequestModel
from app.infrastructure.external.ml_engine import MLEngineClientError, ml_engine_client
from app.workers.celery_app import celery_app
from app.workers.session import worker_session
from app.workers.utils import _run_async

logger = get_logger(__name__)


@celery_app.task(bind=True, name="unlearning.execute")
def execute_unlearning(self, request_id: str) -> dict:
    logger.info("Executing unlearning request %s", request_id)
    with worker_session() as session:
        req = session.query(UnlearningRequestModel).filter_by(id=request_id).first()
        if not req:
            logger.error("Unlearning request %s not found", request_id)
            return {"request_id": request_id, "status": "not_found"}

        try:
            req.status = "processing"
            session.flush()

            result: dict = _run_async(ml_engine_client.execute_unlearning(
                target_data_ids=[req.target_id],
                model_type=req.target_type or "transformer",
                data_size=1,
                regulatory=req.gdpr_article or "gdpr",
            ))

            req.status = "completed" if result.get("success") else "failed"
            session.flush()

            job = UnlearningJobModel(
                id=str(uuid.uuid4()),
                request_id=request_id,
                algorithm=result.get("algorithm", "hybrid"),
                model_id=req.target_id,
                status="completed" if result.get("success") else "failed",
                progress=100 if result.get("success") else 0,
                error_message=result.get("error_message"),
                processing_time_ms=result.get("processing_time_ms"),
            )
            session.add(job)

            return {
                "request_id": request_id,
                "job_id": str(job.id),
                "status": req.status,
                "algorithm": job.algorithm,
            }

        except MLEngineClientError as e:
            req.status = "failed"
            logger.error("Unlearning failed for %s: %s", request_id, str(e))
            return {"request_id": request_id, "status": "failed", "error": str(e)}


@celery_app.task(bind=True, name="unlearning.generate_proof")
def generate_deletion_proof(self, prev_result: dict) -> dict:
    job_id = prev_result.get("job_id", "")
    request_id = prev_result.get("request_id", "")
    logger.info("Generating deletion proof for job %s (request %s)", job_id, request_id)
    with worker_session() as session:
        if job_id:
            job = session.query(UnlearningJobModel).filter_by(id=job_id).first()
            if not job:
                return {"job_id": job_id, "request_id": request_id, "status": "not_found"}
            target_id = job.model_id or request_id
        else:
            target_id = request_id

        try:
            proof: dict = _run_async(ml_engine_client.generate_proof(
                deletion_steps=[target_id or job_id or request_id],
                algorithm="ed25519",
            ))

            return {
                "job_id": job_id,
                "request_id": request_id,
                "proof_id": proof.get("merkle_root", ""),
                "merkle_root": proof.get("merkle_root", ""),
                "leaf_count": proof.get("leaf_count", 0),
                "signature_hex": proof.get("signature_hex", ""),
                "status": "completed",
            }

        except MLEngineClientError as e:
            logger.error("Proof generation failed for %s: %s", job_id, str(e))
            return {"job_id": job_id, "request_id": request_id, "status": "failed", "error": str(e)}


@celery_app.task(bind=True, name="unlearning.cleanup_queue")
def cleanup_deletion_queue(self) -> dict:
    logger.info("Cleaning up deletion queue")
    with worker_session() as session:
        from app.core.metrics import deletion_queue_size, unlearning_queue_size
        from app.infrastructure.database.models import DeletionQueueItemModel

        stale = (
            session.query(DeletionQueueItemModel)
            .filter(DeletionQueueItemModel.status == "pending")
            .count()
        )
        deletion_queue_size.labels(status="pending").set(stale)

        pending_requests = (
            session.query(UnlearningRequestModel)
            .filter(UnlearningRequestModel.status == "pending")
            .count()
        )
        unlearning_queue_size.labels(status="pending").set(pending_requests)
        return {"status": "completed", "stale_items": stale, "pending_requests": pending_requests}


@celery_app.task(bind=True, name="unlearning.generate_compliance_report")
def generate_compliance_report(self, prev_result: dict) -> dict:
    request_id = prev_result.get("request_id", "")
    proof_id = prev_result.get("proof_id", "")
    logger.info("Generating compliance report for request %s (proof %s)", request_id, proof_id)
    with worker_session() as session:
        from app.infrastructure.database.models import UnlearningRequestModel

        req = session.query(UnlearningRequestModel).filter_by(id=request_id).first()
        if not req:
            return {"request_id": request_id, "status": "not_found"}

        req.compliance_verified = True
        req.compliance_timestamp = datetime.now(timezone.utc)
        session.flush()

        return {
            "request_id": request_id,
            "proof_id": proof_id,
            "status": "completed",
            "compliance_verified": True,
            "generated_at": req.compliance_timestamp.isoformat(),
        }


def dispatch_unlearning_workflow(request_id: str) -> dict:
    """Dispatch the full unlearning workflow as a Celery chain.

    Chain: execute_unlearning → generate_deletion_proof → generate_compliance_report
    """
    from celery import chain as celery_chain  # type: ignore[import-untyped]  # no stubs shipped

    workflow = celery_chain(
        execute_unlearning.s(request_id=request_id),
        generate_deletion_proof.s(),
        generate_compliance_report.s(),
    )
    workflow.delay()
    logger.info("Dispatched unlearning workflow chain for request %s", request_id)
    return {
        "request_id": request_id,
        "status": "dispatched",
        "workflow": "execute_unlearning → generate_deletion_proof → generate_compliance_report",
    }
