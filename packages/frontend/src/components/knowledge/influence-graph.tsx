"use client"

import { useKnowledgeStore } from "@/lib/store/knowledge-store"
import { KNOWLEDGE_TYPE_COLORS, KNOWLEDGE_TYPE_LABELS } from "@/lib/types/knowledge"
import { ArrowDown, TrendingUp, Trash2, Cpu } from "lucide-react"

export default function InfluenceGraph() {
  const { getInfluenceNodes } = useKnowledgeStore()
  const nodes = getInfluenceNodes()

  const sorted = [...nodes].sort((a, b) => b.influenceScore - a.influenceScore)

  return (
    <div className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-4">
      <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-1">Influence Visualization</h3>
      <p className="text-[11px] text-[var(--text-tertiary)] mb-4">How knowledge flows through the AI system</p>

      <div className="space-y-2">
        {sorted.slice(0, 8).map((node, idx) => {
          const color = KNOWLEDGE_TYPE_COLORS[node.type]
          return (
            <div key={node.id}>
              <div className="flex items-center gap-3 p-2.5 bg-[var(--bg-app)] rounded-lg border border-[var(--border-subtle)] hover:border-[var(--border-default)] transition-colors">
                <div
                  className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-[10px] font-bold text-[var(--text-on-brand)]"
                  style={{ backgroundColor: color }}
                >
                  {idx + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-[var(--text-primary)] truncate">{node.label}</span>
                    <span
                      className="text-[9px] font-mono px-1.5 py-0.5 rounded shrink-0"
                      style={{ backgroundColor: color + "20", color }}
                    >
                      {KNOWLEDGE_TYPE_LABELS[node.type]}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 mt-1.5">
                    <div className="flex items-center gap-1 text-[10px]">
                      <TrendingUp className="w-3 h-3 text-[var(--warning)]" />
                      <span className="text-[var(--text-secondary)]">Influence:</span>
                      <span className="text-[var(--text-primary)] font-medium">{Math.round(node.influenceScore * 100)}%</span>
                    </div>
                    <div className="flex items-center gap-1 text-[10px]">
                      <span className="text-[var(--text-secondary)]">Refs:</span>
                      <span className="text-[var(--text-primary)] font-medium">{node.referenceCount}</span>
                    </div>
                    <div className="flex items-center gap-1 text-[10px]">
                      <span className="text-[var(--text-secondary)]">Imp:</span>
                      <span className="text-[var(--text-primary)] font-medium">{Math.round(node.importance * 100)}%</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 mt-1">
                    <div className="flex items-center gap-1 text-[10px]">
                      <Trash2 className="w-3 h-3 text-[var(--danger)]" />
                      <span className="text-[var(--text-tertiary)]">Delete cost:</span>
                      <span className="text-[var(--danger)] font-medium">{node.deletionCost}</span>
                    </div>
                    <div className="flex items-center gap-1 text-[10px]">
                      <Cpu className="w-3 h-3 text-[var(--purple)]" />
                      <span className="text-[var(--text-tertiary)]">Retrain cost:</span>
                      <span className="text-[var(--purple)] font-medium">{node.retrainingCost}</span>
                    </div>
                  </div>
                  <div className="mt-1.5 h-1 bg-[var(--bg-hover)] rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${node.influenceScore * 100}%`,
                        backgroundColor: color,
                      }}
                    />
                  </div>
                </div>
              </div>
              {idx < Math.min(sorted.length, 8) - 1 && (
                <div className="flex justify-center py-1">
                  <ArrowDown className="w-4 h-4 text-[var(--text-tertiary)]" />
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
