import Link from "next/link"
import { clsx } from "clsx"
import type { LucideIcon } from "lucide-react"

export function PageHeader({
  title,
  description,
  actions,
  breadcrumb,
  className,
}: {
  title: string
  description?: string
  actions?: React.ReactNode
  breadcrumb?: { label: string; href?: string }[]
  className?: string
}) {
  return (
    <div className={clsx("flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between", className)}>
      <div className="min-w-0">
        {breadcrumb && breadcrumb.length > 0 && (
          <nav className="mb-2 flex items-center gap-1.5 text-xs text-[var(--text-tertiary)]" aria-label="Breadcrumb">
            {breadcrumb.map((b, i) => (
              <span key={i} className="flex items-center gap-1.5">
                {b.href ? (
                  <Link href={b.href} className="transition-colors hover:text-[var(--text-secondary)]">
                    {b.label}
                  </Link>
                ) : (
                  <span className="text-[var(--text-secondary)]">{b.label}</span>
                )}
                {i < breadcrumb.length - 1 && <span aria-hidden>/</span>}
              </span>
            ))}
          </nav>
        )}
        <h1 className="text-xl font-semibold tracking-tight text-[var(--text-primary)] sm:text-2xl">
          {title}
        </h1>
        {description && (
          <p className="mt-1 text-sm text-[var(--text-secondary)]">{description}</p>
        )}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

/** A small KPI stat tile used across dashboards. */
export function StatCard({
  label,
  value,
  delta,
  icon: Icon,
  tone = "brand",
  hint,
}: {
  label: string
  value: React.ReactNode
  delta?: { value: string; positive?: boolean }
  icon?: LucideIcon
  tone?: "brand" | "info" | "warning" | "danger" | "success" | "purple"
  hint?: string
}) {
  const toneColor = {
    brand: "var(--brand)",
    info: "var(--info)",
    warning: "var(--warning)",
    danger: "var(--danger)",
    success: "var(--success)",
    purple: "var(--purple)",
  }[tone]

  return (
    <div className="surface rounded-xl p-5 transition-shadow hover:shadow-[var(--shadow-md)]">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">{label}</p>
        {Icon && (
          <span
            className="flex h-8 w-8 items-center justify-center rounded-lg"
            style={{ backgroundColor: `color-mix(in srgb, ${toneColor} 14%, transparent)`, color: toneColor }}
          >
            <Icon className="h-4 w-4" />
          </span>
        )}
      </div>
      <p className="mt-3 text-2xl font-semibold tabular-nums text-[var(--text-primary)]">{value}</p>
      <div className="mt-1.5 flex items-center gap-2">
        {delta && (
          <span
            className={clsx("text-xs font-medium", delta.positive ? "text-[var(--success)]" : "text-[var(--danger)]")}
          >
            {delta.positive ? "▲" : "▼"} {delta.value}
          </span>
        )}
        {hint && <span className="text-xs text-[var(--text-tertiary)]">{hint}</span>}
      </div>
    </div>
  )
}
