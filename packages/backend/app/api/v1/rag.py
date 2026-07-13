from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, DatabaseSession, default_rate_limiter, require_permission
from app.core.logging import get_logger
from app.core.rbac import Permission
from app.infrastructure.external.ml_engine import ml_engine_client, MLEngineClientError

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(default_rate_limiter), Depends(require_permission(Permission.RAG))])

_documents: dict[str, dict] = {}


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    filters: dict = {}
    hybrid: bool = True


@router.post("/documents/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    current_user: CurrentUser,
    session: DatabaseSession,
    file: UploadFile = File(...),
    metadata: str = Form("{}"),
):
    import json as _json
    doc_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    try:
        file_content = await file.read()
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
    doc_record = {
        "id": doc_id,
        "filename": file.filename,
        "status": "processing",
        "source_name": file.filename,
        "size_bytes": len(file_content) if file_content else 0,
        "content_type": file.content_type,
        "metadata": parsed_metadata,
        "user_id": current_user["user_id"],
        "tenant_id": current_user["tenant_id"],
        "created_at": now,
        "updated_at": now,
    }
    _documents[doc_id] = doc_record
    try:
        ml_result = await ml_engine_client.ingest_document(
            text=text,
            source_name=file.filename,
            metadata=parsed_metadata,
        )
        doc_record["status"] = "indexed"
        doc_record["ml_result"] = ml_result
    except MLEngineClientError as e:
        logger.error("ML engine ingestion failed for document %s: %s", doc_id, str(e))
        doc_record["status"] = "failed"
        doc_record["error"] = str(e)
    doc_record["updated_at"] = datetime.now(timezone.utc).isoformat()
    return {"document_id": doc_id, "filename": file.filename, "status": doc_record["status"]}


@router.get("/documents")
async def list_documents(
    current_user: CurrentUser,
    session: DatabaseSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    file_type: Optional[str] = None,
):
    user_docs = [
        d for d in _documents.values()
        if d["user_id"] == current_user["user_id"] and d["tenant_id"] == current_user["tenant_id"]
    ]
    if status_filter:
        user_docs = [d for d in user_docs if d.get("status") == status_filter]
    if file_type:
        user_docs = [d for d in user_docs if d.get("content_type") == file_type]
    user_docs.sort(key=lambda d: d.get("created_at", ""), reverse=True)
    total = len(user_docs)
    start = (page - 1) * page_size
    end = start + page_size
    return {"data": user_docs[start:end], "meta": {"page": page, "page_size": page_size, "total": total}}


@router.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    doc = _documents.get(document_id)
    if not doc or doc["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return {
        "id": doc["id"],
        "filename": doc["filename"],
        "status": doc["status"],
        "size_bytes": doc.get("size_bytes", 0),
        "content_type": doc.get("content_type"),
        "metadata": doc.get("metadata", {}),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }


@router.delete("/documents/{document_id}", status_code=status.HTTP_202_ACCEPTED)
async def delete_document(
    document_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    doc = _documents.get(document_id)
    if not doc or doc["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    del _documents[document_id]
    return {"message": "Deletion initiated", "unlearning_request_id": None}


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
        logger.error("ML engine search failed: %s", str(e))
        local_docs = [
            d for d in _documents.values()
            if d["tenant_id"] == current_user["tenant_id"]
        ]
        results = [
            {
                "id": d["id"],
                "filename": d["filename"],
                "score": 0.0,
                "text": f"[Local fallback] {d['filename']}",
            }
            for d in local_docs[:request.top_k]
        ]
    return {"results": results}
