
from app.core.logging import get_logger
from app.infrastructure.database.models import RagDocumentModel
from app.infrastructure.external.ml_engine import MLEngineClientError, ml_engine_client
from app.workers.celery_app import celery_app
from app.workers.session import worker_session
from app.workers.utils import _run_async

logger = get_logger(__name__)


@celery_app.task(bind=True, name="rag.process_document")
def process_document(self, document_id: str) -> dict:
    logger.info("Processing document %s", document_id)
    with worker_session() as session:
        doc = session.query(RagDocumentModel).filter_by(id=document_id).first()
        if not doc:
            logger.error("Document %s not found", document_id)
            return {"document_id": document_id, "status": "not_found", "chunks_created": 0}

        try:
            doc.status = "processing"
            session.flush()

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
            doc.status = "failed"
            doc.error_message = str(e)
            logger.error("Document processing failed for %s: %s", document_id, str(e))
            return {"document_id": document_id, "status": "failed", "chunks_created": 0, "error": str(e)}


@celery_app.task(bind=True, name="rag.generate_embeddings")
def generate_embeddings(self, document_id: str) -> dict:
    logger.info("Generating embeddings for document %s", document_id)
    with worker_session() as session:
        doc = session.query(RagDocumentModel).filter_by(id=document_id).first()
        if not doc:
            return {"document_id": document_id, "embeddings_generated": 0, "status": "not_found"}

        try:
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
            logger.error("Embedding generation failed for %s: %s", document_id, str(e))
            return {"document_id": document_id, "embeddings_generated": 0, "status": "failed", "error": str(e)}


@celery_app.task(bind=True, name="rag.ocr_process")
def ocr_process(self, document_id: str) -> dict:
    logger.info("Running OCR on document %s", document_id)
    with worker_session() as session:
        doc = session.query(RagDocumentModel).filter_by(id=document_id).first()
        if not doc:
            return {"document_id": document_id, "pages_processed": 0, "status": "not_found"}

        try:
            doc.status = "processing"
            session.flush()

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
            doc.status = "failed"
            doc.error_message = str(e)
            logger.error("OCR processing failed for %s: %s", document_id, str(e))
            return {"document_id": document_id, "pages_processed": 0, "status": "failed", "error": str(e)}
