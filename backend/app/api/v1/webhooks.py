from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.dependencies import CurrentUser
from app.services.webhook_service import webhook_service, WebhookConfig

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


class WebhookCreate(BaseModel):
    url: str
    secret: str | None = None
    events: list[str] = ["training.completed", "training.failed"]


class WebhookResponse(BaseModel):
    url: str
    events: list[str]
    enabled: bool


@router.get("/", response_model=list[WebhookResponse])
async def list_webhooks(user: CurrentUser):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return [WebhookResponse(**w.model_dump()) for w in webhook_service.get_webhooks()]


@router.post("/", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(body: WebhookCreate, user: CurrentUser):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    config = WebhookConfig(url=body.url, secret=body.secret, events=body.events)
    webhook_service.register(config)
    return WebhookResponse(**config.model_dump())


@router.delete("/{url:path}")
async def delete_webhook(url: str, user: CurrentUser):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    removed = webhook_service.unregister(url)
    if not removed:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"status": "removed"}


@router.get("/deliveries")
async def get_deliveries(user: CurrentUser):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return webhook_service.get_delivery_log()
