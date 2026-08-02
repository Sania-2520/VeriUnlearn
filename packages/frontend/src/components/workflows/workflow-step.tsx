"use client"

import { motion } from "framer-motion"
import { clsx } from "clsx"
import { AlertCircle, RefreshCw } from "lucide-react"
import { useWorkflow } from "./workflow-context"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"

const variants = {
  enter: (direction: number) => ({
    x: direction > 0 ? 80 : -80,
    opacity: 0,
  }),
  center: {
    x: 0,
    opacity: 1,
  },
  exit: (direction: number) => ({
    x: direction > 0 ? -80 : 80,
    opacity: 0,
  }),
}

export function WorkflowStep({
  title,
  description,
  children,
  error,
  onRetry,
  loading,
  className,
}: {
  title?: string
  description?: string
  children: React.ReactNode
  error?: string | null
  onRetry?: () => void
  loading?: boolean
  className?: string
}) {
  const { direction } = useWorkflow()

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-4 w-72" />
        <div className="mt-6 space-y-3">
          <Skeleton className="h-12 w-full rounded-lg" />
          <Skeleton className="h-12 w-full rounded-lg" />
          <Skeleton className="h-12 w-3/4 rounded-lg" />
        </div>
      </div>
    )
  }

  return (
    <motion.div
      custom={direction}
      variants={variants}
      initial="enter"
      animate="center"
      exit="exit"
      transition={{
        x: { type: "spring", stiffness: 300, damping: 30 },
        opacity: { duration: 0.2 },
      }}
      className={clsx("min-h-[320px]", className)}
    >
      {title && (
        <h2 className="text-lg font-semibold text-[var(--text-primary)]">{title}</h2>
      )}
      {description && (
        <p className="mt-1 text-sm text-[var(--text-secondary)]">{description}</p>
      )}

      <div className="mt-6">{children}</div>

      {error && (
        <div className="mt-4 flex items-start gap-3 rounded-lg border border-[var(--danger-border)] bg-[var(--danger-soft)] p-3">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-[var(--danger)]" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-[var(--danger)]">Error</p>
            <p className="mt-0.5 text-xs text-[var(--text-secondary)]">{error}</p>
          </div>
          {onRetry && (
            <Button variant="ghost" size="sm" onClick={onRetry} className="shrink-0">
              <RefreshCw className="mr-1 h-3.5 w-3.5" />
              Retry
            </Button>
          )}
        </div>
      )}
    </motion.div>
  )
}
