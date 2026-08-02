from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import desc, func, select

from app.api.deps import CurrentUser, DatabaseSession, default_rate_limiter, require_permission
from app.core.logging import get_logger
from app.core.rbac import Permission
from app.infrastructure.database.models import RagDocumentModel
from app.infrastructure.external.ml_engine import MLEngineClientError, ml_engine_client

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(default_rate_limiter), Depends(require_permission(Permission.RAG))])


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    filters: dict = {}
    hybrid: bool = True


ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "text/csv",
    "application/json",
    "text/html",
    "text/markdown",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "image/png",
    "image/jpeg",
    "image/webp",
}


@router.post("/documents/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    current_user: CurrentUser,
    session: DatabaseSession,
    file: UploadFile = File(...),
    metadata: str = Form("{}"),
):
    import json as _json
    import os

    from app.core.config import settings

    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}",
        )

    doc_id = str(uuid4())
    now = datetime.now(timezone.utc)
    file_content = await file.read()

    max_size = settings.max_upload_size_bytes
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large ({len(file_content)} bytes). Maximum allowed: {max_size} bytes",
        )

    try:
        text = file_content.decode("utf-8")
    except UnicodeDecodeError:
        text = ""
        logger.warning("Could not decode file %s as UTF-8, ingesting raw bytes", file.filename)
    try:
        parsed_metadata = _json.loads(metadata)
    except _json.JSONDecodeError:
        parsed_metadata = {}
    parsed_metadata["filename"] = file.filename
    parsed_metadata["user_id"] = current_user["user_id"]
    parsed_metadata["tenant_id"] = current_user["tenant_id"]
    _, ext = os.path.splitext(file.filename or "")
    file_type = ext.lstrip(".").lower() or "txt"
    doc = RagDocumentModel(
        id=doc_id,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        filename=file.filename or "unknown",
        original_filename=file.filename or "unknown",
        file_type=file_type,
        file_size_bytes=len(file_content),
        storage_path="",
        mime_type=file.content_type,
        status="processing",
        event_metadata=parsed_metadata,
        created_at=now,
        updated_at=now,
    )
    session.add(doc)
    await session.flush()
    try:
        ml_result = await ml_engine_client.ingest_document(
            text=text,
            source_name=file.filename or "unknown",
            metadata=parsed_metadata,
        )
        doc.status = "indexed"
        doc.chunk_count = len(ml_result.get("chunks", [])) if ml_result else 0
    except MLEngineClientError as e:
        logger.error("ML engine ingestion failed for document %s: %s", doc_id, str(e))
        doc.status = "failed"
        doc.error_message = str(e)
    doc.updated_at = datetime.now(timezone.utc)
    await session.commit()
    return {"document_id": doc_id, "filename": file.filename, "status": doc.status}


@router.get("/documents")
async def list_documents(
    current_user: CurrentUser,
    session: DatabaseSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    file_type: Optional[str] = None,
):
    query = select(RagDocumentModel).where(
        RagDocumentModel.tenant_id == current_user["tenant_id"],
        RagDocumentModel.is_deleted == False,
    )
    count_query = select(func.count(RagDocumentModel.id)).where(
        RagDocumentModel.tenant_id == current_user["tenant_id"],
        RagDocumentModel.is_deleted == False,
    )
    if current_user.get("user_id"):
        query = query.where(RagDocumentModel.user_id == current_user["user_id"])
        count_query = count_query.where(RagDocumentModel.user_id == current_user["user_id"])
    if status_filter:
        query = query.where(RagDocumentModel.status == status_filter)
        count_query = count_query.where(RagDocumentModel.status == status_filter)
    if file_type:
        query = query.where(RagDocumentModel.file_type == file_type)
        count_query = count_query.where(RagDocumentModel.file_type == file_type)
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    query = query.order_by(desc(RagDocumentModel.created_at)).offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    docs = result.scalars().all()
    return {
        "data": [
            {
                "id": d.id,
                "filename": d.filename,
                "file_type": d.file_type,
                "file_size_bytes": d.file_size_bytes,
                "mime_type": d.mime_type,
                "status": d.status,
                "chunk_count": d.chunk_count,
                "metadata": d.event_metadata,
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "updated_at": d.updated_at.isoformat() if d.updated_at else None,
            }
            for d in docs
        ],
        "meta": {"page": page, "page_size": page_size, "total": total},
    }


@router.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    result = await session.execute(
        select(RagDocumentModel).where(
            RagDocumentModel.id == document_id,
            RagDocumentModel.tenant_id == current_user["tenant_id"],
            RagDocumentModel.is_deleted == False,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return {
        "id": doc.id,
        "filename": doc.filename,
        "original_filename": doc.original_filename,
        "file_type": doc.file_type,
        "file_size_bytes": doc.file_size_bytes,
        "mime_type": doc.mime_type,
        "status": doc.status,
        "chunk_count": doc.chunk_count,
        "metadata": doc.event_metadata,
        "error_message": doc.error_message,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
    }


@router.delete("/documents/{document_id}", status_code=status.HTTP_202_ACCEPTED)
async def delete_document(
    document_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    result = await session.execute(
        select(RagDocumentModel).where(
            RagDocumentModel.id == document_id,
            RagDocumentModel.tenant_id == current_user["tenant_id"],
            RagDocumentModel.is_deleted == False,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    doc.is_deleted = True
    doc.deleted_at = datetime.now(timezone.utc)
    await session.commit()
    return {"message": "Deletion initiated", "document_id": document_id, "unlearning_request_id": None}


@router.post("/search")
async def search_documents(
    request: SearchRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    try:
        ml_result = await ml_engine_client.search_documents(
            query=request.query,
            top_k=request.top_k,
            filters={
                **request.filters,
                "tenant_id": current_user["tenant_id"],
            },
        )
        results = ml_result.get("results", [])
    except MLEngineClientError as e:
        logger.error("ML engine search failed, falling back to local: %s", str(e))
        result = await session.execute(
            select(RagDocumentModel).where(
                RagDocumentModel.tenant_id == current_user["tenant_id"],
                RagDocumentModel.status == "indexed",
                RagDocumentModel.is_deleted == False,
            ).limit(request.top_k)
        )
        local_docs = result.scalars().all()
        results = [
            {
                "id": d.id,
                "filename": d.filename,
                "score": 0.0,
                "text": f"[Local fallback] {d.filename}",
            }
            for d in local_docs
        ]
    return {"results": results}
