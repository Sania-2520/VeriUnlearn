from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.dependencies import CurrentUser
from app.services.backup_service import BackupService

router = APIRouter(prefix="/backup", tags=["Backup"])


class BackupCreate(BaseModel):
    name: str | None = None


@router.get("/")
async def list_backups(user: CurrentUser):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    service = BackupService()
    return service.list_backups()


@router.post("/", status_code=201)
async def create_backup(body: BackupCreate, user: CurrentUser):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    service = BackupService()
    return service.create_backup(name=body.name)


@router.post("/restore/{backup_name}")
async def restore_backup(backup_name: str, user: CurrentUser):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    service = BackupService()
    try:
        return service.restore_backup(backup_name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{backup_name}")
async def delete_backup(backup_name: str, user: CurrentUser):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    service = BackupService()
    if not service.delete_backup(backup_name):
        raise HTTPException(status_code=404, detail="Backup not found")
    return {"status": "deleted"}
