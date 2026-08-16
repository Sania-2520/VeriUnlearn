import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type Tone = "cyan" | "emerald" | "rose" | "amber" | "violet" | "slate";

const tones: Record<Tone, string> = {
  cyan: "bg-cyan-500/15 text-cyan-300 border-cyan-500/30",
  emerald: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  rose: "bg-rose-500/15 text-rose-300 border-rose-500/30",
  amber: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  violet: "bg-violet-500/15 text-violet-300 border-violet-500/30",
  slate: "bg-slate-500/15 text-slate-300 border-slate-500/30",
};

export function Badge({
  tone = "slate",
  className,
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: Tone }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-medium",
        tones[tone],
        className
      )}
      {...props}
    />
  );
}

export function statusTone(status: string): Tone {
  const s = status.toLowerCase();
  if (["completed", "valid", "ready", "ok", "compliant", "low"].includes(s)) return "emerald";
  if (["pending", "in_progress", "training", "review"].includes(s)) return "amber";
  if (["failed", "invalid", "high", "rejected"].includes(s)) return "rose";
  if (["running"].includes(s)) return "cyan";
  if (["medium"].includes(s)) return "amber";
  return "slate";
}
