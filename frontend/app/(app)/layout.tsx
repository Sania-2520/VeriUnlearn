"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  LayoutDashboard,
  Fingerprint,
  Database,
  FileCheck2,
  ScrollText,
  Scale,
  Crosshair,
  Gauge,
  Settings,
  LogOut,
  Lock,
  Menu,
  X,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { Spinner } from "@/components/ui/progress";

const nav = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/privacy", label: "Privacy Auditor", icon: Fingerprint },
  { href: "/datasets", label: "Datasets & Training", icon: Database },
  { href: "/certificates", label: "Certificates", icon: FileCheck2 },
  { href: "/audit", label: "Audit Trail", icon: ScrollText },
  { href: "/compliance", label: "Compliance", icon: Scale },
  { href: "/attacks", label: "Attack Lab", icon: Crosshair },
  { href: "/benchmark", label: "Benchmark", icon: Gauge },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function AppLayout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!user) router.replace("/login");
  }, [user, router]);

  if (!user) {
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
        {nav.map((item) => {
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
          <span className="mono flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-[11px] text-emerald-300">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
            system online
          </span>
        </header>
        <main className="mx-auto max-w-7xl p-6">{children}</main>
      </div>
    </div>
  );
}
