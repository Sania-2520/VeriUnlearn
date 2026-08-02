import type { NavSection } from "@/lib/types/navigation"

export const navigationConfig: NavSection[] = [
  {
    title: "Workspace",
    roles: ["admin", "researcher", "ml-engineer", "compliance-officer", "executive"],
    items: [
      { label: "Overview", href: "/dashboard", icon: "LayoutDashboard", tourId: "dashboard", roles: ["admin", "researcher", "ml-engineer", "compliance-officer", "executive"] },
      { label: "Activity", href: "/dashboard/activity", icon: "Activity", roles: ["admin", "researcher", "ml-engineer", "compliance-officer", "executive"] },
    ],
  },
  {
    title: "Machine Unlearning",
    tourId: "unlearning",
    roles: ["admin", "researcher", "ml-engineer", "compliance-officer"],
    items: [
      { label: "All Requests", href: "/dashboard/unlearning", icon: "ListTodo", roles: ["admin", "researcher", "ml-engineer", "compliance-officer"] },
      { label: "New Request", href: "/dashboard/unlearning/new", icon: "PlusCircle", roles: ["admin", "researcher", "ml-engineer", "compliance-officer"] },
      { label: "Queue", href: "/dashboard/unlearning/queue", icon: "ListOrdered", roles: ["admin", "researcher", "ml-engineer", "compliance-officer"] },
    ],
  },
  {
    title: "Experiments",
    tourId: "experiments",
    roles: ["researcher", "ml-engineer"],
    items: [
      { label: "Benchmarks", href: "/dashboard/benchmarks", icon: "BarChart3", roles: ["researcher", "ml-engineer"] },
      { label: "Training", href: "/dashboard/training", icon: "FlaskConical", roles: ["researcher", "ml-engineer"] },
      { label: "Models", href: "/dashboard/models", icon: "Brain", roles: ["researcher", "ml-engineer"] },
      { label: "Explainability", href: "/dashboard/explainability", icon: "SearchCode", roles: ["researcher", "ml-engineer"] },
    ],
  },
  {
    title: "Data",
    roles: ["researcher", "ml-engineer"],
    items: [
      { label: "Datasets", href: "/dashboard/datasets", icon: "Database", roles: ["researcher", "ml-engineer"] },
      { label: "RAG Documents", href: "/dashboard/rag", icon: "FileText", roles: ["researcher", "ml-engineer"] },
      { label: "Adapters", href: "/dashboard/adapters", icon: "Puzzle", roles: ["researcher", "ml-engineer"] },
    ],
  },
  {
    title: "Verification",
    roles: ["admin", "compliance-officer"],
    items: [
      { label: "Certificates", href: "/dashboard/certificates", icon: "ShieldCheck", tourId: "certificates", roles: ["admin", "compliance-officer"] },
      { label: "Audit Log", href: "/dashboard/audit", icon: "ScrollText", roles: ["admin", "compliance-officer"] },
      { label: "Proofs", href: "/dashboard/proofs", icon: "Fingerprint", roles: ["admin", "compliance-officer"] },
    ],
  },
  {
    title: "Monitoring",
    roles: ["admin", "ml-engineer", "executive"],
    items: [
      { label: "Operations", href: "/dashboard/operations", icon: "Gauge", tourId: "operations", roles: ["admin", "ml-engineer", "executive"] },
      { label: "System Health", href: "/dashboard/monitoring", icon: "HeartPulse", roles: ["admin", "ml-engineer", "executive"] },
      { label: "Webhooks", href: "/dashboard/webhooks", icon: "Webhook", roles: ["admin", "ml-engineer", "executive"] },
    ],
  },
  {
    title: "Configuration",
    roles: ["admin"],
    items: [
      { label: "API Keys", href: "/dashboard/api-keys", icon: "Key", roles: ["admin"] },
      { label: "Adapters", href: "/dashboard/adapters", icon: "Cable", roles: ["admin"] },
      { label: "Sessions", href: "/dashboard/sessions", icon: "Monitor", roles: ["admin"] },
      { label: "Webhooks Settings", href: "/dashboard/webhooks", icon: "Settings", roles: ["admin"] },
    ],
  },
  {
    title: "Profile",
    roles: ["admin", "researcher", "ml-engineer", "compliance-officer", "executive"],
    items: [
      { label: "Profile", href: "/dashboard/profile", icon: "User", roles: ["admin", "researcher", "ml-engineer", "compliance-officer", "executive"] },
      { label: "API Keys", href: "/dashboard/api-keys", icon: "Key", roles: ["admin", "researcher", "ml-engineer", "compliance-officer", "executive"] },
    ],
  },
]

export function filterNavSections(
  sections: NavSection[],
  role: string,
): NavSection[] {
  return sections
    .map((section) => ({
      ...section,
      items: section.items.filter((item) => item.roles.includes(role as any)),
    }))
    .filter((section) => section.items.length > 0 && section.roles.includes(role as any))
}

export function findActiveItem(
  sections: NavSection[],
  pathname: string,
): { section: NavSection; item: typeof sections[number]["items"][number] } | null {
  for (const section of sections) {
    for (const item of section.items) {
      if (pathname === item.href) return { section, item }
      if (item.children) {
        for (const child of item.children) {
          if (pathname === child.href) return { section, item: child }
        }
      }
    }
  }
  return null
}

export function generateBreadcrumbs(
  sections: NavSection[],
  pathname: string,
): { label: string; href: string }[] {
  const crumbs: { label: string; href: string }[] = [{ label: "Dashboard", href: "/dashboard" }]
  const active = findActiveItem(sections, pathname)
  if (active) {
    crumbs.push({ label: active.section.title, href: "" })
    crumbs.push({ label: active.item.label, href: pathname })
  }
  return crumbs
}