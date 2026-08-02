"use client"

import { motion } from "framer-motion"
import {
  Skeleton,
  SkeletonGrid,
  SkeletonChart,
} from "@/components/ui/skeleton"
import { useReducedMotion } from "@/hooks/use-reduced-motion"

function ShimmerLine({ className }: { className?: string }) {
  const reduced = useReducedMotion()
  return (
    <motion.div
      className={className}
      initial={reduced ? {} : { opacity: 0.4 }}
      animate={reduced ? {} : { opacity: [0.4, 0.8, 0.4] }}
      transition={
        reduced
          ? {}
          : { duration: 1.8, repeat: Infinity, ease: "easeInOut" }
      }
    />
  )
}

export default function DashboardLoading() {
  const reduced = useReducedMotion()

  return (
    <div className="space-y-6 p-6" aria-busy="true" aria-label="Dashboard loading">
      <span className="sr-only">Dashboard is loading…</span>

      {/* Page header */}
      <div className="flex items-center justify-between">
        <div className="space-y-1.5">
          <ShimmerLine className="h-7 w-48 rounded-md bg-[var(--bg-hover)]" />
          <ShimmerLine className="h-4 w-72 rounded-md bg-[var(--bg-hover)]" />
        </div>
        <ShimmerLine className="h-9 w-32 rounded-lg bg-[var(--bg-hover)]" />
      </div>

      {/* Stat cards */}
      <motion.div
        initial={reduced ? {} : { opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: "easeOut" }}
      >
        <SkeletonGrid count={4} />
      </motion.div>

      {/* Chart area */}
      <motion.div
        initial={reduced ? {} : { opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: 0.08, ease: "easeOut" }}
      >
        <SkeletonChart />
      </motion.div>

      {/* Activity feed skeletons */}
      <motion.div
        initial={reduced ? {} : { opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: 0.16, ease: "easeOut" }}
        className="surface rounded-xl p-5"
      >
        <Skeleton className="mb-4 h-5 w-32" />
        <div className="space-y-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3">
              <Skeleton className="h-8 w-8 rounded-full" />
              <div className="flex-1 space-y-1.5">
                <Skeleton className="h-3 w-2/3" />
                <Skeleton className="h-3 w-1/3" />
              </div>
              <Skeleton className="h-4 w-12" />
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  )
}
