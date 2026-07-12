from __future__ import annotations

from enum import Enum
from functools import wraps

from fastapi import HTTPException, status

from app.models.user import User


class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"
    AUDITOR = "auditor"


class Permission(str, Enum):
    # User management
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"

    # Training
    TRAINING_READ = "training:read"
    TRAINING_WRITE = "training:write"
    TRAINING_DELETE = "training:delete"

    # Unlearning
    UNLEARNING_READ = "unlearning:read"
    UNLEARNING_WRITE = "unlearning:write"
    UNLEARNING_EXECUTE = "unlearning:execute"

    # Documents
    DOCUMENT_READ = "document:read"
    DOCUMENT_WRITE = "document:write"
    DOCUMENT_DELETE = "document:delete"

    # Admin
    ADMIN_READ = "admin:read"
    ADMIN_WRITE = "admin:write"
    SYSTEM_CONFIG = "system:config"
    AUDIT_LOG = "audit:log"


ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.ADMIN: {
        Permission.USER_READ,
        Permission.USER_WRITE,
        Permission.USER_DELETE,
        Permission.TRAINING_READ,
        Permission.TRAINING_WRITE,
        Permission.TRAINING_DELETE,
        Permission.UNLEARNING_READ,
        Permission.UNLEARNING_WRITE,
        Permission.UNLEARNING_EXECUTE,
        Permission.DOCUMENT_READ,
        Permission.DOCUMENT_WRITE,
        Permission.DOCUMENT_DELETE,
        Permission.ADMIN_READ,
        Permission.ADMIN_WRITE,
        Permission.SYSTEM_CONFIG,
        Permission.AUDIT_LOG,
    },
    Role.USER: {
        Permission.USER_READ,
        Permission.TRAINING_READ,
        Permission.TRAINING_WRITE,
        Permission.UNLEARNING_READ,
        Permission.UNLEARNING_WRITE,
        Permission.UNLEARNING_EXECUTE,
        Permission.DOCUMENT_READ,
        Permission.DOCUMENT_WRITE,
        Permission.DOCUMENT_DELETE,
    },
    Role.AUDITOR: {
        Permission.UNLEARNING_READ,
        Permission.AUDIT_LOG,
        Permission.TRAINING_READ,
        Permission.DOCUMENT_READ,
    },
}


def check_permission(user: User, permission: Permission) -> None:
    role = Role(user.role)
    if permission not in ROLE_PERMISSIONS.get(role, set()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required permission: {permission.value}",
        )


def require_permission(permission: Permission):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get("user")
            if user is None:
                for arg in args:
                    if isinstance(arg, User):
                        user = arg
                        break
            if user is None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
            check_permission(user, permission)
            return await func(*args, **kwargs)
        return wrapper
    return decorator
