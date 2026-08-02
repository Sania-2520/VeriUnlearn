
import httpx

from app.core.logging import get_logger
from app.workers.celery_app import celery_app
from app.workers.session import worker_session
from app.workers.utils import _run_async

logger = get_logger(__name__)


@celery_app.task(bind=True, name="notification.send_email")
def send_email(self, to: str, subject: str, body: str) -> dict:
    logger.info("Sending email to %s: %s", to, subject)
    from app.infrastructure.external.email_service import email_service

    try:
        _run_async(email_service.send_email(to, subject, body))
        return {"to": to, "subject": subject, "status": "sent"}
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to, str(e))
        return {"to": to, "subject": subject, "status": "failed", "error": str(e)}


@celery_app.task(bind=True, name="notification.dispatch_webhook")
def dispatch_webhook(self, webhook_id: str, event_type: str, payload: dict) -> dict:
    logger.info("Dispatching webhook %s for event %s", webhook_id, event_type)
    import hashlib
    import hmac
    import json
    from datetime import datetime, timezone

    from app.infrastructure.database.models import WebhookEventLogModel, WebhookModel

    with worker_session() as session:
        webhook = session.query(WebhookModel).filter_by(id=webhook_id).first()
        if not webhook or not webhook.is_active:
            return {"webhook_id": webhook_id, "status": "skipped", "reason": "inactive"}

        if webhook.secret:
            body = json.dumps(payload, sort_keys=True).encode()
            signature = hmac.new(
                webhook.secret.encode(), body, hashlib.sha256
            ).hexdigest()
        else:
            signature = ""

        try:
            resp = httpx.post(
                webhook.url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Event": event_type,
                    "X-Webhook-Signature": signature,
                    "X-Webhook-ID": webhook_id,
                },
                timeout=webhook.timeout_ms / 1000.0 if webhook.timeout_ms else 5.0,
            )

            log = WebhookEventLogModel(
                webhook_id=webhook_id,
                event_type=event_type,
                payload=payload,
                status="delivered" if resp.is_success else "failed",
                response_code=resp.status_code,
                response_body=resp.text[:5000],
                attempt_count=webhook.last_success_at or 1,
                max_attempts=webhook.retry_count or 3,
            )
            session.add(log)

            if resp.is_success:
                webhook.last_success_at = datetime.now(timezone.utc)
                webhook.consecutive_failures = 0
                webhook.status = "active"
            else:
                webhook.last_failure_at = datetime.now(timezone.utc)
                webhook.consecutive_failures = (webhook.consecutive_failures or 0) + 1
                if webhook.consecutive_failures >= 5:
                    webhook.status = "failing"

            return {
                "webhook_id": webhook_id,
                "status": "delivered" if resp.is_success else "failed",
                "status_code": resp.status_code,
            }

        except Exception as e:
            log = WebhookEventLogModel(
                webhook_id=webhook_id,
                event_type=event_type,
                payload=payload,
                status="failed",
                response_code=None,
                response_body=str(e)[:5000],
                attempt_count=1,
                max_attempts=webhook.retry_count or 3,
            )
            session.add(log)

            webhook.last_failure_at = datetime.now(timezone.utc)
            webhook.consecutive_failures = (webhook.consecutive_failures or 0) + 1

            logger.error("Webhook dispatch failed for %s: %s", webhook_id, str(e))
            return {"webhook_id": webhook_id, "status": "failed", "error": str(e)}


@celery_app.task(bind=True, name="notification.retry_failed_webhooks")
def retry_failed_webhooks(self) -> dict:
    logger.info("Checking for failed webhooks to retry")
    from app.infrastructure.database.models import WebhookModel

    retried = 0
    with worker_session() as session:
        failing = (
            session.query(WebhookModel)
            .filter(
                WebhookModel.is_active == True,
                WebhookModel.status.in_(["failing", "active"]),
                WebhookModel.consecutive_failures > 0,
                WebhookModel.consecutive_failures < 5,
            )
            .all()
        )

        for webhook in failing:
            remaining = webhook.retry_count or 3
            if remaining > 0:
                dispatch_webhook.delay(
                    webhook_id=webhook.id,
                    event_type="webhook.retry",
                    payload={"auto_retry": True, "webhook_id": webhook.id},
                )
                retried += 1

    return {"status": "completed", "webhooks_retried": retried}
