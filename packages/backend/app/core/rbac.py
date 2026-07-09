from enum import Enum
from typing import Optional


class Permission(str, Enum):
    UNLEARNING_CREATE = "unlearning:create"
    UNLEARNING_READ = "unlearning:read"
    UNLEARNING_RETRY = "unlearning:retry"
    VERIFICATION_READ = "verification:read"
    VERIFICATION_VERIFY = "verification:verify"
    AUDIT_READ = "audit:read"
    COMPLIANCE_READ = "compliance:read"
    COMPLIANCE_CREATE = "compliance:create"
    USERS_READ = "users:read"
    USERS_WRITE = "users:write"
    ADMIN_READ = "admin:read"
    ADMIN_WRITE = "admin:write"
    API_KEYS_MANAGE = "api_keys:manage"
    CHAT = "chat"
    RAG = "rag"
    MEMORY = "memory"
    PROVIDERS_READ = "providers:read"
    PROVIDERS_WRITE = "providers:write"
    SECURITY_CREATE = "security:create"
    SECURITY_READ = "security:read"
    SETTINGS_READ = "settings:read"
    SETTINGS_WRITE = "settings:write"
    WEBHOOKS_READ = "webhooks:read"
    WEBHOOKS_WRITE = "webhooks:write"


ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    "admin": {
        Permission.UNLEARNING_CREATE,
        Permission.UNLEARNING_READ,
        Permission.UNLEARNING_RETRY,
        Permission.VERIFICATION_READ,
        Permission.VERIFICATION_VERIFY,
        Permission.AUDIT_READ,
        Permission.COMPLIANCE_READ,
        Permission.COMPLIANCE_CREATE,
        Permission.USERS_READ,
        Permission.USERS_WRITE,
        Permission.ADMIN_READ,
        Permission.ADMIN_WRITE,
        Permission.API_KEYS_MANAGE,
        Permission.CHAT,
        Permission.RAG,
        Permission.MEMORY,
        Permission.PROVIDERS_READ,
        Permission.PROVIDERS_WRITE,
        Permission.SECURITY_CREATE,
        Permission.SECURITY_READ,
        Permission.SETTINGS_READ,
        Permission.SETTINGS_WRITE,
        Permission.WEBHOOKS_READ,
        Permission.WEBHOOKS_WRITE,
    },
    "compliance_officer": {
        Permission.UNLEARNING_READ,
        Permission.VERIFICATION_READ,
        Permission.VERIFICATION_VERIFY,
        Permission.AUDIT_READ,
        Permission.COMPLIANCE_READ,
        Permission.COMPLIANCE_CREATE,
        Permission.USERS_READ,
        Permission.SECURITY_READ,
        Permission.SETTINGS_READ,
        Permission.SETTINGS_WRITE,
        Permission.WEBHOOKS_READ,
        Permission.WEBHOOKS_WRITE,
    },
    "unlearning_auditor": {
        Permission.UNLEARNING_CREATE,
        Permission.UNLEARNING_READ,
        Permission.UNLEARNING_RETRY,
        Permission.VERIFICATION_READ,
        Permission.VERIFICATION_VERIFY,
        Permission.AUDIT_READ,
        Permission.USERS_READ,
    },
    "member": {
        Permission.UNLEARNING_CREATE,
        Permission.UNLEARNING_READ,
        Permission.VERIFICATION_READ,
        Permission.AUDIT_READ,
        Permission.CHAT,
        Permission.RAG,
        Permission.MEMORY,
        Permission.USERS_READ,
        Permission.USERS_WRITE,
        Permission.PROVIDERS_READ,
        Permission.API_KEYS_MANAGE,
        Permission.SECURITY_CREATE,
        Permission.SECURITY_READ,
        Permission.SETTINGS_READ,
    },
    "viewer": {
        Permission.UNLEARNING_READ,
        Permission.VERIFICATION_READ,
        Permission.AUDIT_READ,
        Permission.CHAT,
        Permission.MEMORY,
    },
}


def get_role_permissions(role: str) -> set[Permission]:
    return ROLE_PERMISSIONS.get(role, set())


def check_permission(role: str, required: Permission) -> bool:
    return required in get_role_permissions(role)


def get_required_permission(
    resource: str,
    action: str,
    role: Optional[str] = None,
) -> Permission:
    return Permission(f"{resource}:{action}")
