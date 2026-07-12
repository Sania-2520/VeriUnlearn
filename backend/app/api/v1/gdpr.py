from __future__ import annotations


from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.dependencies import DatabaseDep, CurrentUser
from app.services.gdpr_service import GDPRService

router = APIRouter(prefix="/gdpr", tags=["GDPR"])


@router.get("/export")
async def export_my_data(user: CurrentUser, db: DatabaseDep):
    service = GDPRService(db)
    data = await service.export_user_data(user)
    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": f'attachment; filename="veriunlearn_export_{user.id}.json"',
        },
    )


@router.delete("/delete-account", status_code=status.HTTP_200_OK)
async def delete_my_account(user: CurrentUser, db: DatabaseDep):
    service = GDPRService(db)
    result = await service.delete_user_account(user)
    return {"status": "deleted", "details": result}
