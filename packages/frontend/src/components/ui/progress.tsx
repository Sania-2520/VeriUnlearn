import { clsx } from "clsx"

export function Progress({
  value,
  tone = "brand",
  size = "md",
  showLabel = false,
  className,
}: {
  value: number
  tone?: "brand" | "info" | "warning" | "danger" | "success"
  size?: "sm" | "md"
  showLabel?: boolean
  className?: string
}) {
  const pct = Math.min(100, Math.max(0, value))
  const barColor = {
    brand: "var(--brand)",
    info: "var(--info)",
    warning: "var(--warning)",
    danger: "var(--danger)",
    success: "var(--success)",
  }[tone]

  return (
    <div className={clsx("flex items-center gap-2", className)}>
      <div
        className={clsx(
          "relative flex-1 overflow-hidden rounded-full bg-[var(--bg-subtle)]",
          size === "sm" ? "h-1.5" : "h-2.5",
        )}
        role="progressbar"
        aria-valuenow={Math.round(pct)}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="h-full rounded-full transition-[width] duration-500 ease-out"
          style={{ width: `${pct}%`, backgroundColor: barColor }}
        />
      </div>
      {showLabel && (
        <span className="text-xs tabular-nums text-[var(--text-secondary)] w-10 text-right">
          {Math.round(pct)}%
        </span>
      )}
    </div>
  )
}
