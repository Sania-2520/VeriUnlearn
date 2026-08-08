
from app.core.logging import get_logger
from app.infrastructure.database.models import RagDocumentModel
from app.infrastructure.external.ml_engine import MLEngineClientError, ml_engine_client
from app.workers.celery_app import celery_app
from app.workers.session import worker_session
from app.workers.utils import _run_async

logger = get_logger(__name__)

# Maximum number of times a RAG task retries transient ML Engine failures
# (connection errors, 429, 5xx). Permanent failures (4xx) are never retried.
RAG_TASK_MAX_RETRIES = 3


@celery_app.task(bind=True, name="rag.process_document", max_retries=RAG_TASK_MAX_RETRIES)
def process_document(self, document_id: str) -> dict:
    logger.info("Processing document %s", document_id)
    with worker_session() as session:
        doc = session.query(RagDocumentModel).filter_by(id=document_id).first()
        if not doc:
            logger.error("Document %s not found", document_id)
            return {"document_id": document_id, "status": "not_found", "chunks_created": 0}

        try:
            doc.status = "processing"
            doc.error_message = None
            session.flush()

            self.update_state(
                state="PROGRESS",
                meta={"document_id": document_id, "stage": "parsing_and_chunking"},
            )

            result: dict = _run_async(ml_engine_client.process_document(
                document_id=document_id,
                filename=doc.filename,
                file_type=doc.file_type,
                storage_path=doc.storage_path,
            ))

            doc.status = "completed" if result.get("success") else "failed"
            doc.chunk_count = result.get("chunks_created", 0)
            session.flush()

            return {
                "document_id": document_id,
                "status": doc.status,
                "chunks_created": doc.chunk_count,
            }

        except MLEngineClientError as e:
            if e.is_transient and self.request.retries < self.max_retries:
                logger.warning(
                    "Transient ML Engine failure for document %s (attempt %d/%d): %s — retrying",
                    document_id, self.request.retries + 1, self.max_retries + 1, str(e),
                )
                # Keep the document in "processing" while retries are pending
                # so callers observe progress rather than a premature failure.
                doc.status = "processing"
                doc.error_message = str(e)
                session.commit()
                raise self.retry(exc=e, countdown=min(2 ** self.request.retries * 5, 60))

            doc.status = "failed"
            doc.error_message = str(e)
            logger.error("Document processing failed for %s: %s", document_id, str(e))
            return {"document_id": document_id, "status": "failed", "chunks_created": 0, "error": str(e)}


@celery_app.task(bind=True, name="rag.generate_embeddings", max_retries=RAG_TASK_MAX_RETRIES)
def generate_embeddings(self, document_id: str) -> dict:
    logger.info("Generating embeddings for document %s", document_id)
    with worker_session() as session:
        doc = session.query(RagDocumentModel).filter_by(id=document_id).first()
        if not doc:
            return {"document_id": document_id, "embeddings_generated": 0, "status": "not_found"}

        try:
            self.update_state(
                state="PROGRESS",
                meta={"document_id": document_id, "stage": "embedding"},
            )

            result: dict = _run_async(ml_engine_client.generate_embeddings(
                document_id=document_id,
                chunk_count=doc.chunk_count,
            ))

            return {
                "document_id": document_id,
                "embeddings_generated": result.get("embeddings_generated", 0),
                "status": "completed",
            }

        except MLEngineClientError as e:
            if e.is_transient and self.request.retries < self.max_retries:
                logger.warning(
                    "Transient ML Engine failure for embeddings of %s (attempt %d/%d): %s — retrying",
                    document_id, self.request.retries + 1, self.max_retries + 1, str(e),
                )
                raise self.retry(exc=e, countdown=min(2 ** self.request.retries * 5, 60))

            logger.error("Embedding generation failed for %s: %s", document_id, str(e))
            return {"document_id": document_id, "embeddings_generated": 0, "status": "failed", "error": str(e)}


@celery_app.task(bind=True, name="rag.ocr_process", max_retries=RAG_TASK_MAX_RETRIES)
def ocr_process(self, document_id: str) -> dict:
    logger.info("Running OCR on document %s", document_id)
    with worker_session() as session:
        doc = session.query(RagDocumentModel).filter_by(id=document_id).first()
        if not doc:
            return {"document_id": document_id, "pages_processed": 0, "status": "not_found"}

        try:
            doc.status = "processing"
            doc.error_message = None
            session.flush()

            self.update_state(
                state="PROGRESS",
                meta={"document_id": document_id, "stage": "ocr"},
            )

            result: dict = _run_async(ml_engine_client.ocr_process(
                document_id=document_id,
                storage_path=doc.storage_path,
                file_type=doc.file_type,
            ))

            doc.status = "completed" if result.get("success") else "failed"
            doc.page_count = result.get("pages_processed", 0)
            session.flush()

            return {
                "document_id": document_id,
                "pages_processed": doc.page_count,
                "status": doc.status,
            }

        except MLEngineClientError as e:
            if e.is_transient and self.request.retries < self.max_retries:
                logger.warning(
                    "Transient ML Engine failure for OCR of %s (attempt %d/%d): %s — retrying",
                    document_id, self.request.retries + 1, self.max_retries + 1, str(e),
                )
                doc.status = "processing"
                doc.error_message = str(e)
                session.commit()
                raise self.retry(exc=e, countdown=min(2 ** self.request.retries * 5, 60))

            doc.status = "failed"
            doc.error_message = str(e)
            logger.error("OCR processing failed for %s: %s", document_id, str(e))
            return {"document_id": document_id, "pages_processed": 0, "status": "failed", "error": str(e)}
