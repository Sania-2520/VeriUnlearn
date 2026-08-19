"""Role-based access control (Phase 7).

Defines the five platform roles and the permission matrix. Permissions are
scoped ``resource:action`` strings that are enforced at the API layer via
:func:`require_permission` and mirrored on the frontend for page guards.

Roles (highest → lowest privilege):

- ``admin``      : full platform control (users, roles, keys, monitoring, config)
- ``researcher`` : read everything + run benchmarks/attacks/experiments
- ``auditor``    : read-only verification, audit trail, compliance, monitoring
- ``operator``   : day-to-day operations (datasets, training, unlearning)
- ``viewer``     : read-only dashboards and reports

The matrix is the single source of truth; it is also persisted to the
``roles`` / ``permissions`` tables for admin visibility and audit.
"""
from __future__ import annotations

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "admin": [
        "users:manage", "roles:manage", "api_keys:manage", "api_keys:read",
        "datasets:manage", "datasets:read", "models:manage", "models:read",
        "unlearning:execute", "privacy:read", "privacy:scan",
        "verification:read", "verification:run", "certificates:read", "audit:read",
        "compliance:read", "compliance:report", "monitoring:read", "analytics:read",
        "research:run", "notifications:read",
    ],
    "researcher": [
        "datasets:read", "models:read", "privacy:read", "privacy:scan",
        "verification:read", "certificates:read", "audit:read", "compliance:read",
        "analytics:read", "research:run", "notifications:read",
    ],
    "auditor": [
        "datasets:read", "models:read", "privacy:read", "verification:read",
        "certificates:read", "audit:read", "compliance:read", "monitoring:read",
        "analytics:read", "notifications:read",
    ],
    "operator": [
        "datasets:manage", "models:manage", "unlearning:execute",
        "privacy:read", "privacy:scan", "verification:run", "verification:read",
        "certificates:read", "compliance:read", "notifications:read",
    ],
    "viewer": [
        "datasets:read", "models:read", "privacy:read", "verification:read",
        "certificates:read", "compliance:read", "analytics:read", "notifications:read",
    ],
}

VALID_ROLES = sorted(ROLE_PERMISSIONS.keys())

# Legacy roles map onto the matrix so existing accounts keep working.
_LEGACY_MAP = {"operator": "operator", "auditor": "auditor", "admin": "admin"}


def role_permissions(role: str) -> list[str]:
    """Resolve a role's permission set (legacy roles included)."""
    role = _LEGACY_MAP.get(role, role)
    return ROLE_PERMISSIONS.get(role, [])


def has_permission(role: str, permission: str) -> bool:
    return permission in role_permissions(role)


def permission_definitions() -> list[dict[str, str]]:
    """Flattened (role → permissions) for admin visibility."""
    return [
        {"role": role, "permissions": perms}
        for role, perms in ROLE_PERMISSIONS.items()
    ]
