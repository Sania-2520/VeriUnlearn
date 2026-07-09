from typing import Any

from app.workers.celery_app import celery_app
from app.workers.unlearning_tasks import AsyncTask


@celery_app.task(bind=True, base=AsyncTask, name="rag.process_document")
async def process_document(self, document_id: str) -> dict:
    return {
        "document_id": document_id,
        "status": "completed",
        "chunks_created": 0,
    }


@celery_app.task(bind=True, base=AsyncTask, name="rag.generate_embeddings")
async def generate_embeddings(self, document_id: str) -> dict:
    return {
        "document_id": document_id,
        "embeddings_generated": 0,
        "status": "completed",
    }


@celery_app.task(bind=True, base=AsyncTask, name="rag.ocr_process")
async def ocr_process(self, document_id: str) -> dict:
    return {
        "document_id": document_id,
        "pages_processed": 0,
        "status": "completed",
    }
