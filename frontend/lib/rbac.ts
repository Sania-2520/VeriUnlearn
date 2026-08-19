/** Client-side RBAC mirror of backend/app/core/rbac.py.
 *
 * Each route rule lists the roles allowed to view it. Backend permission
 * checks remain the source of truth; these guards only hide UI.
 */

export type Role = "admin" | "researcher" | "auditor" | "operator" | "viewer";

const ROUTE_ROLES: Record<string, Role[]> = {
  "/assistant": ["admin", "researcher", "auditor", "operator", "viewer"],
  "/dashboard": ["admin", "researcher", "auditor", "operator", "viewer"],
  "/privacy": ["admin", "researcher", "auditor", "operator", "viewer"],
  "/unlearning": ["admin", "operator"],
  "/datasets": ["admin", "researcher", "auditor", "operator", "viewer"],
  "/verification": ["admin", "researcher", "auditor", "operator"],
  "/certificates": ["admin", "researcher", "auditor", "operator", "viewer"],
  "/audit": ["admin", "researcher", "auditor"],
  "/compliance": ["admin", "researcher", "auditor", "operator", "viewer"],
  "/attacks": ["admin", "researcher", "operator"],
  "/benchmark": ["admin", "researcher", "operator"],
  "/research": ["admin", "researcher"],
  "/admin": ["admin"],
  "/monitoring": ["admin", "auditor"],
  "/developer": ["admin", "researcher", "auditor", "operator"],
  "/notifications": ["admin", "researcher", "auditor", "operator", "viewer"],
  "/settings": ["admin", "researcher", "auditor", "operator", "viewer"],
};

const ALL_ROLES: Role[] = ["admin", "researcher", "auditor", "operator", "viewer"];

/** True if `role` may view the given path (prefix match on /research/* etc.). */
export function canView(role: string | undefined, pathname: string): boolean {
  if (!role) return false;
  // Exact match wins; otherwise fall back to the longest matching prefix.
  const direct = ROUTE_ROLES[pathname];
  if (direct) return direct.includes(role as Role);
  const prefixes = Object.keys(ROUTE_ROLES)
    .filter((p) => p !== "/dashboard" && pathname.startsWith(p + "/"))
    .sort((a, b) => b.length - a.length);
  for (const prefix of prefixes) {
    if (ROUTE_ROLES[prefix].includes(role as Role)) return true;
  }
  // Nested admin/developer/monitoring pages follow their root rule.
  if (pathname.startsWith("/admin/")) return canView(role, "/admin");
  if (pathname.startsWith("/developer")) return canView(role, "/developer");
  if (pathname.startsWith("/monitoring")) return canView(role, "/monitoring");
  return false;
}

export function isRole(role: string | undefined, ...roles: Role[]): boolean {
  return !!role && roles.includes(role as Role);
}

export function roleLabel(role: string | undefined): string {
  if (!role) return "—";
  return role.charAt(0).toUpperCase() + role.slice(1);
}

export function allRoles(): Role[] {
  return ALL_ROLES;
}
