"use client"

import { useEffect, useState, useRef } from "react"
import { useRouter, usePathname } from "next/navigation"
import Link from "next/link"
import { useAuthStore } from "@/lib/store/auth-store"
import { clsx } from "clsx"
import {
  Menu,
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
  LayoutDashboard,
  Trash2,
  FileText,
  Webhook,
  Database,
  Cpu,
  FileSearch,
  Activity,
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
      <div className="min-h-screen flex items-center justify-center bg-[#212121]">
        <div className="animate-spin h-8 w-8 border-4 border-emerald-500 border-t-transparent rounded-full" />
      </div>
    )
  }

  if (!isAuthenticated || !user) return null

  const workspaceItems = [
    { href: "/dashboard", label: "Overview", icon: Brain },
    { href: "/dashboard/unlearning", label: "Unlearning", icon: Trash2 },
    { href: "/dashboard/rag", label: "RAG Documents", icon: FileSearch },
    { href: "/dashboard/models", label: "Model Registry", icon: Database },
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
    <div className="min-h-screen bg-[#212121] text-gray-100 flex overflow-hidden font-sans">
      {/* Sidebar */}
      <aside
        className={clsx(
          "bg-[#171717] w-64 border-r border-[#2f2f2f]/50 flex flex-col transition-all duration-300 z-30 shrink-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-64 absolute md:relative"
        )}
        style={{ height: "100vh" }}
      >
        {/* Sidebar Header */}
        <div className="p-3.5 flex items-center justify-between border-b border-[#2f2f2f]/30">
          <Link href="/dashboard" className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg hover:bg-[#2f2f2f] transition-colors w-full">
            <span className="text-emerald-500 text-xl font-semibold">⊗</span>
            <span className="font-semibold text-[15px] tracking-wide text-gray-200">VeriUnlearn v1.0</span>
          </Link>
          <button
            onClick={() => setSidebarOpen(false)}
            className="p-2 hover:bg-[#2f2f2f] rounded-lg text-gray-400 hover:text-white transition-colors cursor-pointer"
            title="Close sidebar"
          >
            <PanelLeftClose className="h-[18px] w-[18px]" />
          </button>
        </div>

        {/* New Deletion Request Button */}
        <div className="p-3.5">
          <Link href="/dashboard/unlearning/new">
            <button className="flex items-center justify-start gap-3 w-full px-3 py-2.5 bg-transparent hover:bg-[#2f2f2f] border border-[#2f2f2f] hover:border-gray-500 rounded-lg text-[14px] font-medium text-gray-200 transition-all cursor-pointer">
              <Plus className="h-4 w-4 text-gray-300" />
              New Deletion Request
            </button>
          </Link>
        </div>

        {/* Navigation List */}
        <div className="flex-1 overflow-y-auto px-3.5 py-2 space-y-6 scrollbar-thin scrollbar-thumb-[#2f2f2f]">
          {/* Workspace Category */}
          <div>
            <p className="text-[11px] font-semibold text-gray-500 px-3 uppercase tracking-wider mb-2">Workspace</p>
            <nav className="space-y-1">
              {workspaceItems.map((item) => {
                const isActive = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href))
                const Icon = item.icon
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={clsx(
                      "flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13px] font-medium transition-colors",
                      isActive
                        ? "bg-[#212121] text-white border border-[#2f2f2f]/80"
                        : "text-gray-400 hover:bg-[#2f2f2f] hover:text-white"
                    )}
                  >
                    <Icon className={clsx("h-4 w-4", isActive ? "text-emerald-500" : "text-gray-400")} />
                    {item.label}
                  </Link>
                )
              })}
            </nav>
          </div>

          {/* Configuration Category */}
          <div>
            <p className="text-[11px] font-semibold text-gray-500 px-3 uppercase tracking-wider mb-2">Configuration</p>
            <nav className="space-y-1">
              {configItems.map((item) => {
                const isActive = pathname === item.href || (item.href !== "/dashboard/admin" && pathname.startsWith(item.href))
                const Icon = item.icon
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={clsx(
                      "flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13px] font-medium transition-colors",
                      isActive
                        ? "bg-[#212121] text-white border border-[#2f2f2f]/80"
                        : "text-gray-400 hover:bg-[#2f2f2f] hover:text-white"
                    )}
                  >
                    <Icon className={clsx("h-4 w-4", isActive ? "text-emerald-500" : "text-gray-400")} />
                    {item.label}
                  </Link>
                )
              })}
            </nav>
          </div>
        </div>

        {/* Profile Card at the Bottom */}
        <div className="p-3.5 border-t border-[#2f2f2f]/30 relative" ref={profileRef}>
          {profileMenuOpen && (
            <div className="absolute bottom-16 left-3.5 right-3.5 bg-[#212121] border border-[#2f2f2f] rounded-xl shadow-2xl py-1.5 z-40 text-[13px] animate-in fade-in slide-in-from-bottom-2 duration-150">
              <Link
                href="/dashboard/profile"
                onClick={() => setProfileMenuOpen(false)}
                className="flex items-center gap-2.5 px-4 py-2.5 hover:bg-[#2f2f2f] text-gray-200 transition-colors"
              >
                <User className="h-4 w-4 text-gray-400" />
                My Profile
              </Link>
              <Link
                href="/dashboard/api-keys"
                onClick={() => setProfileMenuOpen(false)}
                className="flex items-center gap-2.5 px-4 py-2.5 hover:bg-[#2f2f2f] text-gray-200 transition-colors"
              >
                <Key className="h-4 w-4 text-gray-400" />
                API Credentials
              </Link>
              <Link
                href="/dashboard/sessions"
                onClick={() => setProfileMenuOpen(false)}
                className="flex items-center gap-2.5 px-4 py-2.5 hover:bg-[#2f2f2f] text-gray-200 transition-colors"
              >
                <ShieldAlert className="h-4 w-4 text-gray-400" />
                Active Sessions
              </Link>
              <div className="border-t border-[#2f2f2f]/50 my-1"></div>
              <button
                onClick={async () => {
                  setProfileMenuOpen(false)
                  await logout()
                  router.push("/auth/login")
                }}
                className="flex items-center gap-2.5 w-full text-left px-4 py-2.5 hover:bg-[#2f2f2f] text-red-400 hover:text-red-300 transition-colors cursor-pointer"
              >
                <LogOut className="h-4 w-4" />
                Sign Out
              </button>
            </div>
          )}

          <button
            onClick={() => setProfileMenuOpen(!profileMenuOpen)}
            className="flex items-center justify-between gap-3 w-full p-2.5 hover:bg-[#2f2f2f] rounded-xl text-left transition-colors cursor-pointer"
          >
            <div className="flex items-center gap-3 overflow-hidden">
              <div className="h-8 w-8 rounded-full bg-emerald-700/80 flex items-center justify-center text-white text-[13px] font-semibold uppercase shrink-0">
                {user.full_name.substring(0, 2)}
              </div>
              <div className="overflow-hidden">
                <p className="text-[13px] font-medium text-gray-200 truncate">{user.full_name}</p>
                <p className="text-[11px] text-gray-500 truncate">{user.email}</p>
              </div>
            </div>
            <ChevronDown className="h-4 w-4 text-gray-400 shrink-0" />
          </button>
        </div>
      </aside>

      {/* Main View Area */}
      <div className="flex-1 flex flex-col min-w-0 relative h-screen">
        {/* Sticky Header */}
        <header className="h-[60px] border-b border-[#2f2f2f]/30 flex items-center justify-between px-4 bg-[#212121]/90 backdrop-blur sticky top-0 z-20 shrink-0">
          <div className="flex items-center gap-3">
            {!sidebarOpen && (
              <button
                onClick={() => setSidebarOpen(true)}
                className="p-2 hover:bg-[#2f2f2f] rounded-lg text-gray-400 hover:text-white transition-colors cursor-pointer"
                title="Open sidebar"
              >
                <PanelLeft className="h-[18px] w-[18px]" />
              </button>
            )}
            
            {/* Model / Engine Dropdown Selector */}
            <div className="relative" ref={engineRef}>
              <button
                onClick={() => setEngineMenuOpen(!engineMenuOpen)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl hover:bg-[#2f2f2f] text-gray-200 hover:text-white text-[14px] font-semibold transition-colors cursor-pointer"
              >
                <span>{selectedEngine}</span>
                <ChevronDown className="h-4 w-4 text-gray-400" />
              </button>
              
              {engineMenuOpen && (
                <div className="absolute top-11 left-0 w-64 bg-[#171717] border border-[#2f2f2f] rounded-xl shadow-2xl py-1.5 z-40 text-[13px] animate-in fade-in slide-in-from-top-2 duration-150">
                  <div className="px-3.5 py-2 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Unlearning Policy</div>
                  {engines.map((eng) => (
                    <button
                      key={eng}
                      onClick={() => {
                        setSelectedEngine(eng)
                        setEngineMenuOpen(false)
                      }}
                      className={clsx(
                        "w-full text-left px-4 py-2.5 hover:bg-[#2f2f2f] flex items-center justify-between transition-colors cursor-pointer",
                        selectedEngine === eng ? "text-emerald-400 font-medium" : "text-gray-300"
                      )}
                    >
                      {eng}
                      {selectedEngine === eng && <span className="h-2 w-2 rounded-full bg-emerald-400"></span>}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Quick System Indicators */}
          <div className="flex items-center gap-4 text-xs text-gray-400">
            <div className="flex items-center gap-1.5 bg-[#171717] border border-[#2f2f2f]/60 px-2.5 py-1 rounded-full">
              <Database className="h-3.5 w-3.5 text-emerald-500 animate-pulse" />
              <span className="font-medium text-gray-300">SQLite</span>
            </div>
            <div className="flex items-center gap-1.5 bg-[#171717] border border-[#2f2f2f]/60 px-2.5 py-1 rounded-full">
              <Cpu className="h-3.5 w-3.5 text-emerald-500 animate-pulse" />
              <span className="font-medium text-gray-300">Memory Cache</span>
            </div>
          </div>
        </header>

        {/* Content Area */}
        <main className="flex-1 overflow-auto bg-[#212121] relative flex flex-col">
          {children}
        </main>
      </div>
    </div>
  )
}
