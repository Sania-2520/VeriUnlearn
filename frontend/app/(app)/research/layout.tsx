"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { Atom, BarChart3, FlaskConical, Gauge, TestTubes } from "lucide-react";
import { cn } from "@/lib/utils";

const tabs = [
  { href: "/research", label: "Research Dashboard", icon: Atom, exact: true },
  { href: "/research/benchmark", label: "Benchmark", icon: BarChart3 },
  { href: "/research/experiments", label: "Experiments", icon: FlaskConical },
  { href: "/research/attacks", label: "Attack Suite", icon: TestTubes },
  { href: "/research/performance", label: "Performance", icon: Gauge },
];

export default function ResearchLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2">
        {tabs.map((t) => {
          const active = t.exact ? pathname === t.href : pathname.startsWith(t.href);
          return (
            <Link key={t.href} href={t.href}>
              <span
                className={cn(
                  "flex items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors",
                  active
                    ? "border-violet-400/40 bg-violet-500/10 text-violet-200"
                    : "border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200"
                )}
              >
                <t.icon className="h-4 w-4" />
                {t.label}
              </span>
            </Link>
          );
        })}
      </div>
      {children}
    </div>
  );
}
