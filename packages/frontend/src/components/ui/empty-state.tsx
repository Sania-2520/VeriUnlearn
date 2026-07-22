import Link from "next/link"
import { clsx } from "clsx"
import type { LucideIcon } from "lucide-react"

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  actionHref,
  className,
}: {
  icon?: LucideIcon
  title: string
  description?: string
  action?: string
  actionHref?: string
  className?: string
}) {
  const content = (
    <div
      className={clsx(
        "flex flex-col items-center justify-center rounded-xl border border-dashed border-[var(--border-default)] bg-[var(--bg-subtle)]/40 px-6 py-14 text-center animate-fade-up",
        className,
      )}
    >
      {Icon && (
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-[var(--brand-soft)] text-[var(--brand)]">
          <Icon className="h-6 w-6" />
        </div>
      )}
      <p className="text-base font-semibold text-[var(--text-primary)]">{title}</p>
      {description && (
        <p className="mt-1.5 max-w-sm text-sm text-[var(--text-secondary)]">{description}</p>
      )}
      {action && actionHref && (
        <Link
          href={actionHref}
          className="mt-5 inline-flex items-center rounded-lg bg-[var(--brand)] px-4 py-2 text-sm font-medium text-[var(--text-on-brand)] transition-colors hover:bg-[var(--brand-strong)]"
        >
          {action}
        </Link>
      )}
    </div>
  )
  return content
}

export function ErrorState({
  title = "Something went wrong",
  description,
  onRetry,
  className,
}: {
  title?: string
  description?: string
  onRetry?: () => void
  className?: string
}) {
  return (
    <div
      role="alert"
      className={clsx(
        "flex flex-col items-center justify-center rounded-xl border border-[var(--danger-border)] bg-[var(--danger-soft)] px-6 py-12 text-center animate-fade-up",
        className,
      )}
    >
      <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-[var(--danger-soft)] text-[var(--danger)] ring-1 ring-[var(--danger-border)]">
        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 9v4m0 4h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
      <p className="text-base font-semibold text-[var(--text-primary)]">{title}</p>
      {description && (
        <p className="mt-1.5 max-w-sm text-sm text-[var(--text-secondary)]">{description}</p>
      )}
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-5 inline-flex items-center rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] px-4 py-2 text-sm font-medium text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-hover)]"
        >
          Try again
        </button>
      )}
    </div>
  )
}

export function SuccessBanner({
  title,
  description,
  className,
}: {
  title: string
  description?: string
  className?: string
}) {
  return (
    <div
      className={clsx(
        "flex items-start gap-3 rounded-lg border border-[var(--success-border)] bg-[var(--success-soft)] px-4 py-3 text-sm animate-fade-up",
        className,
      )}
    >
      <svg viewBox="0 0 24 24" className="mt-0.5 h-5 w-5 shrink-0 text-[var(--success)]" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="m5 13 4 4L19 7" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <div>
        <p className="font-medium text-[var(--text-primary)]">{title}</p>
        {description && <p className="mt-0.5 text-[var(--text-secondary)]">{description}</p>}
      </div>
    </div>
  )
}
