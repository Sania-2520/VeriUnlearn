import asyncio
import uuid
from typing import Any

from celery import Task

from app.core.logging import get_logger
from app.infrastructure.external.ml_engine import ml_engine_client, MLEngineClientError
from app.infrastructure.database.models import UnlearningRequestModel, UnlearningJobModel
from app.workers.celery_app import celery_app
from app.workers.session import worker_session

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

            result = asyncio.run(ml_engine_client.execute_unlearning(
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
                "status": req.status,
                "algorithm": job.algorithm,
            }

        except MLEngineClientError as e:
            req.status = "failed"
            logger.error("Unlearning failed for %s: %s", request_id, str(e))
            return {"request_id": request_id, "status": "failed", "error": str(e)}


@celery_app.task(bind=True, name="unlearning.generate_proof")
def generate_deletion_proof(self, job_id: str) -> dict:
    logger.info("Generating deletion proof for job %s", job_id)
    with worker_session() as session:
        job = session.query(UnlearningJobModel).filter_by(id=job_id).first()
        if not job:
            return {"job_id": job_id, "status": "not_found"}

        try:
            proof = asyncio.run(ml_engine_client.generate_proof(
                deletion_steps=[job.model_id or job_id],
                algorithm="ed25519",
            ))

            return {
                "job_id": job_id,
                "proof_id": proof.get("merkle_root", ""),
                "merkle_root": proof.get("merkle_root", ""),
                "leaf_count": proof.get("leaf_count", 0),
                "signature_hex": proof.get("signature_hex", ""),
                "status": "completed",
            }

        except MLEngineClientError as e:
            logger.error("Proof generation failed for %s: %s", job_id, str(e))
            return {"job_id": job_id, "status": "failed", "error": str(e)}


@celery_app.task(bind=True, name="unlearning.cleanup_queue")
def cleanup_deletion_queue(self) -> dict:
    logger.info("Cleaning up deletion queue")
    with worker_session() as session:
        from app.infrastructure.database.models import DeletionQueueItemModel

        stale = (
            session.query(DeletionQueueItemModel)
            .filter(DeletionQueueItemModel.status == "pending")
            .count()
        )
        return {"status": "completed", "stale_items": stale}
