"""Notifications (Phase 7).

In-app notifications with a provider-abstracted email interface. The email
provider is selected by ``EMAIL_PROVIDER`` (``null`` = no-op, ``smtp`` = SMTP
via stdlib). Failed email deliveries are retried with backoff
(``attempts`` / ``next_attempt_at``) until delivered or max attempts reached.
"""
from __future__ import annotations

import smtplib
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models import Notification

logger = get_logger("veriunlearn.notifications")


class EmailProvider(ABC):
    """Interface any email backend must implement."""

    @abstractmethod
    def send(self, *, to: str, subject: str, body: str) -> bool: ...


class NullEmailProvider(EmailProvider):
    """No-op provider (default): records intent, never sends."""

    def send(self, *, to: str, subject: str, body: str) -> bool:
        logger.info("email skipped (null provider) to=%s subject=%s", to, subject)
        return True


class SmtpEmailProvider(EmailProvider):
    """SMTP provider via stdlib (TLS when the port expects it)."""

    def __init__(self) -> None:
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.username = settings.SMTP_USERNAME
        self.password = settings.SMTP_PASSWORD
        self.from_addr = settings.SMTP_FROM

    def send(self, *, to: str, subject: str, body: str) -> bool:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = self.from_addr
        msg["To"] = to
        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                server.starttls()
                if self.username:
                    server.login(self.username, self.password)
                server.sendmail(self.from_addr, [to], msg.as_string())
            return True
        except Exception:
            logger.exception("email send failed to=%s", to)
            return False


def get_email_provider() -> EmailProvider:
    if settings.EMAIL_PROVIDER == "smtp" and settings.SMTP_HOST:
        return SmtpEmailProvider()
    return NullEmailProvider()


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_user(self, user_id: str, *, limit: int = 100) -> list[Notification]:
        result = await self.session.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def unread_count(self, user_id: str) -> int:
        from sqlalchemy import func

        return int(
            await self.session.scalar(
                select(func.count())
                .select_from(Notification)
                .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            )
            or 0
        )

    async def pending_deliveries(self, *, limit: int = 50) -> list[Notification]:
        now = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC for naive column
        result = await self.session.execute(
            select(Notification)
            .where(
                Notification.channel == "email",
                Notification.delivered.is_(False),
                Notification.attempts < settings.NOTIFICATION_MAX_ATTEMPTS,
                (Notification.next_attempt_at.is_(None)) | (Notification.next_attempt_at <= now),
            )
            .order_by(Notification.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = NotificationRepository(session)
        self.email = get_email_provider()

    async def notify(
        self,
        *,
        user_id: str,
        event_type: str,
        title: str,
        body: str = "",
        payload: dict[str, Any] | None = None,
        channels: list[str] | None = None,
    ) -> Notification:
        channels = channels or ["in_app"]
        record: Notification | None = None
        for channel in channels:
            record = Notification(
                user_id=user_id,
                event_type=event_type,
                channel=channel,
                title=title,
                body=body,
                payload=payload or {},
            )
            self.session.add(record)
            if channel == "email":
                record.attempts = 0
                record.next_attempt_at = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC
        await self.session.flush()
        await self._flush_emails()
        return record  # type: ignore[return-value]

    async def list(self, user_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        return [
            {
                "id": n.id,
                "event_type": n.event_type,
                "channel": n.channel,
                "title": n.title,
                "body": n.body,
                "payload": n.payload,
                "is_read": n.is_read,
                "delivered": n.delivered,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in await self.repo.list_for_user(user_id, limit=limit)
        ]

    async def unread_count(self, user_id: str) -> int:
        return await self.repo.unread_count(user_id)

    async def mark_read(self, notification_id: str, user_id: str) -> Notification:
        notification = await self.session.get(Notification, notification_id)
        if notification is None or notification.user_id != user_id:
            from app.core.exceptions import NotFoundError

            raise NotFoundError(f"Notification {notification_id} not found")
        notification.is_read = True
        await self.session.flush()
        return notification

    async def mark_all_read(self, user_id: str) -> int:
        notifications = await self.repo.list_for_user(user_id, limit=500)
        count = 0
        for n in notifications:
            if not n.is_read:
                n.is_read = True
                count += 1
        if count:
            await self.session.flush()
        return count

    async def _flush_emails(self) -> None:
        """Attempt immediate delivery of pending email notifications (with retry)."""
        for notification in await self.repo.pending_deliveries():
            ok = self.email.send(
                to=notification.user_id,  # user_id is the email for platform users
                subject=notification.title,
                body=notification.body,
            )
            notification.attempts += 1
            if ok:
                notification.delivered = True
                notification.next_attempt_at = None
            else:
                notification.next_attempt_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
                    minutes=2 ** min(notification.attempts, 5)
                )
        await self.session.flush()
