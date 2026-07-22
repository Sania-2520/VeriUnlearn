"use client"

import { useKnowledgeStore } from "@/lib/store/knowledge-store"
import { KNOWLEDGE_TYPE_COLORS, KNOWLEDGE_TYPE_LABELS } from "@/lib/types/knowledge"
import type { KnowledgeLineageStep } from "@/lib/types/knowledge"
import { formatDate } from "@/lib/utils"
import { ArrowDown, Check, Clock, Loader2 } from "lucide-react"

export default function KnowledgeLineage() {
  const { lineage, selectedItemId } = useKnowledgeStore()

  const getStatusIcon = (status: KnowledgeLineageStep["status"]) => {
    switch (status) {
      case "completed":
        return <Check className="w-3.5 h-3.5 text-[var(--success)]" />
      case "current":
        return <Loader2 className="w-3.5 h-3.5 text-[var(--warning)] animate-spin" />
      case "pending":
        return <Clock className="w-3.5 h-3.5 text-[var(--text-tertiary)]" />
      case "removed":
        return <span className="w-3.5 h-3.5 flex items-center justify-center text-[var(--danger)] text-xs">✕</span>
    }
  }

  return (
    <div className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-4">
      <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-4">Knowledge Lineage</h3>
      {!selectedItemId ? (
        <p className="text-xs text-[var(--text-tertiary)] text-center py-8">Select a knowledge item to view its lineage</p>
      ) : (
        <div className="space-y-0">
          {lineage.map((step, idx) => {
            const color = KNOWLEDGE_TYPE_COLORS[step.type]
            return (
              <div key={step.id}>
                <div className="flex items-start gap-3">
                  <div className="flex flex-col items-center">
                    <div
                      className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 border-2"
                      style={{
                        borderColor: step.status === "removed" ? "var(--danger)" : color,
                        backgroundColor: color + "15",
                      }}
                    >
                      {getStatusIcon(step.status)}
                    </div>
                    {idx < lineage.length - 1 && (
                      <ArrowDown className="w-4 h-4 text-[var(--text-tertiary)] my-1" />
                    )}
                  </div>
                  <div className="pb-4 min-w-0">
                    <div className="flex items-center gap-2">
                      <span
                        className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                        style={{ backgroundColor: color + "20", color }}
                      >
                        {KNOWLEDGE_TYPE_LABELS[step.type]}
                      </span>
                    </div>
                    <p className="text-xs font-medium text-[var(--text-primary)] mt-1">{step.label}</p>
                    <p className="text-[11px] text-[var(--text-tertiary)] mt-0.5">{step.description}</p>
                    <p className="text-[10px] text-[var(--text-tertiary)] mt-1 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatDate(step.timestamp)}
                    </p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
