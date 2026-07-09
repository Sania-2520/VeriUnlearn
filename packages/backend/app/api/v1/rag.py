from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, status
from pydantic import BaseModel
from typing import Optional

from app.api.deps import CurrentUser, DatabaseSession, default_rate_limiter, require_permission
from app.core.rbac import Permission

router = APIRouter(dependencies=[Depends(default_rate_limiter), Depends(require_permission(Permission.RAG))])


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
    return {"document_id": "placeholder", "filename": file.filename, "status": "processing"}


@router.get("/documents")
async def list_documents(
    current_user: CurrentUser,
    session: DatabaseSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    file_type: Optional[str] = None,
):
    return {"data": [], "meta": {"page": page, "page_size": page_size, "total": 0}}


@router.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    return {"id": document_id, "filename": "", "status": "indexed"}


@router.delete("/documents/{document_id}", status_code=status.HTTP_202_ACCEPTED)
async def delete_document(
    document_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    return {"message": "Deletion initiated", "unlearning_request_id": "placeholder"}


@router.post("/search")
async def search_documents(
    request: SearchRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    return {"results": []}
