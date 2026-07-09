import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class UserRole(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"
    UNLEARNING_AUDITOR = "unlearning_auditor"
    COMPLIANCE_OFFICER = "compliance_officer"


class TenantPlan(str, Enum):
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


@dataclass
class Tenant:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    slug: str = ""
    domain: Optional[str] = None
    plan: TenantPlan = TenantPlan.STARTER
    settings: dict = field(default_factory=dict)
    features: dict = field(default_factory=dict)
    max_users: int = 10
    max_storage_gb: int = 10
    max_api_requests_per_min: int = 1000
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class User:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    email: str = ""
    password_hash: str = ""
    full_name: str = ""
    avatar_url: Optional[str] = None
    role: UserRole = UserRole.MEMBER
    is_email_verified: bool = False
    is_active: bool = True
    is_locked: bool = False
    locked_until: Optional[datetime] = None
    failed_login_attempts: int = 0
    last_login_at: Optional[datetime] = None
    last_login_ip: Optional[str] = None
    mfa_enabled: bool = False
    mfa_secret: Optional[str] = None
    preferences: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Session:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    refresh_token_hash: str = ""
    access_token_jti: str = ""
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    device_name: Optional[str] = None
    is_revoked: bool = False
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    revoked_at: Optional[datetime] = None


@dataclass
class ApiKey:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    name: str = ""
    key_hash: str = ""
    key_prefix: str = ""
    scopes: list[str] = field(default_factory=list)
    expires_at: Optional[datetime] = None
    is_active: bool = True
    created_by: Optional[str] = None
    last_used_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class OAuthAccount:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    provider: str = ""
    provider_user_id: str = ""
    provider_email: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
