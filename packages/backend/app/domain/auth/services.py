from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import pyotp


def ensure_aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


from app.core.cache import cache
from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
)
from app.core.logging import get_logger
from app.core.security import (
    generate_secure_token,
    hash_password,
    token_manager,
    verify_password,
)
from app.domain.audit.entities import ActorType, EventStatus, EventType
from app.domain.audit.services import AuditService
from app.domain.auth.entities import (
    Session,
    Tenant,
    User,
    UserRole,
)
from app.domain.auth.interfaces import (
    SessionRepository,
    TenantRepository,
    UserRepository,
)
from app.infrastructure.external.email_service import email_service

logger = get_logger(__name__)


class MFARequiredError(AuthenticationError):
    def __init__(self, challenge_token: str) -> None:
        self.challenge_token = challenge_token
        super().__init__(
            message="MFA verification required",
            details={"challenge_token": challenge_token},
        )


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        session_repo: SessionRepository,
        tenant_repo: TenantRepository,
        audit_service: AuditService,
    ) -> None:
        self._user_repo = user_repo
        self._session_repo = session_repo
        self._tenant_repo = tenant_repo
        self._audit = audit_service

    async def register(
        self,
        email: str,
        password: str,
        full_name: str,
        tenant_slug: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> tuple[User, str, str]:
        existing = await self._user_repo.get_by_email(email)
        if existing:
            raise ConflictError("Email already registered")

        if not tenant_slug:
            tenant_slug = email.split("@")[0] + "-tenant"

        tenant = await self._tenant_repo.get_by_slug(tenant_slug)
        if not tenant:
            tenant = Tenant(slug=tenant_slug, name=f"{full_name}'s Organization")
            tenant = await self._tenant_repo.create(tenant)

        user = User(
            tenant_id=tenant.id,
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
        )
        user = await self._user_repo.create(user)

        access_token, refresh_token_raw, session = await self._create_session(
            user, ip_address, user_agent
        )

        verify_token = generate_secure_token(48)
        await cache.set(
            f"verify:email:{verify_token}",
            {"user_id": user.id, "email": user.email},
            ttl=timedelta(hours=24),
        )
        await email_service.send_verification_email(
            user.email, verify_token, user.full_name
        )

        await self._audit.record(
            tenant_id=user.tenant_id,
            event_type=EventType.USER_CREATED,
            actor_id=user.id,
            actor_type=ActorType.USER,
            action="auth.register",
            status=EventStatus.SUCCESS,
            metadata={"email": user.email},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        logger.info("User registered: %s (tenant: %s)", user.email, tenant.slug)
        return user, access_token, refresh_token_raw

    async def login(
        self,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> tuple[User, str, str]:
        user = await self._user_repo.get_by_email(email)
        if not user:
            raise AuthenticationError("Invalid email or password")

        if user.is_locked:
            locked_until = ensure_aware(user.locked_until)
            if locked_until and locked_until > datetime.now(timezone.utc):
                raise AuthenticationError("Account is temporarily locked")

        if not verify_password(password, user.password_hash):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.is_locked = True
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            await self._user_repo.update(user)
            raise AuthenticationError("Invalid email or password")

        user.failed_login_attempts = 0
        user.is_locked = False
        user.locked_until = None
        user.last_login_at = datetime.now(timezone.utc)
        user.last_login_ip = ip_address
        await self._user_repo.update(user)

        if user.mfa_enabled:
            challenge_token = generate_secure_token(32)
            await cache.set(
                f"mfa:challenge:{challenge_token}",
                {
                    "user_id": user.id,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
                },
                ttl=timedelta(minutes=5),
            )
            raise MFARequiredError(challenge_token)

        access_token, refresh_token_raw, session = await self._create_session(
            user, ip_address, user_agent
        )

        await self._audit.record(
            tenant_id=user.tenant_id,
            event_type=EventType.USER_LOGIN,
            actor_id=user.id,
            actor_type=ActorType.USER,
            action="auth.login",
            status=EventStatus.SUCCESS,
            metadata={"email": user.email},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        logger.info("User logged in: %s", user.email)
        return user, access_token, refresh_token_raw

    async def verify_mfa_challenge(
        self, challenge_token: str, totp_code: str
    ) -> tuple[str, str]:
        data = await cache.get(f"mfa:challenge:{challenge_token}")
        if not data:
            raise AuthenticationError("Invalid or expired MFA challenge")

        attempts_key = f"mfa:attempts:{challenge_token}"
        attempts_raw = await cache.get(attempts_key)
        attempts = 0
        if isinstance(attempts_raw, (int, str)):
            attempts = int(attempts_raw)
        if attempts >= 5:
            await cache.delete(f"mfa:challenge:{challenge_token}")
            raise AuthenticationError("Too many MFA attempts — challenge invalidated")
        await cache.set(attempts_key, attempts + 1, ttl=timedelta(minutes=5))

        user = await self._user_repo.get_by_id(data["user_id"])
        if not user or not user.is_active:
            raise AuthenticationError("User account is inactive")

        if not user.mfa_enabled or not user.mfa_secret:
            raise AuthenticationError("MFA is not enabled for this account")

        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(totp_code, valid_window=1):
            raise AuthenticationError("Invalid MFA code")

        await cache.delete(f"mfa:challenge:{challenge_token}")

        access_token, refresh_token_raw, session = await self._create_session(
            user,
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            extra_claims={"mfa_verified": True},
        )

        await self._audit.record(
            tenant_id=user.tenant_id,
            event_type=EventType.USER_LOGIN,
            actor_id=user.id,
            actor_type=ActorType.USER,
            action="auth.mfa.challenge_verified",
            status=EventStatus.SUCCESS,
            metadata={"email": user.email},
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
        )
        logger.info("MFA challenge verified: %s", user.email)
        return access_token, refresh_token_raw

    async def oauth_login(
        self,
        provider: str,
        provider_user_id: str,
        email: str,
        full_name: str,
        avatar_url: Optional[str] = None,
        access_token: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> tuple[User, str, str, bool]:
        user = await self._user_repo.get_by_email(email)

        if not user:
            tenant = Tenant(
                slug=f"{email.split('@')[0]}-{provider}",
                name=f"{full_name}'s Organization",
            )
            tenant = await self._tenant_repo.create(tenant)

            user = User(
                tenant_id=tenant.id,
                email=email,
                password_hash=hash_password(generate_secure_token(32)),
                full_name=full_name,
                avatar_url=avatar_url,
                is_email_verified=True,
            )
            user = await self._user_repo.create(user)
            is_new = True
        else:
            is_new = False
            if avatar_url:
                user.avatar_url = avatar_url
            await self._user_repo.update(user)
            if user.mfa_enabled:
                challenge_token = generate_secure_token(32)
                await cache.set(
                    f"mfa:challenge:{challenge_token}",
                    {
                        "user_id": user.id,
                        "ip_address": ip_address,
                        "user_agent": user_agent,
                        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
                    },
                    ttl=timedelta(minutes=5),
                )
                raise MFARequiredError(challenge_token)

        access_token_jwt, refresh_token_raw, session = await self._create_session(
            user, ip_address, user_agent
        )

        if is_new:
            await email_service.send_welcome_email(user.email, user.full_name)

        logger.info(
            "OAuth login: %s via %s (new=%s)", user.email, provider, is_new
        )
        return user, access_token_jwt, refresh_token_raw, is_new

    async def refresh_token(
        self, refresh_token: str
    ) -> tuple[str, str]:
        token_hash = token_manager.hash_token(refresh_token)
        session = await self._session_repo.get_by_refresh_token(token_hash)
        if not session or session.is_revoked:
            raise AuthenticationError("Invalid or revoked refresh token")

        expires_at = ensure_aware(session.expires_at)
        if expires_at is None or expires_at < datetime.now(timezone.utc):
            await self._session_repo.revoke(session.id)
            raise AuthenticationError("Refresh token expired")
        await self._session_repo.revoke(session.id)

        user = await self._user_repo.get_by_id(session.user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User account is inactive")

        new_access_token = token_manager.create_access_token(
            subject=user.id,
            extra_claims={
                "tenant_id": user.tenant_id,
                "role": user.role.value,
                "email": user.email,
            },
        )
        new_refresh_raw, new_refresh_hash = token_manager.generate_token_hash()
        new_session = Session(
            user_id=user.id,
            refresh_token_hash=new_refresh_hash,
            access_token_jti=token_manager.decode_token(new_access_token).get(
                "jti", ""
            ),
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.jwt_refresh_token_expire_days),
        )
        await self._session_repo.create(new_session)

        return new_access_token, new_refresh_raw

    async def logout(self, user_id: str, session_id: Optional[str] = None, jti: Optional[str] = None, tenant_id: Optional[str] = None) -> None:
        if jti:
            await self.blacklist_jti(jti)
        if session_id:
            await self._session_repo.revoke(session_id)
        else:
            await self._session_repo.revoke_all_for_user(user_id)
        await self._audit.record(
            tenant_id=tenant_id or "",
            event_type=EventType.USER_LOGOUT,
            actor_id=user_id,
            actor_type=ActorType.USER,
            action="auth.logout",
            status=EventStatus.SUCCESS,
            metadata={"session_id": session_id, "batch": session_id is None},
        )
        logger.info("User logged out: %s", user_id)

    async def verify_email(self, token: str) -> bool:
        data = await cache.get(f"verify:email:{token}")
        if not data:
            raise AuthenticationError("Invalid or expired verification token")

        user = await self._user_repo.get_by_id(data["user_id"])
        if not user:
            raise NotFoundError("User not found")

        user.is_email_verified = True
        await self._user_repo.update(user)
        await cache.delete(f"verify:email:{token}")

        await self._audit.record(
            tenant_id=user.tenant_id,
            event_type=EventType.USER_CREATED,
            actor_id=user.id,
            actor_type=ActorType.USER,
            action="auth.email.verified",
            status=EventStatus.SUCCESS,
            metadata={"email": user.email},
        )
        logger.info("Email verified: %s", user.email)
        return True

    async def forgot_password(self, email: str) -> bool:
        user = await self._user_repo.get_by_email(email)
        if not user:
            return True

        reset_token = generate_secure_token(48)
        await cache.set(
            f"reset:password:{reset_token}",
            {"user_id": user.id, "email": user.email},
            ttl=timedelta(hours=1),
        )
        await email_service.send_password_reset_email(
            user.email, reset_token, user.full_name
        )

        await self._audit.record(
            tenant_id=user.tenant_id,
            event_type=EventType.SETTINGS_CHANGED,
            actor_id=user.id,
            actor_type=ActorType.USER,
            action="auth.password.reset_requested",
            status=EventStatus.SUCCESS,
            metadata={"email": user.email},
        )
        logger.info("Password reset requested: %s", email)
        return True

    async def reset_password(self, token: str, new_password: str) -> bool:
        data = await cache.get(f"reset:password:{token}")
        if not data:
            raise AuthenticationError("Invalid or expired reset token")

        user = await self._user_repo.get_by_id(data["user_id"])
        if not user:
            raise NotFoundError("User not found")

        user.password_hash = hash_password(new_password)
        await self._user_repo.update(user)
        await cache.delete(f"reset:password:{token}")
        await self._session_repo.revoke_all_for_user(user.id)

        await self._audit.record(
            tenant_id=user.tenant_id,
            event_type=EventType.SETTINGS_CHANGED,
            actor_id=user.id,
            actor_type=ActorType.USER,
            action="auth.password.reset_completed",
            status=EventStatus.SUCCESS,
            metadata={"email": user.email},
        )
        logger.info("Password reset completed: %s", user.email)
        return True

    async def change_password(
        self, user_id: str, current_password: str, new_password: str
    ) -> bool:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        if not verify_password(current_password, user.password_hash):
            raise AuthenticationError("Current password is incorrect")

        user.password_hash = hash_password(new_password)
        await self._user_repo.update(user)

        await self._session_repo.revoke_all_for_user(user_id)

        await self._audit.record(
            tenant_id=user.tenant_id,
            event_type=EventType.SETTINGS_CHANGED,
            actor_id=user.id,
            actor_type=ActorType.USER,
            action="auth.password.changed",
            status=EventStatus.SUCCESS,
            metadata={"email": user.email},
        )
        logger.info("Password changed: %s", user.email)
        return True

    async def get_sessions(self, user_id: str) -> list[Session]:
        return await self._session_repo.list_active_by_user(user_id)

    async def revoke_session(self, user_id: str, session_id: str) -> None:
        await self._session_repo.revoke(session_id)

    async def revoke_all_sessions(self, user_id: str) -> None:
        await self._session_repo.revoke_all_for_user(user_id)

    async def get_profile(self, user_id: str) -> User:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        return user

    async def update_profile(
        self,
        user_id: str,
        full_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        preferences: Optional[dict[str, Any]] = None,
    ) -> User:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        if full_name is not None:
            user.full_name = full_name
        if avatar_url is not None:
            user.avatar_url = avatar_url
        if preferences is not None:
            user.preferences = {**user.preferences, **preferences}

        await self._user_repo.update(user)
        logger.info("Profile updated: %s", user.email)
        return user

    async def check_role(
        self, user_id: str, required_role: UserRole
    ) -> bool:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            return False
        role_hierarchy = {
            UserRole.ADMIN: 4,
            UserRole.COMPLIANCE_OFFICER: 3,
            UserRole.UNLEARNING_AUDITOR: 2,
            UserRole.MEMBER: 1,
            UserRole.VIEWER: 0,
        }
        return role_hierarchy.get(user.role, 0) >= role_hierarchy.get(
            required_role, 0
        )

    async def generate_totp_secret(self, user_id: str, password: str) -> dict[str, str]:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        if not verify_password(password, user.password_hash):
            raise AuthenticationError("Password is incorrect")

        secret = pyotp.random_base32()
        issuer = settings.app_name or "VeriUnlearn"
        provisioning_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user.email, issuer_name=issuer
        )

        return {
            "secret": secret,
            "provisioning_uri": provisioning_uri,
        }

    async def enable_totp(self, user_id: str, secret: str, totp_code: str) -> bool:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        totp = pyotp.TOTP(secret)
        if not totp.verify(totp_code, valid_window=1):
            raise AuthenticationError("Invalid TOTP code")

        user.mfa_secret = secret
        user.mfa_enabled = True
        await self._user_repo.update(user)

        await self._audit.record(
            tenant_id=user.tenant_id,
            event_type=EventType.SETTINGS_CHANGED,
            actor_id=user.id,
            actor_type=ActorType.USER,
            action="auth.mfa.enabled",
            status=EventStatus.SUCCESS,
            metadata={"email": user.email},
        )
        logger.info("TOTP enabled: %s", user.email)
        return True

    async def disable_totp(self, user_id: str, totp_code: str) -> bool:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        if not user.mfa_secret:
            raise AuthenticationError("MFA is not enabled")

        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(totp_code, valid_window=1):
            raise AuthenticationError("Invalid TOTP code")

        user.mfa_secret = None
        user.mfa_enabled = False
        await self._user_repo.update(user)

        await self._audit.record(
            tenant_id=user.tenant_id,
            event_type=EventType.SETTINGS_CHANGED,
            actor_id=user.id,
            actor_type=ActorType.USER,
            action="auth.mfa.disabled",
            status=EventStatus.SUCCESS,
            metadata={"email": user.email},
        )
        logger.info("TOTP disabled: %s", user.email)
        return True

    async def blacklist_jti(self, jti: str) -> None:
        await cache.set(f"jti:blacklist:{jti}", True, ttl=timedelta(hours=24))

    async def is_jti_blacklisted(self, jti: str) -> bool:
        return await cache.exists(f"jti:blacklist:{jti}")

    async def _create_session(
        self,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        extra_claims: Optional[dict[str, Any]] = None,
    ) -> tuple[str, str, Session]:
        claims = {
            "tenant_id": user.tenant_id,
            "role": user.role.value,
            "email": user.email,
        }
        if extra_claims:
            claims.update(extra_claims)
        access_token = token_manager.create_access_token(
            subject=user.id,
            extra_claims=claims,
        )
        refresh_token_raw, refresh_token_hash = token_manager.generate_token_hash()

        session = Session(
            user_id=user.id,
            refresh_token_hash=refresh_token_hash,
            access_token_jti=token_manager.decode_token(access_token).get("jti", ""),
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=7),
        )
        await self._session_repo.create(session)

        return access_token, refresh_token_raw, session
