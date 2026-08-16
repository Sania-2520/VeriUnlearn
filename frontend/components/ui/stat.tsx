import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function StatCard({
  label,
  value,
  sub,
  icon,
  accent = "text-cyan-400",
  delay = 0,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  icon?: ReactNode;
  accent?: string;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4 }}
    >
      <Card className="relative overflow-hidden">
        <div className="absolute -right-6 -top-6 h-24 w-24 rounded-full bg-cyan-500/10 blur-2xl" />
        <div className="flex items-start justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">{label}</p>
            <p className={cn("mt-2 text-3xl font-bold tracking-tight", accent)}>{value}</p>
            {sub && <div className="mt-1 text-xs text-slate-500">{sub}</div>}
          </div>
          {icon && <div className={cn("rounded-xl bg-slate-800/70 p-2.5", accent)}>{icon}</div>}
        </div>
      </Card>
    </motion.div>
  );
}
