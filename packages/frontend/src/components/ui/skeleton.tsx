"use client"

import { clsx } from "clsx"
import { useReducedMotion } from "@/hooks/use-reduced-motion"

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  disableAnimation?: boolean
}

export function Skeleton({ className, disableAnimation, ...props }: SkeletonProps) {
  const reducedMotion = useReducedMotion()
  const noAnim = disableAnimation || reducedMotion

  return (
    <div
      className={clsx(
        "rounded-md bg-[var(--bg-subtle)]",
        !noAnim && "skeleton-shimmer",
        className,
      )}
      aria-hidden="true"
      {...props}
    />
  )
}

export function SkeletonCard({ className }: { className?: string }) {
  return (
    <div className={clsx("surface rounded-xl p-5", className)}>
      <Skeleton className="h-3 w-20" />
      <Skeleton className="mt-3 h-7 w-16" />
      <Skeleton className="mt-3 h-2.5 w-full rounded-full" />
    </div>
  )
}

export function SkeletonChart({ className }: { className?: string }) {
  return (
    <div
      className={clsx(
        "surface relative overflow-hidden rounded-xl p-5",
        className,
      )}
      aria-hidden="true"
    >
      {/* Fake Y-axis */}
      <div className="absolute left-5 top-5 flex flex-col justify-between">
        <Skeleton className="h-2.5 w-8" />
        <Skeleton className="h-2.5 w-8" />
        <Skeleton className="h-2.5 w-8" />
      </div>
      {/* Chart bars */}
      <div className="flex items-end justify-around gap-2 pl-14 pt-5">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton
            key={i}
            className="w-6"
            style={{ height: `${20 + Math.random() * 60}%` }}
          />
        ))}
      </div>
      {/* Fake X-axis labels */}
      <div className="mt-3 flex justify-around gap-2 pl-14">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-2 w-8" />
        ))}
      </div>
    </div>
  )
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="surface overflow-hidden rounded-xl" aria-busy="true">
      <span className="sr-only">Loading table…</span>
      {/* Header */}
      <div className="flex gap-4 border-b border-[var(--border-subtle)] px-5 py-3.5">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-3.5 flex-1" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="flex gap-4 border-b border-[var(--border-subtle)] px-5 py-3.5 last:border-0"
        >
          {Array.from({ length: 4 }).map((_, j) => (
            <Skeleton key={j} className="h-3 flex-1" />
          ))}
        </div>
      ))}
    </div>
  )
}

export function SkeletonText({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-2" aria-hidden="true">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={clsx("h-3", i === lines - 1 ? "w-3/4" : "w-full")}
        />
      ))}
    </div>
  )
}

/** @deprecated Use SkeletonCard instead */
export const SkeletonCards = SkeletonGrid

/** @deprecated Use SkeletonTable instead */
export const SkeletonRows = SkeletonTable

export function SkeletonGrid({ count = 4 }: { count?: number }) {
  return (
    <div
      className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
      aria-busy="true"
    >
      <span className="sr-only">Loading…</span>
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  )
}
