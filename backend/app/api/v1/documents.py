from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.dependencies import DatabaseDep, CurrentUser
from app.schemas.document import DocumentResponse
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/octet-stream",
}

MAX_FILE_SIZE = 10 * 1024 * 1024


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(user: CurrentUser, db: DatabaseDep, file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_CONTENT_TYPES and file.content_type is not None:
        if not file.filename or not any(file.filename.endswith(ext) for ext in (".txt", ".md", ".pdf")):
            raise HTTPException(status_code=400, detail="Only PDF, TXT, and MD files are allowed")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 10MB size limit")

    service = DocumentService(db)
    doc = await service.upload_document(
        user=user,
        filename=file.filename or "unnamed",
        content_type=file.content_type or "application/octet-stream",
        file_obj=content,
    )
    return doc


@router.post("/{document_id}/process", response_model=dict)
async def process_document(document_id: int, user: CurrentUser, db: DatabaseDep):
    service = DocumentService(db)
    try:
        chunk_count = await service.process_document(document_id)
        return {"document_id": document_id, "chunks": chunk_count, "status": "processed"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(user: CurrentUser, db: DatabaseDep):
    service = DocumentService(db)
    return await service.get_documents(user_id=user.id)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: int, user: CurrentUser, db: DatabaseDep):
    service = DocumentService(db)
    doc = await service.get_document(document_id)
    if doc is None or doc.user_id != user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: int, user: CurrentUser, db: DatabaseDep):
    service = DocumentService(db)
    deleted = await service.delete_document(document_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
