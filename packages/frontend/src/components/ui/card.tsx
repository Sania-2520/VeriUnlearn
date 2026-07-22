import { clsx } from "clsx"

export function Card({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={clsx("surface rounded-xl shadow-[var(--shadow-sm)]", className)}
      {...props}
    >
      {children}
    </div>
  )
}

export function CardHeader({
  className,
  title,
  description,
  actions,
  children,
}: {
  className?: string
  title?: React.ReactNode
  description?: React.ReactNode
  actions?: React.ReactNode
  children?: React.ReactNode
}) {
  return (
    <div className={clsx("flex items-start justify-between gap-3 border-b border-[var(--border-subtle)] px-5 py-4", className)}>
      {children ?? (
        <div className="min-w-0">
          {title && <h3 className="text-sm font-semibold text-[var(--text-primary)]">{title}</h3>}
          {description && <p className="mt-0.5 text-xs text-[var(--text-secondary)]">{description}</p>}
        </div>
      )}
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  )
}

export function CardContent({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={clsx("px-5 py-4", className)} {...props}>
      {children}
    </div>
  )
}

export function CardFooter({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={clsx("border-t border-[var(--border-subtle)] px-5 py-4", className)} {...props}>
      {children}
    </div>
  )
}
