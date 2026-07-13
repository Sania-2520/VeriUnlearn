from abc import ABC, abstractmethod
from typing import Optional

from app.domain.auth.entities import User, Session, Tenant, OAuthAccount, ApiKey


class UserRepository(ABC):
    @abstractmethod
    async def create(self, user: User) -> User:
        ...

    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[User]:
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        ...

    @abstractmethod
    async def update(self, user: User) -> User:
        ...

    @abstractmethod
    async def soft_delete(self, user_id: str) -> None:
        ...


class SessionRepository(ABC):
    @abstractmethod
    async def create(self, session: Session) -> Session:
        ...

    @abstractmethod
    async def get_by_refresh_token(self, token_hash: str) -> Optional[Session]:
        ...

    @abstractmethod
    async def revoke(self, session_id: str) -> None:
        ...

    @abstractmethod
    async def revoke_all_for_user(self, user_id: str) -> None:
        ...

    @abstractmethod
    async def list_active_by_user(self, user_id: str) -> list[Session]:
        ...


class TenantRepository(ABC):
    @abstractmethod
    async def create(self, tenant: Tenant) -> Tenant:
        ...

    @abstractmethod
    async def get_by_slug(self, slug: str) -> Optional[Tenant]:
        ...

    @abstractmethod
    async def get_by_id(self, tenant_id: str) -> Optional[Tenant]:
        ...

    @abstractmethod
    async def update(self, tenant: Tenant) -> Tenant:
        ...


class ApiKeyRepository(ABC):
    @abstractmethod
    async def create(self, api_key: ApiKey) -> ApiKey:
        ...

    @abstractmethod
    async def get_by_key_hash(self, key_hash: str) -> Optional[ApiKey]:
        ...

    @abstractmethod
    async def get_by_prefix(self, key_prefix: str) -> Optional[ApiKey]:
        ...

    @abstractmethod
    async def list_by_tenant(self, tenant_id: str) -> list[ApiKey]:
        ...

    @abstractmethod
    async def revoke(self, api_key_id: str) -> None:
        ...

    @abstractmethod
    async def update_last_used(self, api_key_id: str) -> None:
        ...
