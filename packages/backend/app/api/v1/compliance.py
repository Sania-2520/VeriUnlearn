from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import (
    TenantID,
    TenantServiceDep,
    default_rate_limiter,
    require_permission,
)
from app.core.rbac import Permission

router = APIRouter(dependencies=[Depends(default_rate_limiter)])


# ─── Settings ────────────────────────────────────────────────


@router.get("/settings")
async def get_settings(
    current_user: Annotated[dict, Depends(require_permission(Permission.SETTINGS_READ))],
    tenant_service: TenantServiceDep = ...,
    tenant_id: TenantID = ...,
):
    settings = await tenant_service.get_settings(tenant_id)
    return {
        "timezone": settings.timezone,
        "date_format": settings.date_format,
        "notification_email": settings.notification_email,
        "gdpr_contact_email": settings.gdpr_contact_email,
        "data_retention_days": settings.data_retention_days,
        "max_failed_login_attempts": settings.max_failed_login_attempts,
        "session_timeout_minutes": settings.session_timeout_minutes,
        "mfa_enforced": settings.mfa_enforced,
        "audit_retention_days": settings.audit_retention_days,
        "webhook_retry_max_attempts": settings.webhook_retry_max_attempts,
        "webhook_retry_delay_seconds": settings.webhook_retry_delay_seconds,
        "webhook_timeout_ms": settings.webhook_timeout_ms,
        "allowed_ip_ranges": settings.allowed_ip_ranges,
        "custom_branding": settings.custom_branding,
    }


@router.put("/settings")
async def update_settings(
    body: dict,
    current_user: Annotated[dict, Depends(require_permission(Permission.SETTINGS_WRITE))],
    tenant_service: TenantServiceDep = ...,
    tenant_id: TenantID = ...,
):
    settings = await tenant_service.update_settings(
        tenant_id=tenant_id,
        settings_data=body,
        actor_id=current_user.get("user_id"),
    )
    return {"status": "updated", "settings": settings}


# ─── Webhooks ────────────────────────────────────────────────


@router.post("/webhooks", status_code=status.HTTP_201_CREATED)
async def create_webhook(
    name: str = Query(...),
    url: str = Query(...),
    events: list[str] = Query(...),
    retry_count: int = Query(3, ge=1, le=10),
    timeout_ms: int = Query(5000, ge=1000, le=30000),
    current_user: Annotated[dict, Depends(require_permission(Permission.WEBHOOKS_WRITE))] = ...,
    tenant_service: TenantServiceDep = ...,
    tenant_id: TenantID = ...,
):
    webhook = await tenant_service.create_webhook(
        tenant_id=tenant_id,
        name=name,
        url=url,
        events=events,
        retry_count=retry_count,
        timeout_ms=timeout_ms,
        actor_id=current_user.get("user_id"),
    )
    return {
        "id": webhook.id,
        "name": webhook.name,
        "url": webhook.url,
        "events": webhook.events,
        "status": webhook.status.value,
        "created_at": webhook.created_at.isoformat() if webhook.created_at else None,
    }


@router.get("/webhooks")
async def list_webhooks(
    current_user: Annotated[dict, Depends(require_permission(Permission.WEBHOOKS_READ))],
    tenant_service: TenantServiceDep = ...,
    tenant_id: TenantID = ...,
):
    webhooks = await tenant_service.list_webhooks(tenant_id)
    return {
        "data": [
            {
                "id": w.id,
                "name": w.name,
                "url": w.url,
                "events": w.events,
                "status": w.status.value,
                "is_active": w.is_active,
                "last_success_at": w.last_success_at.isoformat() if w.last_success_at else None,
                "last_failure_at": w.last_failure_at.isoformat() if w.last_failure_at else None,
                "created_at": w.created_at.isoformat() if w.created_at else None,
            }
            for w in webhooks
        ]
    }


