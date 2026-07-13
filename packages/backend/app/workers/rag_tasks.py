from typing import Any

from app.workers.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, name="rag.process_document")
def process_document(self, document_id: str) -> dict:
    logger.info("Processing document %s", document_id)
    return {
        "document_id": document_id,
        "status": "completed",
        "chunks_created": 0,
    }


@celery_app.task(bind=True, name="rag.generate_embeddings")
def generate_embeddings(self, document_id: str) -> dict:
    logger.info("Generating embeddings for document %s", document_id)
    return {
        "document_id": document_id,
        "embeddings_generated": 0,
        "status": "completed",
    }


@celery_app.task(bind=True, name="rag.ocr_process")
def ocr_process(self, document_id: str) -> dict:
    logger.info("Running OCR on document %s", document_id)
    return {
        "document_id": document_id,
        "pages_processed": 0,
        "status": "completed",
    }
