"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  Fingerprint,
  FileCheck2,
  ScrollText,
  LogOut,
  Lock,
  Menu,
  X,
  Scissors,
  ShieldCheck,
  Bell,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { canView, isRole, type Role } from "@/lib/rbac";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Spinner } from "@/components/ui/progress";
import { useQuery } from "@tanstack/react-query";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  roles: Role[];
}

const nav: NavItem[] = [
  { href: "/assistant", label: "Assistant", icon: Sparkles, roles: ["admin", "researcher", "auditor", "operator", "viewer"] },
  { href: "/audit", label: "Audit Trail", icon: ScrollText, roles: ["admin", "researcher", "auditor"] },
  { href: "/privacy", label: "Privacy Auditor", icon: Fingerprint, roles: ["admin", "researcher", "auditor", "operator", "viewer"] },
  { href: "/unlearning", label: "Surgical Unlearning", icon: Scissors, roles: ["admin", "operator"] },
  { href: "/verification", label: "Verification", icon: ShieldCheck, roles: ["admin", "researcher", "auditor", "operator"] },
  { href: "/certificates", label: "Certificates", icon: FileCheck2, roles: ["admin", "researcher", "auditor", "operator", "viewer"] },
];

export default function AppLayout({ children }: { children: ReactNode }) {
  const { user, initialized, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);

  const unread = useQuery<{ unread: number }>({
    queryKey: ["notifications-unread"],
    queryFn: () => api.get("/api/v1/notifications/unread-count"),
    refetchInterval: 30_000,
  });

  useEffect(() => {
    if (!initialized) return;
    if (!user) router.replace("/login");
  }, [initialized, user, router]);

  // Phase 7 page guard: hide routes the user's role cannot access.
  useEffect(() => {
    if (!initialized || !user) return;
    if (!canView(user.role, pathname)) router.replace("/assistant");
  }, [initialized, user, pathname, router]);

  if (!initialized || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  const sidebar = (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 px-5 py-5">
        <Lock className="h-6 w-6 text-cyan-400" />
        <span className="text-lg font-bold tracking-tight">
          Veri<span className="text-cyan-400">Unlearn</span>
        </span>
      </div>
      <nav className="flex-1 space-y-1 px-3">
        {nav.filter((item) => isRole(user.role, ...item.roles)).map((item) => {
          const active = pathname.startsWith(item.href);
          return (
            <Link key={item.href} href={item.href} onClick={() => setOpen(false)}>
              <span
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-all",
                  active
                    ? "bg-cyan-500/10 font-medium text-cyan-300 shadow-[inset_0_0_0_1px_rgba(34,211,238,0.25)]"
                    : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
                )}
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </span>
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-slate-800/70 p-4">
        <div className="mb-3 flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-cyan-500 to-violet-500 text-sm font-bold text-slate-950">
            {(user.full_name || "U").slice(0, 1).toUpperCase()}
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-slate-200">{user.full_name}</p>
            <p className="text-xs capitalize text-slate-500">{user.role}</p>
          </div>
        </div>
        <button
          onClick={logout}
          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-400 transition-colors hover:bg-rose-500/10 hover:text-rose-300"
        >
          <LogOut className="h-4 w-4" /> Sign out
        </button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen cyber-grid">
      {/* desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 border-r border-slate-800/70 bg-[#070b14]/90 backdrop-blur lg:block">
        {sidebar}
      </aside>

      {/* mobile drawer */}
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setOpen(false)} />
          <motion.aside
            initial={{ x: -260 }}
            animate={{ x: 0 }}
            className="absolute inset-y-0 left-0 w-60 border-r border-slate-800 bg-[#070b14]"
          >
            <button onClick={() => setOpen(false)} className="absolute right-3 top-4 text-slate-500">
              <X className="h-5 w-5" />
            </button>
            {sidebar}
          </motion.aside>
        </div>
      )}

      <div className="lg:pl-60">
        <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-slate-800/70 bg-[#05070d]/80 px-5 backdrop-blur">
          <button className="lg:hidden text-slate-400" onClick={() => setOpen(true)}>
            <Menu className="h-5 w-5" />
          </button>
          <p className="mono text-xs text-slate-500">
            {pathname.replace("/", "") || "dashboard"}
          </p>
          <div className="flex items-center gap-3">
            <Link href="/notifications" className="relative text-slate-400 transition-colors hover:text-cyan-300">
              <Bell className="h-5 w-5" />
              {(unread.data?.unread ?? 0) > 0 && (
                <span className="absolute -right-1.5 -top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-bold text-white">
                  {Math.min(unread.data?.unread ?? 0, 99)}
                </span>
              )}
            </Link>
            <span className="mono flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-[11px] text-emerald-300">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
              system online
            </span>
          </div>
        </header>
        <main className="mx-auto max-w-7xl p-6">{children}</main>
      </div>
    </div>
  );
}