@router.get("/webhooks/{webhook_id}")
async def get_webhook(
    webhook_id: str,
    current_user: Annotated[dict, Depends(require_permission(Permission.WEBHOOKS_READ))],
    tenant_service: TenantServiceDep = ...,
    tenant_id: TenantID = ...,
):
    webhook = await tenant_service.get_webhook(tenant_id, webhook_id)
    return {
        "id": webhook.id,
        "name": webhook.name,
        "url": webhook.url,
        "events": webhook.events,
        "status": webhook.status.value,
        "is_active": webhook.is_active,
        "headers": webhook.headers,
        "retry_count": webhook.retry_count,
        "timeout_ms": webhook.timeout_ms,
        "last_success_at": webhook.last_success_at.isoformat() if webhook.last_success_at else None,
        "last_failure_at": webhook.last_failure_at.isoformat() if webhook.last_failure_at else None,
        "consecutive_failures": webhook.consecutive_failures,
        "created_at": webhook.created_at.isoformat() if webhook.created_at else None,
        "updated_at": webhook.updated_at.isoformat() if webhook.updated_at else None,
    }


@router.put("/webhooks/{webhook_id}")
async def update_webhook(
    webhook_id: str,
    name: Optional[str] = None,
    url: Optional[str] = None,
    events: Optional[list[str]] = Query(None),
    is_active: Optional[bool] = None,
    retry_count: Optional[int] = Query(None, ge=1, le=10),
    timeout_ms: Optional[int] = Query(None, ge=1000, le=30000),
    current_user: Annotated[dict, Depends(require_permission(Permission.WEBHOOKS_WRITE))] = ...,
    tenant_service: TenantServiceDep = ...,
    tenant_id: TenantID = ...,
):
    webhook = await tenant_service.update_webhook(
        tenant_id=tenant_id,
        webhook_id=webhook_id,
        name=name,
        url=url,
        events=events,
        is_active=is_active,
        retry_count=retry_count,
        timeout_ms=timeout_ms,
        actor_id=current_user.get("user_id"),
    )
    return {
        "id": webhook.id,
        "name": webhook.name,
        "url": webhook.url,
        "events": webhook.events,
        "status": webhook.status.value,
        "is_active": webhook.is_active,
        "updated_at": webhook.updated_at.isoformat() if webhook.updated_at else None,
    }


@router.delete("/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: str,
    current_user: Annotated[dict, Depends(require_permission(Permission.WEBHOOKS_WRITE))] = ...,
    tenant_service: TenantServiceDep = ...,
    tenant_id: TenantID = ...,
):
    await tenant_service.delete_webhook(
        tenant_id=tenant_id,
        webhook_id=webhook_id,
        actor_id=current_user.get("user_id"),
    )
    return None


@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(
    webhook_id: str,
    current_user: Annotated[dict, Depends(require_permission(Permission.WEBHOOKS_WRITE))] = ...,
    tenant_service: TenantServiceDep = ...,
    tenant_id: TenantID = ...,
):
    result = await tenant_service.test_webhook(tenant_id, webhook_id)
    return result


@router.get("/webhooks/{webhook_id}/logs")
async def get_webhook_logs(
    webhook_id: str,
    current_user: Annotated[dict, Depends(require_permission(Permission.WEBHOOKS_READ))],
    tenant_service: TenantServiceDep = ...,
    tenant_id: TenantID = ...,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    logs, total = await tenant_service.get_webhook_logs(tenant_id, webhook_id, page, page_size)
    return {
        "data": [
            {
                "id": log.id,
                "event_type": log.event_type,
                "status": log.status.value,
                "response_code": log.response_code,
                "attempt_count": log.attempt_count,
                "created_at": log.created_at.isoformat() if log.created_at else None,
                "completed_at": log.completed_at.isoformat() if log.completed_at else None,
            }
            for log in logs
        ],
        "meta": {"page": page, "page_size": page_size, "total": total},
    }
