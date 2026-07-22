"use client"

import { useEffect, useState, useRef } from "react"
import { useRouter, usePathname } from "next/navigation"
import Link from "next/link"
import { useAuthStore } from "@/lib/store/auth-store"
import { clsx } from "clsx"
import { ThemeToggle } from "@/components/theme-toggle"
import { TooltipProvider } from "@/components/ui/tooltip"
import {
  Plus,
  LogOut,
  ChevronDown,
  User,
  Settings,
  Key,
  ShieldAlert,
  Brain,
  PanelLeftClose,
  PanelLeft,
  Trash2,
  FileText,
  Webhook,
  Database,
  Cpu,
  FileSearch,
  Activity,
  BarChart3,
  FlaskConical,
} from "lucide-react"

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const { isAuthenticated, isLoading, user, loadUser, logout } = useAuthStore()

  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [profileMenuOpen, setProfileMenuOpen] = useState(false)
  const [engineMenuOpen, setEngineMenuOpen] = useState(false)
  const [selectedEngine, setSelectedEngine] = useState("Hybrid Engine (SISA + Influence)")

  const profileRef = useRef<HTMLDivElement>(null)
  const engineRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadUser()
  }, [loadUser])

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/auth/login")
    }
  }, [isLoading, isAuthenticated, router])

  // Close menus on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (profileRef.current && !profileRef.current.contains(event.target as Node)) {
        setProfileMenuOpen(false)
      }
      if (engineRef.current && !engineRef.current.contains(event.target as Node)) {
        setEngineMenuOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => {
      document.removeEventListener("mousedown", handleClickOutside)
    }
  }, [])

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--bg-app)]">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-[var(--brand)] border-t-transparent" />
      </div>
    )
  }

  if (!isAuthenticated || !user) return null

  const workspaceItems = [
    { href: "/dashboard", label: "Overview", icon: Brain },
    { href: "/dashboard/unlearning", label: "Unlearning", icon: Trash2 },
    { href: "/dashboard/rag", label: "RAG Documents", icon: FileSearch },
    { href: "/dashboard/models", label: "Model Registry", icon: Database },
    { href: "/dashboard/explainability", label: "Explainability", icon: BarChart3 },
    { href: "/dashboard/adapters", label: "Adapter Lifecycle", icon: Cpu },
    { href: "/dashboard/benchmarks", label: "Benchmarks", icon: FlaskConical },
    { href: "/dashboard/training", label: "Training", icon: Cpu },
    { href: "/dashboard/audit", label: "Audit Log", icon: FileText },
    { href: "/dashboard/webhooks", label: "Webhooks", icon: Webhook },
  ]

  const configItems = [
    { href: "/dashboard/monitoring", label: "Monitoring", icon: Activity },
    { href: "/dashboard/admin", label: "Admin Settings", icon: Settings },
    { href: "/dashboard/profile", label: "User Profile", icon: User },
    { href: "/dashboard/sessions", label: "Active Sessions", icon: ShieldAlert },
    { href: "/dashboard/api-keys", label: "API Credentials", icon: Key },
  ]

  const engines = [
    "Hybrid Engine (SISA + Influence)",
    "SISA (Sharded Retraining)",
    "Influence Function Approximation",
    "Certified Removal (DP)",
  ]

  return (
    <TooltipProvider delayDuration={200}>
      <a
        href="#main-content"
        className="sr-only z-50 rounded-lg bg-[var(--brand)] px-4 py-2 text-sm font-medium text-[var(--text-on-brand)] focus:not-sr-only focus:absolute focus:left-4 focus:top-4"
      >
        Skip to content
      </a>
      <div className="flex min-h-screen overflow-hidden bg-[var(--bg-app)] font-sans text-[var(--text-primary)]">
        {/* Sidebar */}
        <aside
          className={clsx(
            "z-30 flex w-64 shrink-0 flex-col border-r border-[var(--border-default)] bg-[var(--bg-surface)] transition-all duration-300",
            sidebarOpen ? "translate-x-0" : "absolute -translate-x-64 md:relative"
          )}
          style={{ height: "100vh" }}
        >
          {/* Sidebar Header */}
          <div className="flex items-center justify-between border-b border-[var(--border-subtle)] p-3.5">
            <Link href="/dashboard" className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 transition-colors hover:bg-[var(--bg-hover)]">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--brand)] text-sm font-bold text-[var(--text-on-brand)]">⊗</span>
              <span className="text-[15px] font-semibold tracking-wide text-[var(--text-primary)]">VeriUnlearn</span>
              <span className="ml-0.5 rounded bg-[var(--bg-subtle)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--text-tertiary)]">v1.0</span>
            </Link>
            <button
              onClick={() => setSidebarOpen(false)}
              className="rounded-lg p-2 text-[var(--text-tertiary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] cursor-pointer"
              title="Close sidebar"
              aria-label="Close sidebar"
            >
              <PanelLeftClose className="h-[18px] w-[18px]" />
            </button>
          </div>

          {/* New Deletion Request Button */}
          <div className="p-3.5">
            <Link href="/dashboard/unlearning/new">
              <button className="flex w-full items-center justify-start gap-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-2.5 text-[14px] font-medium text-[var(--text-primary)] transition-all hover:border-[var(--brand)] hover:bg-[var(--brand-soft)] hover:text-[var(--brand-strong)] cursor-pointer">
                <Plus className="h-4 w-4 text-[var(--brand)]" />
                New Deletion Request
              </button>
            </Link>
          </div>

          {/* Navigation List */}
          <div className="flex-1 space-y-6 overflow-y-auto px-3.5 py-2">
            {/* Workspace Category */}
            <div>
              <p className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">Workspace</p>
              <nav className="space-y-1">
                {workspaceItems.map((item) => {
                  const isActive = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href))
                  const Icon = item.icon
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      aria-current={isActive ? "page" : undefined}
                      className={clsx(
                        "flex items-center gap-3 rounded-lg px-3 py-2.5 text-[13px] font-medium transition-colors",
                        isActive
                          ? "border border-[var(--brand-border)] bg-[var(--brand-soft)] text-[var(--brand-strong)]"
                          : "text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
                      )}
                    >
                      <Icon className={clsx("h-4 w-4", isActive ? "text-[var(--brand)]" : "text-[var(--text-tertiary)]")} />
                      {item.label}
                    </Link>
                  )
                })}
              </nav>
            </div>

            {/* Configuration Category */}
            <div>
              <p className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">Configuration</p>
              <nav className="space-y-1">
                {configItems.map((item) => {
                  const isActive = pathname === item.href || (item.href !== "/dashboard/admin" && pathname.startsWith(item.href))
                  const Icon = item.icon
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      aria-current={isActive ? "page" : undefined}
                      className={clsx(
                        "flex items-center gap-3 rounded-lg px-3 py-2.5 text-[13px] font-medium transition-colors",
                        isActive
                          ? "border border-[var(--brand-border)] bg-[var(--brand-soft)] text-[var(--brand-strong)]"
                          : "text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
                      )}
                    >
                      <Icon className={clsx("h-4 w-4", isActive ? "text-[var(--brand)]" : "text-[var(--text-tertiary)]")} />
                      {item.label}
                    </Link>
                  )
                })}
              </nav>
            </div>
          </div>

          {/* Profile Card at the Bottom */}
          <div className="relative border-t border-[var(--border-subtle)] p-3.5" ref={profileRef}>
            {profileMenuOpen && (
              <div className="absolute bottom-16 left-3.5 right-3.5 z-40 animate-scale-in rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface-elevated)] py-1.5 text-[13px] shadow-[var(--shadow-lg)]">
                <Link
                  href="/dashboard/profile"
                  onClick={() => setProfileMenuOpen(false)}
                  className="flex items-center gap-2.5 px-4 py-2.5 text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
                >
                  <User className="h-4 w-4 text-[var(--text-tertiary)]" />
                  My Profile
                </Link>
                <Link
                  href="/dashboard/api-keys"
                  onClick={() => setProfileMenuOpen(false)}
                  className="flex items-center gap-2.5 px-4 py-2.5 text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
                >
                  <Key className="h-4 w-4 text-[var(--text-tertiary)]" />
                  API Credentials
                </Link>
                <Link
                  href="/dashboard/sessions"
                  onClick={() => setProfileMenuOpen(false)}
                  className="flex items-center gap-2.5 px-4 py-2.5 text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
                >
                  <ShieldAlert className="h-4 w-4 text-[var(--text-tertiary)]" />
                  Active Sessions
                </Link>
                <div className="my-1 border-t border-[var(--border-subtle)]"></div>
                <button
                  onClick={async () => {
                    setProfileMenuOpen(false)
                    await logout()
                    router.push("/auth/login")
                  }}
                  className="flex w-full items-center gap-2.5 px-4 py-2.5 text-left text-[var(--danger)] transition-colors hover:bg-[var(--danger-soft)] cursor-pointer"
                >
                  <LogOut className="h-4 w-4" />
                  Sign Out
                </button>
              </div>
            )}

            <button
              onClick={() => setProfileMenuOpen(!profileMenuOpen)}
              aria-expanded={profileMenuOpen}
              className="flex w-full items-center justify-between gap-3 rounded-xl p-2.5 text-left transition-colors hover:bg-[var(--bg-hover)] cursor-pointer"
            >
              <div className="flex items-center gap-3 overflow-hidden">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--brand)] text-[13px] font-semibold uppercase text-[var(--text-on-brand)]">
                  {user.full_name.substring(0, 2)}
                </div>
                <div className="overflow-hidden">
                  <p className="truncate text-[13px] font-medium text-[var(--text-primary)]">{user.full_name}</p>
                  <p className="truncate text-[11px] text-[var(--text-tertiary)]">{user.email}</p>
                </div>
              </div>
              <ChevronDown className="h-4 w-4 shrink-0 text-[var(--text-tertiary)]" />
            </button>
          </div>
        </aside>

        {/* Main View Area */}
        <div className="relative flex min-w-0 flex-1 flex-col h-screen">
          {/* Sticky Header */}
          <header className="sticky top-0 z-20 flex h-[60px] shrink-0 items-center justify-between border-b border-[var(--border-subtle)] bg-[var(--bg-app)]/80 px-4 backdrop-blur">
            <div className="flex items-center gap-3">
              {!sidebarOpen && (
                <button
                  onClick={() => setSidebarOpen(true)}
                  className="rounded-lg p-2 text-[var(--text-tertiary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] cursor-pointer"
                  title="Open sidebar"
                  aria-label="Open sidebar"
                >
                  <PanelLeft className="h-[18px] w-[18px]" />
                </button>
              )}
            
            {/* Model / Engine Dropdown Selector */}
            <div className="relative" ref={engineRef}>
              <button
                onClick={() => setEngineMenuOpen(!engineMenuOpen)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl hover:bg-[var(--bg-hover)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-[14px] font-semibold transition-colors cursor-pointer"
              >
                <span>{selectedEngine}</span>
                <ChevronDown className="h-4 w-4 text-[var(--text-tertiary)]" />
              </button>
              
              {engineMenuOpen && (
                <div className="absolute left-0 top-11 z-40 w-64 animate-scale-in rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface-elevated)] py-1.5 text-[13px] shadow-[var(--shadow-lg)]">
                  <div className="px-3.5 py-2 text-[11px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">Unlearning Policy</div>
                  {engines.map((eng) => (
                    <button
                      key={eng}
                      onClick={() => {
                        setSelectedEngine(eng)
                        setEngineMenuOpen(false)
                      }}
                      className={clsx(
                        "flex w-full items-center justify-between px-4 py-2.5 text-left transition-colors hover:bg-[var(--bg-hover)] cursor-pointer",
                        selectedEngine === eng ? "font-medium text-[var(--brand-strong)]" : "text-[var(--text-secondary)]"
                      )}
                    >
                      {eng}
                      {selectedEngine === eng && <span className="h-2 w-2 rounded-full bg-[var(--brand)]"></span>}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Quick System Indicators + Theme */}
          <div className="flex items-center gap-3 text-xs">
            <div className="hidden items-center gap-1.5 rounded-full border border-[var(--border-default)] bg-[var(--bg-surface)] px-2.5 py-1 sm:flex">
              <Database className="h-3.5 w-3.5 text-[var(--brand)]" />
              <span className="font-medium text-[var(--text-secondary)]">SQLite</span>
            </div>
            <div className="hidden items-center gap-1.5 rounded-full border border-[var(--border-default)] bg-[var(--bg-surface)] px-2.5 py-1 sm:flex">
              <Cpu className="h-3.5 w-3.5 text-[var(--brand)]" />
              <span className="font-medium text-[var(--text-secondary)]">Memory Cache</span>
            </div>
            <ThemeToggle />
          </div>
        </header>

        {/* Content Area */}
        <main id="main-content" className="relative flex flex-1 flex-col overflow-auto bg-[var(--bg-app)]">
          {children}
        </main>
      </div>
      </div>
      </TooltipProvider>
  )
}
