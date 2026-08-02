"use client"

import { useCallback, useMemo, useState } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { clsx } from "clsx"
import * as Collapsible from "@radix-ui/react-collapsible"
import {
  Activity,
  BarChart3,
  Brain,
  Cable,
  Database,
  FileText,
  Fingerprint,
  FlaskConical,
  Gauge,
  HeartPulse,
  Key,
  LayoutDashboard,
  ListOrdered,
  ListTodo,
  Monitor,
  type LucideIcon,
  PlusCircle,
  Puzzle,
  ScrollText,
  SearchCode,
  Settings,
  ShieldCheck,
  User,
  Webhook,
} from "lucide-react"
import type { NavSection, NavItem } from "@/lib/types/navigation"
import { Badge } from "@/components/ui/badge"

const iconMap: Record<string, LucideIcon> = {
  Activity,
  BarChart3,
  Brain,
  Cable,
  Database,
  FileText,
  Fingerprint,
  FlaskConical,
  Gauge,
  HeartPulse,
  Key,
  LayoutDashboard,
  ListOrdered,
  ListTodo,
  Monitor,
  PlusCircle,
  Puzzle,
  ScrollText,
  SearchCode,
  Settings,
  ShieldCheck,
  User,
  Webhook,
}

export interface NavSidebarProps {
  sections: NavSection[]
  role: string
  isCollapsed: boolean
  onToggleCollapse: () => void
  onMobileClose?: () => void
}

function NavItemLink({
  item,
  depth = 0,
  isCollapsed,
  onNavigate,
}: {
  item: NavItem
  depth?: number
  isCollapsed: boolean
  onNavigate?: () => void
}) {
  const pathname = usePathname()
  const Icon = iconMap[item.icon]

  const isActive =
    pathname === item.href ||
    (item.href !== "/dashboard" && pathname.startsWith(item.href) && pathname.length > item.href.length)

  if (isCollapsed && depth === 0) {
    return (
      <Link
        href={item.href}
        onClick={onNavigate}
        aria-current={isActive ? "page" : undefined}
        data-tour={item.tourId}
        className={clsx(
          "relative flex items-center justify-center rounded-lg p-2.5 transition-colors",
          isActive
            ? "bg-[var(--brand-soft)] text-[var(--brand-strong)]"
            : "text-[var(--text-tertiary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]",
        )}
        title={item.label}
      >
        {Icon && <Icon className="h-[18px] w-[18px]" />}
        {item.badge && (
          <span className="absolute -right-0.5 -top-0.5 flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[var(--brand)] opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-[var(--brand)]" />
          </span>
        )}
      </Link>
    )
  }

  return (
      <Link
      href={item.href}
      onClick={onNavigate}
      aria-current={isActive ? "page" : undefined}
      data-tour={item.tourId}
      className={clsx(
        "group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-[13px] font-medium transition-all duration-150",
        isActive
          ? "border border-[var(--brand-border)] bg-[var(--brand-soft)] text-[var(--brand-strong)]"
          : "text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]",
      )}
      style={{ paddingLeft: depth > 0 ? `${12 + depth * 16}px` : undefined }}
    >
      {Icon && (
        <Icon
          className={clsx(
            "h-[18px] w-[18px] shrink-0 transition-colors",
            isActive ? "text-[var(--brand)]" : "text-[var(--text-tertiary)] group-hover:text-[var(--text-secondary)]",
          )}
        />
      )}
      <span className="truncate">{item.label}</span>
      {item.badge && (
        <Badge tone={item.badge.tone as any} className="ml-auto shrink-0">
          {item.badge.label}
        </Badge>
      )}
    </Link>
  )
}

function NavSectionGroup({
  section,
  isCollapsed,
  defaultOpen = true,
  onNavigate,
}: {
  section: NavSection
  isCollapsed: boolean
  defaultOpen?: boolean
  onNavigate?: () => void
}) {
  const [open, setOpen] = useState(defaultOpen)

  if (isCollapsed) {
    return (
      <div className="space-y-1">
        {section.items.map((item) => (
          <NavItemLink key={item.href} item={item} isCollapsed={true} onNavigate={onNavigate} />
        ))}
      </div>
    )
  }

  return (
    <Collapsible.Root open={open} onOpenChange={setOpen}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        data-tour={section.tourId}
        className="flex w-full items-center justify-between rounded-lg px-3 py-1.5 text-left transition-colors hover:bg-[var(--bg-hover)]"
      >
        <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
          {section.title}
        </span>
        <svg
          className={clsx(
            "h-3.5 w-3.5 text-[var(--text-tertiary)] transition-transform duration-200",
            open && "rotate-90",
          )}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </button>
      <Collapsible.Content className="overflow-hidden data-[state=closed]:animate-collapse-up data-[state=open]:animate-collapse-down">
        <div className="mt-1 space-y-0.5 pb-2">
          {section.items.map((item) => (
            <NavItemLink key={item.href} item={item} isCollapsed={false} onNavigate={onNavigate} />
          ))}
        </div>
      </Collapsible.Content>
    </Collapsible.Root>
  )
}

export function NavSidebar({ sections, role, isCollapsed, onToggleCollapse, onMobileClose }: NavSidebarProps) {
  const filteredSections = useMemo(
    () =>
      sections
        .map((s) => ({
          ...s,
          items: s.items.filter((item) => item.roles.includes(role as any)),
        }))
        .filter((s) => s.items.length > 0),
    [sections, role],
  )

  return (
    <nav className="flex flex-1 flex-col gap-1 overflow-y-auto px-3 py-2 scrollbar-thin">
      {filteredSections.map((section) => (
        <NavSectionGroup
          key={section.title}
          section={section}
          isCollapsed={isCollapsed}
          defaultOpen={true}
          onNavigate={onMobileClose}
        />
      ))}
    </nav>
  )
}

export function getBreadcrumbsFromSections(
  sections: NavSection[],
  pathname: string,
  role: string,
): { label: string; href: string }[] {
  const crumbs: { label: string; href: string }[] = [{ label: "Dashboard", href: "/dashboard" }]

  for (const section of sections) {
    if (!section.roles.includes(role as any)) continue
    for (const item of section.items) {
      if (!item.roles.includes(role as any)) continue
      if (pathname === item.href) {
        crumbs.push({ label: section.title, href: "" })
        crumbs.push({ label: item.label, href: pathname })
        return crumbs
      }
      if (item.children) {
        for (const child of item.children) {
          if (pathname === child.href) {
            crumbs.push({ label: item.label, href: item.href })
            crumbs.push({ label: child.label, href: pathname })
            return crumbs
          }
        }
      }
    }
  }

  const deeperParts = pathname.replace("/dashboard/", "").split("/")
  if (deeperParts.length > 1 && crumbs.length === 1) {
    for (const part of deeperParts) {
      crumbs.push({
        label: part.charAt(0).toUpperCase() + part.slice(1).replace(/-/g, " "),
        href: `/dashboard/${deeperParts.slice(0, deeperParts.indexOf(part) + 1).join("/")}`,
      })
    }
  }

  return crumbs
}