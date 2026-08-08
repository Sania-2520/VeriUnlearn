"""RAG document management and retrieval endpoints."""

import logging

from fastapi import APIRouter, HTTPException

from api import deps
from api.schemas import (
    RAGEmbeddingsRequest,
    RAGOCRRequest,
    RAGProcessRequest,
    RAGSearchRequest,
    RAGUploadRequest,
    RAGVectorDeleteRequest,
    RAGVectorUpsertRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/rag/documents/process")
async def process_document(request: RAGProcessRequest):
    """Asynchronously process and index a document (Celery worker path).

    Real work: parses the file (or inline text), chunks, embeds and indexes
    into the vector store — identical pipeline to the synchronous upload path.
    """
    pipeline = deps.get_rag_pipeline()
    try:
        doc = pipeline.process_document(
            document_id=request.document_id,
            filename=request.filename,
            file_type=request.file_type,
            storage_path=request.storage_path,
            text=request.text,
            metadata=request.metadata,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception:
        logger.exception("process_document failed for document %s", request.document_id)
        raise HTTPException(status_code=422, detail="Document processing failed")
    return {
        "document_id": doc.document_id,
        "filename": doc.filename,
        "status": doc.status,
        "success": doc.status == "indexed",
        "chunks_created": doc.chunk_count,
        "error_message": doc.error_message,
    }


@router.post("/rag/embeddings/generate")
async def generate_embeddings(request: RAGEmbeddingsRequest):
    """(Re)generate embeddings for every chunk of an indexed document."""
    pipeline = deps.get_rag_pipeline()
    count = pipeline.regenerate_embeddings(request.document_id)
    if count == 0:
        raise HTTPException(status_code=404, detail=f"Document {request.document_id} not found or has no chunks")
    return {
        "document_id": request.document_id,
        "embeddings_generated": count,
        "status": "completed",
    }


@router.post("/rag/documents/ocr")
async def ocr_process(request: RAGOCRRequest):
    """Extract text from a scanned/PDF document via OCR and index it."""
    pipeline = deps.get_rag_pipeline()
    try:
        doc = pipeline.ocr_process(
            document_id=request.document_id,
            storage_path=request.storage_path,
            file_type=request.file_type,
            metadata=request.metadata,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception:
        logger.exception("ocr_process failed for document %s", request.document_id)
        raise HTTPException(status_code=422, detail="OCR processing failed")
    return {
        "document_id": doc.document_id,
        "status": doc.status,
        "success": doc.status == "indexed",
        "chunks_created": doc.chunk_count,
        "pages_processed": doc.metadata.get("page_count", 0),
        "error_message": doc.error_message,
    }


@router.post("/rag/vectors/upsert")
async def upsert_vector(request: RAGVectorUpsertRequest):
    """Upsert a raw vector into an arbitrary collection (memory pipeline)."""
    pipeline = deps.get_rag_pipeline()
    pipeline.upsert_vector(
        collection=request.collection,
        point_id=request.point_id,
        vector=request.vector,
        payload=request.payload,
    )
    return {"success": True, "collection": request.collection, "point_id": request.point_id}


@router.post("/rag/vectors/delete")
async def delete_vectors(request: RAGVectorDeleteRequest):
    """Delete vectors matching an exact-match payload filter."""
    pipeline = deps.get_rag_pipeline()
    deleted = pipeline.delete_vectors(request.collection, request.filter)
    return {"success": True, "collection": request.collection, "deleted": deleted}


@router.post("/rag/documents/ingest")
async def ingest_document(request: RAGUploadRequest):
    pipeline = deps.get_rag_pipeline()
    result = pipeline.ingest_text(
        text=request.text,
        source_name=request.source_name,
        metadata=request.metadata,
    )
    return result


@router.post("/rag/documents/ingest-text")
async def ingest_text(request: RAGUploadRequest):
    pipeline = deps.get_rag_pipeline()
    result = pipeline.ingest_text(
        text=request.text,
        source_name=request.source_name,
        metadata=request.metadata,
    )
    return result


@router.get("/rag/documents")
async def list_documents():
    pipeline = deps.get_rag_pipeline()
    return pipeline.list_documents()


@router.get("/rag/documents/{document_id}")
async def get_document(document_id: str):
    pipeline = deps.get_rag_pipeline()
    doc = pipeline.get_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    return doc


@router.delete("/rag/documents/{document_id}")
async def delete_document(document_id: str):
    pipeline = deps.get_rag_pipeline()
    result = pipeline.delete_document(document_id)
    return result


@router.post("/rag/search")
async def search_documents(request: RAGSearchRequest):
    pipeline = deps.get_rag_pipeline()
    results = pipeline.search(
        query=request.query,
        top_k=request.top_k,
        filters=request.filters,
    )
    return results


@router.get("/rag/stats")
async def rag_stats():
    pipeline = deps.get_rag_pipeline()
    return pipeline.get_stats()
