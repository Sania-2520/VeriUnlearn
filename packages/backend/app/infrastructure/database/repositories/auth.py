from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.auth.entities import (
    ApiKey as ApiKeyEntity,
)
from app.domain.auth.entities import (
    Session as SessionEntity,
)
from app.domain.auth.entities import (
    Tenant as TenantEntity,
)
from app.domain.auth.entities import (
    TenantPlan,
    UserRole,
)
from app.domain.auth.entities import (
    User as UserEntity,
)
from app.domain.auth.interfaces import (
    ApiKeyRepository,
    SessionRepository,
    TenantRepository,
    UserRepository,
)
from app.infrastructure.database.models import (
    SessionModel,
    TenantApiKeyModel,
    TenantModel,
    UserModel,
)


class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user: UserEntity) -> UserEntity:
        model = UserModel(
            id=UUID(user.id) if isinstance(user.id, str) else user.id,
            tenant_id=UUID(user.tenant_id) if isinstance(user.tenant_id, str) else user.tenant_id,
            email=user.email,
            password_hash=user.password_hash,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            role=user.role.value,
            is_email_verified=user.is_email_verified,
            is_active=user.is_active,
            preferences=user.preferences,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def get_by_id(self, user_id: str) -> Optional[UserEntity]:
        if not user_id:
            return None
        try:
            uid = UUID(user_id)
        except (ValueError, TypeError):
            return None
        result = await self._session.execute(
            select(UserModel).where(UserModel.id == uid)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_email(self, email: str) -> Optional[UserEntity]:
        result = await self._session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def update(self, user: UserEntity) -> UserEntity:
        uid = UUID(user.id) if isinstance(user.id, str) else user.id
        await self._session.execute(
            update(UserModel)
            .where(UserModel.id == uid)
            .values(
                email=user.email,
                password_hash=user.password_hash,
                full_name=user.full_name,
                avatar_url=user.avatar_url,
                role=user.role.value,
                is_email_verified=user.is_email_verified,
                is_active=user.is_active,
                is_locked=user.is_locked,
                locked_until=user.locked_until,
                failed_login_attempts=user.failed_login_attempts,
                last_login_at=user.last_login_at,
                last_login_ip=user.last_login_ip,
                mfa_enabled=user.mfa_enabled,
                mfa_secret=user.mfa_secret,
                preferences=user.preferences,
            )
        )
        return user

    async def soft_delete(self, user_id: str) -> None:
        uid = UUID(user_id) if isinstance(user_id, str) else user_id
        await self._session.execute(
            update(UserModel)
            .where(UserModel.id == uid)
            .values(is_active=False)
        )

    @staticmethod
    def _to_entity(model: UserModel) -> UserEntity:
        return UserEntity(
            id=str(model.id),
            tenant_id=str(model.tenant_id),
            email=model.email,
            password_hash=model.password_hash,
            full_name=model.full_name,
            avatar_url=model.avatar_url,
            role=UserRole(model.role),
            is_email_verified=model.is_email_verified,
            is_active=model.is_active,
            is_locked=model.is_locked,
            locked_until=model.locked_until,
            failed_login_attempts=model.failed_login_attempts,
            last_login_at=model.last_login_at,
            last_login_ip=str(model.last_login_ip) if model.last_login_ip else None,
            mfa_enabled=model.mfa_enabled,
            mfa_secret=model.mfa_secret,
            preferences=model.preferences or {},
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SQLAlchemySessionRepository(SessionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, session_entity: SessionEntity) -> SessionEntity:
        model = SessionModel(
            id=UUID(session_entity.id) if isinstance(session_entity.id, str) else session_entity.id,
            user_id=UUID(session_entity.user_id) if isinstance(session_entity.user_id, str) else session_entity.user_id,
            refresh_token_hash=session_entity.refresh_token_hash,
            access_token_jti=session_entity.access_token_jti,
            user_agent=session_entity.user_agent,
            ip_address=session_entity.ip_address,
            device_name=session_entity.device_name,
            is_revoked=session_entity.is_revoked,
            expires_at=session_entity.expires_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def get_by_refresh_token(self, token_hash: str) -> Optional[SessionEntity]:
        result = await self._session.execute(
            select(SessionModel).where(
                SessionModel.refresh_token_hash == token_hash,
                SessionModel.is_revoked == False,  # noqa: E712
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def revoke(self, session_id: str) -> None:
        sid = UUID(session_id) if isinstance(session_id, str) else session_id
        await self._session.execute(
            update(SessionModel)
            .where(SessionModel.id == sid)
            .values(
                is_revoked=True,
                revoked_at=datetime.now(timezone.utc),
            )
        )

    async def revoke_all_for_user(self, user_id: str) -> None:
        uid = UUID(user_id) if isinstance(user_id, str) else user_id
        await self._session.execute(
            update(SessionModel)
            .where(
                SessionModel.user_id == uid,
                SessionModel.is_revoked == False,  # noqa: E712
            )
            .values(
                is_revoked=True,
                revoked_at=datetime.now(timezone.utc),
            )
        )

    async def list_active_by_user(self, user_id: str) -> list[SessionEntity]:
        uid = UUID(user_id) if isinstance(user_id, str) else user_id
        result = await self._session.execute(
            select(SessionModel)
            .where(
                SessionModel.user_id == uid,
                SessionModel.is_revoked == False,  # noqa: E712
            )
            .order_by(SessionModel.created_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    @staticmethod
    def _to_entity(model: SessionModel) -> SessionEntity:
        return SessionEntity(
            id=str(model.id),
            user_id=str(model.user_id),
            refresh_token_hash=model.refresh_token_hash,
            access_token_jti=model.access_token_jti,
            user_agent=model.user_agent,
            ip_address=str(model.ip_address) if model.ip_address else None,
            device_name=model.device_name,
            is_revoked=model.is_revoked,
            expires_at=model.expires_at,
            created_at=model.created_at,
            revoked_at=model.revoked_at,
        )


class SQLAlchemyTenantRepository(TenantRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, tenant: TenantEntity) -> TenantEntity:
        model = TenantModel(
            id=UUID(tenant.id) if isinstance(tenant.id, str) else tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            domain=tenant.domain,
            plan=tenant.plan.value,
            settings=tenant.settings,
            features=tenant.features,
            max_users=tenant.max_users,
            max_storage_gb=tenant.max_storage_gb,
            max_api_requests_per_min=tenant.max_api_requests_per_min,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def get_by_slug(self, slug: str) -> Optional[TenantEntity]:
        result = await self._session.execute(
            select(TenantModel).where(TenantModel.slug == slug)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_id(self, tenant_id: str) -> Optional[TenantEntity]:
        try:
            tid = UUID(tenant_id)
        except ValueError:
            return None
        result = await self._session.execute(
            select(TenantModel).where(TenantModel.id == tid)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def update(self, tenant: TenantEntity) -> TenantEntity:
        tid = UUID(tenant.id) if isinstance(tenant.id, str) else tenant.id
        await self._session.execute(
            update(TenantModel)
            .where(TenantModel.id == tid)
            .values(
                name=tenant.name,
                slug=tenant.slug,
                domain=tenant.domain,
                plan=tenant.plan.value if isinstance(tenant.plan, TenantPlan) else tenant.plan,
                settings=tenant.settings,
                features=tenant.features,
                max_users=tenant.max_users,
                max_storage_gb=tenant.max_storage_gb,
                max_api_requests_per_min=tenant.max_api_requests_per_min,
                is_active=tenant.is_active,
            )
        )
        return tenant

    @staticmethod
    def _to_entity(model: TenantModel) -> TenantEntity:
        return TenantEntity(
            id=str(model.id),
            name=model.name,
            slug=model.slug,
            domain=model.domain,
            plan=TenantPlan(model.plan),
            settings=model.settings or {},
            features=model.features or {},
            max_users=model.max_users,
            max_storage_gb=model.max_storage_gb,
            max_api_requests_per_min=model.max_api_requests_per_min,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SQLAlchemyApiKeyRepository(ApiKeyRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, api_key: ApiKeyEntity) -> ApiKeyEntity:
        model = TenantApiKeyModel(
            id=UUID(api_key.id) if isinstance(api_key.id, str) else api_key.id,
            tenant_id=UUID(api_key.tenant_id) if isinstance(api_key.tenant_id, str) else api_key.tenant_id,
            name=api_key.name,
            key_hash=api_key.key_hash,
            key_prefix=api_key.key_prefix,
            scopes=api_key.scopes,
            expires_at=api_key.expires_at,
            is_active=api_key.is_active,
            created_by=UUID(api_key.created_by) if api_key.created_by else None,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def get_by_key_hash(self, key_hash: str) -> Optional[ApiKeyEntity]:
        result = await self._session.execute(
            select(TenantApiKeyModel).where(
                TenantApiKeyModel.key_hash == key_hash,
                TenantApiKeyModel.is_active == True,  # noqa: E712
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_prefix(self, key_prefix: str) -> Optional[ApiKeyEntity]:
        result = await self._session.execute(
            select(TenantApiKeyModel).where(
                TenantApiKeyModel.key_prefix == key_prefix,
                TenantApiKeyModel.is_active == True,  # noqa: E712
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_tenant(self, tenant_id: str) -> list[ApiKeyEntity]:
        tid = UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
        result = await self._session.execute(
            select(TenantApiKeyModel)
            .where(TenantApiKeyModel.tenant_id == tid)
            .order_by(TenantApiKeyModel.created_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def revoke(self, api_key_id: str) -> None:
        aid = UUID(api_key_id) if isinstance(api_key_id, str) else api_key_id
        await self._session.execute(
            update(TenantApiKeyModel)
            .where(TenantApiKeyModel.id == aid)
            .values(is_active=False)
        )

    async def update_last_used(self, api_key_id: str) -> None:
        aid = UUID(api_key_id) if isinstance(api_key_id, str) else api_key_id
        await self._session.execute(
            update(TenantApiKeyModel)
            .where(TenantApiKeyModel.id == aid)
            .values(last_used_at=datetime.now(timezone.utc))
        )

    @staticmethod
    def _to_entity(model: TenantApiKeyModel) -> ApiKeyEntity:
        return ApiKeyEntity(
            id=str(model.id),
            tenant_id=str(model.tenant_id),
            name=model.name,
            key_hash=model.key_hash,
            key_prefix=model.key_prefix,
            scopes=model.scopes or [],
            expires_at=model.expires_at,
            is_active=model.is_active,
            created_by=str(model.created_by) if model.created_by else None,
            last_used_at=model.last_used_at,
            created_at=model.created_at,
        )
