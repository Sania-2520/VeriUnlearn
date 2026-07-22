import { clsx } from "clsx"
import { cva, type VariantProps } from "class-variance-authority"

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap ring-1 ring-inset transition-colors",
  {
    variants: {
      tone: {
        neutral: "bg-[var(--bg-subtle)] text-[var(--text-secondary)] ring-[var(--border-default)]",
        brand: "bg-[var(--brand-soft)] text-[var(--brand-strong)] ring-[var(--brand-border)]",
        accent: "bg-[var(--accent-soft)] text-[var(--accent)] ring-[var(--accent-soft)]",
        success: "bg-[var(--success-soft)] text-[var(--success)] ring-[var(--success-border)]",
        warning: "bg-[var(--warning-soft)] text-[var(--warning)] ring-[var(--warning-border)]",
        danger: "bg-[var(--danger-soft)] text-[var(--danger)] ring-[var(--danger-border)]",
        info: "bg-[var(--info-soft)] text-[var(--info)] ring-[var(--info-border)]",
        purple: "bg-[var(--purple-soft)] text-[var(--purple)] ring-[var(--purple-border)]",
      },
      dot: {
        true: "",
        false: "",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {
  dot?: boolean
}

export function Badge({ className, tone, dot, children, ...props }: BadgeProps) {
  return (
    <span className={clsx(badgeVariants({ tone }), className)} {...props}>
      {dot && (
        <span
          className={clsx("h-1.5 w-1.5 rounded-full", {
            "bg-[var(--text-tertiary)]": tone === "neutral",
            "bg-[var(--brand)]": tone === "brand",
            "bg-[var(--accent)]": tone === "accent",
            "bg-[var(--success)]": tone === "success",
            "bg-[var(--warning)]": tone === "warning",
            "bg-[var(--danger)]": tone === "danger",
            "bg-[var(--info)]": tone === "info",
            "bg-[var(--purple)]": tone === "purple",
          })}
        />
      )}
      {children}
    </span>
  )
}

/** Map a status string to a consistent tone. */
export function statusTone(status: string): NonNullable<BadgeProps["tone"]> {
  const s = status.toLowerCase()
  if (/(success|completed|verified|active|healthy|done)/.test(s)) return "success"
  if (/(pending|queued|waiting|scheduled)/.test(s)) return "warning"
  if (/(progress|running|processing|deploying)/.test(s)) return "info"
  if (/(failed|error|denied|rejected|expired|revoked)/.test(s)) return "danger"
  if (/(retry|retrying|paused|warning|degraded)/.test(s)) return "warning"
  return "neutral"
}
