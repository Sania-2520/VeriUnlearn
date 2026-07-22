"use client"

import { Check, X, Minus } from "lucide-react"
import type { StorageLocation } from "@/lib/types/knowledge"
import { STORAGE_LOCATION_LABELS } from "@/lib/types/knowledge"

interface StorageBadgesProps {
  storageLocations: Record<StorageLocation, "exists" | "removed" | "never_stored">
  compact?: boolean
}

const statusConfig = {
  exists: { icon: Check, color: "text-[var(--success)]", bg: "bg-[var(--success-soft)]", border: "border-[var(--success-border)]", label: "Exists" },
  removed: { icon: X, color: "text-[var(--danger)]", bg: "bg-[var(--danger-soft)]", border: "border-[var(--danger-border)]", label: "Removed" },
  never_stored: { icon: Minus, color: "text-[var(--text-tertiary)]", bg: "bg-[var(--bg-subtle)]", border: "border-[var(--border-default)]", label: "Never Stored" },
}

export default function StorageBadges({ storageLocations, compact = false }: StorageBadgesProps) {
  const locations = Object.entries(storageLocations) as [StorageLocation, "exists" | "removed" | "never_stored"][]

  if (compact) {
    return (
      <div className="flex flex-wrap gap-1.5">
        {locations.map(([loc, status]) => {
          const config = statusConfig[status]
          const Icon = config.icon
          return (
            <div
              key={loc}
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${config.bg} ${config.border} border ${config.color}`}
              title={`${STORAGE_LOCATION_LABELS[loc]}: ${config.label}`}
            >
              <Icon className="w-2.5 h-2.5" />
              <span className="hidden xl:inline">{STORAGE_LOCATION_LABELS[loc]}</span>
              <span className="xl:hidden">{STORAGE_LOCATION_LABELS[loc].split(" ")[0]}</span>
            </div>
          )
        })}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-3 gap-2">
      {locations.map(([loc, status]) => {
        const config = statusConfig[status]
        const Icon = config.icon
        return (
          <div
            key={loc}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg ${config.bg} border ${config.border}`}
          >
            <Icon className={`w-4 h-4 ${config.color} shrink-0`} />
            <div className="min-w-0">
              <p className="text-[11px] font-medium text-[var(--text-primary)] truncate">{STORAGE_LOCATION_LABELS[loc]}</p>
              <p className={`text-[10px] ${config.color}`}>{config.label}</p>
            </div>
          </div>
        )
      })}
    </div>
  )
}
