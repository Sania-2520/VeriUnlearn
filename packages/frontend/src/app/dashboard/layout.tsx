"use client"

import { useEffect, useState, useRef, useCallback } from "react"
import { useRouter, usePathname } from "next/navigation"
import Link from "next/link"
import { useAuthStore } from "@/lib/store/auth-store"
import { clsx } from "clsx"
import { ThemeToggle } from "@/components/theme-toggle"
import { NavSidebar, getBreadcrumbsFromSections } from "@/components/nav-sidebar"
import { navigationConfig, filterNavSections } from "@/lib/config/navigation"
import { TooltipProvider } from "@/components/ui/tooltip"
import type { UserRole } from "@/lib/types/navigation"
import { CopilotProvider, useCopilot } from "@/hooks/use-copilot"
import { AiCopilot } from "@/components/ai-copilot"
import { OnboardingProvider, TourOverlay, WelcomeDialog } from "@/components/onboarding"
import {
  ChevronDown,
  ChevronRight,
  LogOut,
  PanelLeftClose,
  PanelLeft,
  User,
  Key,
  ShieldAlert,
  Sparkles,
  Database,
  Cpu,
  Menu,
  X,
  ChevronLeft,
} from "lucide-react"

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const { isAuthenticated, isLoading, user, loadUser, logout } = useAuthStore()

  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)
  const [profileMenuOpen, setProfileMenuOpen] = useState(false)
  const profileRef = useRef<HTMLDivElement>(null)

  const userRole: UserRole = (user?.role as UserRole) ?? "admin"

  const filteredSections = filterNavSections(navigationConfig, userRole)

  const breadcrumbs = getBreadcrumbsFromSections(navigationConfig, pathname, userRole)

  useEffect(() => {
    loadUser()
  }, [loadUser])

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/auth/login")
    }
  }, [isLoading, isAuthenticated, router])

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (profileRef.current && !profileRef.current.contains(event.target as Node)) {
        setProfileMenuOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  const closeMobileSidebar = useCallback(() => setMobileSidebarOpen(false), [])

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--bg-app)]">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-[var(--brand)] border-t-transparent" />
      </div>
    )
  }

  if (!isAuthenticated || !user) return null

  function CopilotToggleButton() {
    const { toggle } = useCopilot()
    return (
      <button
        onClick={toggle}
        data-tour="copilot"
        className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--brand-strong)]"
        title="AI Copilot (Ctrl+K)"
        aria-label="Open AI Copilot"
      >
        <svg
          className="h-[18px] w-[18px]"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M12 8V4H8" />
          <rect width="16" height="12" x="4" y="8" rx="2" />
          <path d="M2 14h2" />
          <path d="M20 14h2" />
          <path d="M15 13v2" />
          <path d="M9 13v2" />
        </svg>
      </button>
    )
  }

  const initials = user.full_name
    .split(" ")
    .map((n: string) => n[0])
    .join("")
    .substring(0, 2)
    .toUpperCase()

  return (
    <TooltipProvider delayDuration={200}>
      <OnboardingProvider>
      <CopilotProvider>
      <a
        href="#main-content"
        className="sr-only z-50 rounded-lg bg-[var(--brand)] px-4 py-2 text-sm font-medium text-[var(--text-on-brand)] focus:not-sr-only focus:absolute focus:left-4 focus:top-4"
      >
        Skip to content
      </a>

      <div className="flex min-h-screen overflow-hidden bg-[var(--bg-app)] font-sans text-[var(--text-primary)]">
        {/* Mobile overlay */}
        {mobileSidebarOpen && (
          <div
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm md:hidden"
            onClick={closeMobileSidebar}
          />
        )}

        {/* Sidebar */}
        <aside
          className={clsx(
            "z-50 flex flex-col border-r border-[var(--border-default)] bg-[var(--bg-surface)] transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]",
            "fixed inset-y-0 left-0 md:static",
            sidebarOpen ? "w-64" : "w-0 md:w-[60px]",
            mobileSidebarOpen
              ? "translate-x-0"
              : "-translate-x-full md:translate-x-0",
            !sidebarOpen && "md:border-r-0",
          )}
        >
          {/* Sidebar header */}
          <div
            className={clsx(
              "flex shrink-0 items-center border-b border-[var(--border-subtle)] transition-all duration-300",
              sidebarOpen ? "justify-between p-3.5" : "justify-center p-3",
            )}
          >
            {sidebarOpen ? (
              <>
                <Link
                  href="/dashboard"
                  onClick={closeMobileSidebar}
                  className="flex items-center gap-2 rounded-lg px-2.5 py-1.5 transition-colors hover:bg-[var(--bg-hover)]"
                >
                  <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--brand)] text-sm font-bold text-[var(--text-on-brand)]">
                    ⊗
                  </span>
                  <span className="text-[15px] font-semibold tracking-wide text-[var(--text-primary)]">
                    VeriUnlearn
                  </span>
                  <span className="ml-0.5 rounded bg-[var(--bg-subtle)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--text-tertiary)]">
                    v1.0
                  </span>
                </Link>
                <button
                  onClick={() => setSidebarOpen(false)}
                  className="rounded-lg p-2 text-[var(--text-tertiary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
                  title="Collapse sidebar"
                  aria-label="Collapse sidebar"
                >
                  <PanelLeftClose className="h-[18px] w-[18px]" />
                </button>
              </>
            ) : (
              <button
                onClick={() => setSidebarOpen(true)}
                className="rounded-lg p-2 text-[var(--text-tertiary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
                title="Expand sidebar"
                aria-label="Expand sidebar"
              >
                <PanelLeft className="h-[18px] w-[18px]" />
              </button>
            )}
          </div>

          {/* New Request quick action */}
          {sidebarOpen && (
            <div className="shrink-0 px-3.5 pt-3.5">
              <Link href="/dashboard/unlearning/new" onClick={closeMobileSidebar}>
                <button className="flex w-full items-center justify-start gap-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-2.5 text-[14px] font-medium text-[var(--text-primary)] transition-all hover:border-[var(--brand)] hover:bg-[var(--brand-soft)] hover:text-[var(--brand-strong)]">
                  <svg
                    className="h-4 w-4 text-[var(--brand)]"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <circle cx="12" cy="12" r="10" />
                    <path d="M12 8v8" />
                    <path d="M8 12h8" />
                  </svg>
                  New Deletion Request
                </button>
              </Link>
            </div>
          )}

          {/* Navigation */}
          <NavSidebar
            sections={navigationConfig}
            role={userRole}
            isCollapsed={!sidebarOpen}
            onToggleCollapse={() => setSidebarOpen(!sidebarOpen)}
            onMobileClose={closeMobileSidebar}
          />

          {/* Profile card at bottom */}
          <div
            ref={profileRef}
            className={clsx(
              "shrink-0 border-t border-[var(--border-subtle)] transition-all duration-300",
              sidebarOpen ? "p-3.5" : "p-2",
            )}
          >
            {profileMenuOpen && sidebarOpen && (
              <div className="absolute bottom-16 left-3.5 right-3.5 z-40 animate-scale-in rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface-elevated)] py-1.5 text-[13px] shadow-[var(--shadow-lg)]">
                <Link
                  href="/dashboard/profile"
                  onClick={() => { setProfileMenuOpen(false); closeMobileSidebar() }}
                  className="flex items-center gap-2.5 px-4 py-2.5 text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
                >
                  <User className="h-4 w-4 text-[var(--text-tertiary)]" />
                  My Profile
                </Link>
                <Link
                  href="/dashboard/api-keys"
                  onClick={() => { setProfileMenuOpen(false); closeMobileSidebar() }}
                  className="flex items-center gap-2.5 px-4 py-2.5 text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
                >
                  <Key className="h-4 w-4 text-[var(--text-tertiary)]" />
                  API Credentials
                </Link>
                <Link
                  href="/dashboard/sessions"
                  onClick={() => { setProfileMenuOpen(false); closeMobileSidebar() }}
                  className="flex items-center gap-2.5 px-4 py-2.5 text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
                >
                  <ShieldAlert className="h-4 w-4 text-[var(--text-tertiary)]" />
                  Active Sessions
                </Link>
                <div className="my-1 border-t border-[var(--border-subtle)]" />
                <button
                  onClick={async () => {
                    setProfileMenuOpen(false)
                    await logout()
                    router.push("/auth/login")
                  }}
                  className="flex w-full items-center gap-2.5 px-4 py-2.5 text-left text-[var(--danger)] transition-colors hover:bg-[var(--danger-soft)]"
                >
                  <LogOut className="h-4 w-4" />
                  Sign Out
                </button>
              </div>
            )}

            {sidebarOpen ? (
              <button
                onClick={() => setProfileMenuOpen(!profileMenuOpen)}
                aria-expanded={profileMenuOpen}
                className="flex w-full items-center justify-between gap-3 rounded-xl p-2.5 text-left transition-colors hover:bg-[var(--bg-hover)]"
              >
                <div className="flex items-center gap-3 overflow-hidden">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--brand)] text-[13px] font-semibold uppercase text-[var(--text-on-brand)]">
                    {initials}
                  </div>
                  <div className="overflow-hidden">
                    <p className="truncate text-[13px] font-medium text-[var(--text-primary)]">
                      {user.full_name}
                    </p>
                    <p className="truncate text-[11px] text-[var(--text-tertiary)]">
                      {userRole.replace("-", " ")}
                    </p>
                  </div>
                </div>
                <ChevronDown
                  className={clsx(
                    "h-4 w-4 shrink-0 text-[var(--text-tertiary)] transition-transform duration-200",
                    profileMenuOpen && "rotate-180",
                  )}
                />
              </button>
            ) : (
              <button
                onClick={() => setSidebarOpen(true)}
                className="flex w-full items-center justify-center rounded-xl p-2 text-[var(--text-tertiary)] transition-colors hover:bg-[var(--bg-hover)]"
                title="Expand sidebar"
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--brand)] text-[12px] font-semibold uppercase text-[var(--text-on-brand)]">
                  {initials}
                </div>
              </button>
            )}
          </div>
        </aside>

        {/* Main View Area */}
        <div className="relative flex min-w-0 flex-1 flex-col">
          {/* Sticky Header */}
          <header className="sticky top-0 z-30 flex h-[60px] shrink-0 items-center justify-between border-b border-[var(--border-subtle)] bg-[var(--bg-app)]/80 px-4 backdrop-blur-lg">
            <div className="flex items-center gap-3">
              {/* Mobile hamburger */}
              <button
                onClick={() => setMobileSidebarOpen(true)}
                className="rounded-lg p-2 text-[var(--text-tertiary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] md:hidden"
                title="Open menu"
                aria-label="Open navigation menu"
              >
                <Menu className="h-[18px] w-[18px]" />
              </button>

              {/* Desktop open trigger */}
              {!sidebarOpen && (
                <button
                  onClick={() => setSidebarOpen(true)}
                  className="hidden rounded-lg p-2 text-[var(--text-tertiary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] md:block"
                  title="Open sidebar"
                  aria-label="Open sidebar"
                >
                  <PanelLeft className="h-[18px] w-[18px]" />
                </button>
              )}

              {/* Breadcrumbs */}
              <nav aria-label="Breadcrumb" className="hidden sm:flex">
                <ol className="flex items-center gap-1.5 text-[13px]">
                  {breadcrumbs.map((crumb, index) => (
                    <li key={index} className="flex items-center gap-1.5">
                      {index > 0 && (
                        <ChevronRight className="h-3.5 w-3.5 text-[var(--text-tertiary)]" />
                      )}
                      {crumb.href && index < breadcrumbs.length - 1 ? (
                        <Link
                          href={crumb.href}
                          className="rounded-md px-1.5 py-0.5 text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
                        >
                          {crumb.label}
                        </Link>
                      ) : (
                        <span
                          className={clsx(
                            "rounded-md px-1.5 py-0.5",
                            index === breadcrumbs.length - 1
                              ? "font-medium text-[var(--text-primary)]"
                              : "text-[var(--text-secondary)]",
                          )}
                        >
                          {crumb.label}
                        </span>
                      )}
                    </li>
                  ))}
                </ol>
              </nav>

              {/* Mobile page title */}
              <span className="text-[14px] font-semibold text-[var(--text-primary)] sm:hidden">
                {breadcrumbs[breadcrumbs.length - 1]?.label ?? "Dashboard"}
              </span>
            </div>

            <div className="flex items-center gap-2">
              <CopilotToggleButton />

              {/* System indicators */}
              <div className="hidden items-center gap-1.5 rounded-full border border-[var(--border-default)] bg-[var(--bg-surface)] px-2.5 py-1 sm:flex">
                <Database className="h-3.5 w-3.5 text-[var(--brand)]" />
                <span className="text-[12px] font-medium text-[var(--text-secondary)]">SQLite</span>
              </div>
              <div className="hidden items-center gap-1.5 rounded-full border border-[var(--border-default)] bg-[var(--bg-surface)] px-2.5 py-1 sm:flex">
                <Cpu className="h-3.5 w-3.5 text-[var(--brand)]" />
                <span className="text-[12px] font-medium text-[var(--text-secondary)]">Memory Cache</span>
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
      <TourOverlay />
      <WelcomeDialog />
      <AiCopilot />
      </CopilotProvider>
      </OnboardingProvider>
    </TooltipProvider>
  )
}