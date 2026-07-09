import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailTemplate:
    VERIFY_EMAIL = "verify_email"
    RESET_PASSWORD = "reset_password"
    WELCOME = "welcome"
    DELETION_CONFIRMED = "deletion_confirmed"
    ACCOUNT_DELETED = "account_deleted"


class EmailService:
    def __init__(self) -> None:
        self._host = settings.smtp_host
        self._port = settings.smtp_port
        self._user = settings.smtp_user
        self._password = settings.smtp_password
        self._from = settings.smtp_from
        self._from_name = settings.smtp_from_name

    async def send_verification_email(
        self, to_email: str, token: str, full_name: str
    ) -> bool:
        subject = "Verify your email address"
        verify_url = f"{settings.domain}/api/v1/auth/verify-email?token={token}"
        body = self._render_template(
            "verify_email",
            name=full_name,
            verify_url=verify_url,
        )
        return await self._send(to_email, subject, body)

    async def send_password_reset_email(
        self, to_email: str, token: str, full_name: str
    ) -> bool:
        subject = "Reset your password"
        reset_url = f"{settings.domain}/reset-password?token={token}"
        body = self._render_template(
            "reset_password",
            name=full_name,
            reset_url=reset_url,
        )
        return await self._send(to_email, subject, body)

    async def send_welcome_email(self, to_email: str, full_name: str) -> bool:
        subject = f"Welcome to {settings.app_name}"
        body = self._render_template("welcome", name=full_name)
        return await self._send(to_email, subject, body)

    async def send_deletion_confirmation(
        self, to_email: str, full_name: str, proof_id: str
    ) -> bool:
        subject = "Your data deletion has been confirmed"
        body = self._render_template(
            "deletion_confirmed",
            name=full_name,
            proof_id=proof_id,
        )
        return await self._send(to_email, subject, body)

    async def _send(
        self, to_email: str, subject: str, body: str
    ) -> bool:
        if not self._host:
            logger.warning("SMTP not configured, skipping email to %s", to_email)
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{self._from_name} <{self._from}>"
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "html"))

            with smtplib.SMTP(self._host, self._port) as server:
                server.starttls()
                if self._user and self._password:
                    server.login(self._user, self._password)
                server.send_message(msg)

            logger.info("Email sent to %s: %s", to_email, subject)
            return True
        except Exception as e:
            logger.error("Failed to send email to %s: %s", to_email, str(e))
            return False

    @staticmethod
    def _render_template(template_name: str, **kwargs: str) -> str:
        name = kwargs.get("name", "User")
        if template_name == "verify_email":
            verify_url = kwargs.get("verify_url", "#")
            return f"""<!DOCTYPE html>
<html><body style="font-family:-apple-system,sans-serif;max-width:600px;margin:0 auto;padding:20px">
<div style="text-align:center;margin-bottom:30px">
<h1 style="color:#2563eb;font-size:24px">Verify Your Email</h1>
</div>
<p style="font-size:16px;line-height:1.5">Hi {name},</p>
<p style="font-size:16px;line-height:1.5">Please verify your email address by clicking the button below:</p>
<div style="text-align:center;margin:30px 0">
<a href="{verify_url}" style="background-color:#2563eb;color:white;padding:12px 32px;text-decoration:none;border-radius:6px;font-size:16px;display:inline-block">Verify Email</a>
</div>
<p style="color:#6b7280;font-size:14px">This link expires in 24 hours.</p>
</body></html>"""

        if template_name == "reset_password":
            reset_url = kwargs.get("reset_url", "#")
            return f"""<!DOCTYPE html>
<html><body style="font-family:-apple-system,sans-serif;max-width:600px;margin:0 auto;padding:20px">
<div style="text-align:center;margin-bottom:30px">
<h1 style="color:#2563eb;font-size:24px">Reset Your Password</h1>
</div>
<p style="font-size:16px;line-height:1.5">Hi {name},</p>
<p style="font-size:16px;line-height:1.5">Click below to reset your password:</p>
<div style="text-align:center;margin:30px 0">
<a href="{reset_url}" style="background-color:#2563eb;color:white;padding:12px 32px;text-decoration:none;border-radius:6px;font-size:16px;display:inline-block">Reset Password</a>
</div>
<p style="color:#6b7280;font-size:14px">This link expires in 1 hour. If you didn't request this, ignore this email.</p>
</body></html>"""

        if template_name == "welcome":
            return f"""<!DOCTYPE html>
<html><body style="font-family:-apple-system,sans-serif;max-width:600px;margin:0 auto;padding:20px">
<div style="text-align:center;margin-bottom:30px">
<h1 style="color:#2563eb;font-size:24px">Welcome to VeriUnlearn</h1>
</div>
<p style="font-size:16px;line-height:1.5">Hi {name},</p>
<p style="font-size:16px;line-height:1.5">Your account is ready. You can now use the platform for verifiable machine unlearning.</p>
</body></html>"""

        return "<html><body>No template found</body></html>"


email_service = EmailService()
