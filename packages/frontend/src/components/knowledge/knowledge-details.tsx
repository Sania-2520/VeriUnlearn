"use client"

import { useKnowledgeStore } from "@/lib/store/knowledge-store"
import { formatDate } from "@/lib/utils"
import StorageBadges from "./storage-badges"
import {
  KNOWLEDGE_TYPE_LABELS,
  KNOWLEDGE_TYPE_COLORS,
} from "@/lib/types/knowledge"
import {
  X,
  ExternalLink,
  Shield,
  Clock,
  Brain,
  Zap,
  Link2,
  Trash2,
} from "lucide-react"

export default function KnowledgeDetails() {
  const { items, selectedItemId, selectItem, startUnlearning } = useKnowledgeStore()
  const item = items.find((i) => i.id === selectedItemId)

  if (!item) return null

  const typeColor = KNOWLEDGE_TYPE_COLORS[item.type]

  return (
    <div className="h-full flex flex-col bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl overflow-hidden">
      <div className="p-4 border-b border-[var(--border-subtle)] flex items-start justify-between">
        <div className="flex items-start gap-3 min-w-0">
          <div
            className="w-3 h-3 rounded-full mt-1.5 shrink-0"
            style={{ backgroundColor: typeColor }}
          />
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-[var(--text-primary)] truncate">{item.title}</h3>
            <span
              className="inline-block mt-1 px-2 py-0.5 rounded-full text-[10px] font-medium text-[var(--text-primary)]"
              style={{ backgroundColor: typeColor + "40" }}
            >
              {KNOWLEDGE_TYPE_LABELS[item.type]}
            </span>
          </div>
        </div>
        <button
          onClick={() => selectItem(null)}
          className="p-1 hover:bg-[var(--bg-hover)] rounded-lg text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors shrink-0"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <p className="text-xs text-[var(--text-secondary)] leading-relaxed">{item.description}</p>

        <div className="grid grid-cols-2 gap-3">
          <div className="bg-[var(--bg-app)] rounded-lg p-3 border border-[var(--border-subtle)]">
            <div className="flex items-center gap-1.5 mb-1">
              <Shield className="w-3 h-3 text-[var(--success)]" />
              <span className="text-[10px] font-medium text-[var(--text-tertiary)] uppercase">Confidence</span>
            </div>
            <div className="flex items-baseline gap-1">
              <span className="text-lg font-bold text-[var(--text-primary)]">{Math.round(item.learningConfidence * 100)}</span>
              <span className="text-xs text-[var(--text-secondary)]">%</span>
            </div>
            <div className="mt-1.5 h-1 bg-[var(--bg-hover)] rounded-full overflow-hidden">
              <div
                className="h-full bg-[var(--success)] rounded-full transition-all"
                style={{ width: `${item.learningConfidence * 100}%` }}
              />
            </div>
          </div>
          <div className="bg-[var(--bg-app)] rounded-lg p-3 border border-[var(--border-subtle)]">
            <div className="flex items-center gap-1.5 mb-1">
              <Brain className="w-3 h-3 text-[var(--info)]" />
              <span className="text-[10px] font-medium text-[var(--text-tertiary)] uppercase">Importance</span>
            </div>
            <div className="flex items-baseline gap-1">
              <span className="text-lg font-bold text-[var(--text-primary)]">{Math.round(item.importanceScore * 100)}</span>
              <span className="text-xs text-[var(--text-secondary)]">%</span>
            </div>
            <div className="mt-1.5 h-1 bg-[var(--bg-hover)] rounded-full overflow-hidden">
              <div
                className="h-full bg-[var(--info)] rounded-full transition-all"
                style={{ width: `${item.importanceScore * 100}%` }}
              />
            </div>
          </div>
          <div className="bg-[var(--bg-app)] rounded-lg p-3 border border-[var(--border-subtle)]">
            <div className="flex items-center gap-1.5 mb-1">
              <Zap className="w-3 h-3 text-[var(--warning)]" />
              <span className="text-[10px] font-medium text-[var(--text-tertiary)] uppercase">Influence</span>
            </div>
            <div className="flex items-baseline gap-1">
              <span className="text-lg font-bold text-[var(--text-primary)]">{Math.round(item.influenceScore * 100)}</span>
              <span className="text-xs text-[var(--text-secondary)]">%</span>
            </div>
            <div className="mt-1.5 h-1 bg-[var(--bg-hover)] rounded-full overflow-hidden">
              <div
                className="h-full bg-[var(--warning)] rounded-full transition-all"
                style={{ width: `${item.influenceScore * 100}%` }}
              />
            </div>
          </div>
          <div className="bg-[var(--bg-app)] rounded-lg p-3 border border-[var(--border-subtle)]">
            <div className="flex items-center gap-1.5 mb-1">
              <Link2 className="w-3 h-3 text-[var(--purple)]" />
              <span className="text-[10px] font-medium text-[var(--text-tertiary)] uppercase">References</span>
            </div>
            <span className="text-lg font-bold text-[var(--text-primary)]">{item.referencedResponseCount}</span>
            <span className="text-xs text-[var(--text-secondary)] ml-1">responses</span>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-[var(--text-tertiary)]">Knowledge ID</span>
            <span className="text-[var(--text-secondary)] font-mono">{item.id}</span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-[var(--text-tertiary)]">Status</span>
            <span
              className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                item.status === "active"
                  ? "bg-[var(--success-soft)] text-[var(--success)] border border-[var(--success-border)]"
                  : item.status === "unlearned"
                  ? "bg-[var(--danger-soft)] text-[var(--danger)] border border-[var(--danger-border)]"
                  : "bg-[var(--warning-soft)] text-[var(--warning)] border border-[var(--warning-border)]"
              }`}
            >
              {item.status}
            </span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-[var(--text-tertiary)]">Verification</span>
            <span
              className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                item.verificationStatus === "verified"
                  ? "bg-[var(--success-soft)] text-[var(--success)] border border-[var(--success-border)]"
                  : "bg-[var(--warning-soft)] text-[var(--warning)] border border-[var(--warning-border)]"
              }`}
            >
              {item.verificationStatus}
            </span>
          </div>
          {item.certificateId && (
            <div className="flex items-center justify-between text-xs">
              <span className="text-[var(--text-tertiary)]">Certificate</span>
              <span className="text-[var(--info)] font-mono text-[11px] flex items-center gap-1">
                {item.certificateId}
                <ExternalLink className="w-3 h-3" />
              </span>
            </div>
          )}
          <div className="flex items-center justify-between text-xs">
            <span className="text-[var(--text-tertiary)]">Source Conversation</span>
            <span className="text-[var(--text-secondary)] font-mono">{item.sourceConversationId || "N/A"}</span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-[var(--text-tertiary)]">Source Message</span>
            <span className="text-[var(--text-secondary)] font-mono">{item.sourceMessageId || "N/A"}</span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-[var(--text-tertiary)]">LoRA Version</span>
            <span className="text-[var(--accent)] font-mono">{item.loraAdapterVersion || "N/A"}</span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-[var(--text-tertiary)]">Date Learned</span>
            <span className="text-[var(--text-secondary)] flex items-center gap-1">
              <Clock className="w-3 h-3 text-[var(--text-tertiary)]" />
              {formatDate(item.dateLearned)}
            </span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-[var(--text-tertiary)]">Last Accessed</span>
            <span className="text-[var(--text-secondary)] flex items-center gap-1">
              <Clock className="w-3 h-3 text-[var(--text-tertiary)]" />
              {formatDate(item.lastAccessed)}
            </span>
          </div>
        </div>

        {item.associatedEmbeddings.length > 0 && (
          <div>
            <p className="text-[10px] font-semibold text-[var(--text-tertiary)] uppercase tracking-wider mb-2">Associated Embeddings</p>
            <div className="flex flex-wrap gap-1.5">
              {item.associatedEmbeddings.map((emb) => (
                <span key={emb} className="px-2 py-0.5 bg-[var(--warning-soft)] text-[var(--warning)] border border-[var(--warning-border)] rounded-full text-[10px] font-mono">
                  {emb}
                </span>
              ))}
            </div>
          </div>
        )}

        {item.trainingSamples.length > 0 && (
          <div>
            <p className="text-[10px] font-semibold text-[var(--text-tertiary)] uppercase tracking-wider mb-2">Training Samples</p>
            <div className="flex flex-wrap gap-1.5">
              {item.trainingSamples.map((ts) => (
                <span key={ts} className="px-2 py-0.5 bg-[var(--danger-soft)] text-[var(--danger)] border border-[var(--danger-border)] rounded-full text-[10px] font-mono">
                  {ts}
                </span>
              ))}
            </div>
          </div>
        )}

        {item.memoryGraphConnections.length > 0 && (
          <div>
            <p className="text-[10px] font-semibold text-[var(--text-tertiary)] uppercase tracking-wider mb-2">Memory Graph Connections</p>
            <div className="flex flex-wrap gap-1.5">
              {item.memoryGraphConnections.map((mem) => (
                <span key={mem} className="px-2 py-0.5 bg-[var(--info-soft)] text-[var(--info)] border border-[var(--info-border)] rounded-full text-[10px] font-mono">
                  {mem}
                </span>
              ))}
            </div>
          </div>
        )}

        {item.tags.length > 0 && (
          <div>
            <p className="text-[10px] font-semibold text-[var(--text-tertiary)] uppercase tracking-wider mb-2">Tags</p>
            <div className="flex flex-wrap gap-1.5">
              {item.tags.map((tag) => (
                <span key={tag} className="px-2 py-0.5 bg-[var(--bg-subtle)] text-[var(--text-secondary)] rounded-full text-[10px]">
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}

        <div>
          <p className="text-[10px] font-semibold text-[var(--text-tertiary)] uppercase tracking-wider mb-2">Storage Locations</p>
          <StorageBadges storageLocations={item.storageLocations} />
        </div>
      </div>

      <div className="p-4 border-t border-[var(--border-subtle)]">
        <button
          onClick={() => startUnlearning(item.id)}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-[var(--danger-soft)] hover:bg-[var(--danger-soft)] text-[var(--danger)] hover:opacity-90 border border-[var(--danger-border)] rounded-lg text-sm font-medium transition-colors"
        >
          <Trash2 className="w-4 h-4" />
          Machine Unlearn This Knowledge
        </button>
      </div>
    </div>
  )
}
