"use client"

import { useEffect, useState, useCallback } from "react"
import { Button } from "@/components/ui/button"
import {
  listModelVersions,
  rollbackVersion,
  verifyVersion,
} from "@/lib/api/client"
import {
  GitBranch,
  ShieldCheck,
  RotateCcw,
  Clock,
  AlertCircle,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  Lock,
  Hash,
} from "lucide-react"

interface ModelVersionEntry {
  id: string
  model_name: string
  version: string
  algorithm: string
  status: "active" | "archived" | "training"
  metrics?: Record<string, number>
  sha256?: string
  config?: Record<string, unknown>
  created_at: string
  updated_at?: string
}

export default function ModelsPage() {
  const [versions, setVersions] = useState<ModelVersionEntry[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [compareIds, setCompareIds] = useState<string[]>([])
  const [verifyingId, setVerifyingId] = useState<string | null>(null)
  const [rollingBackId, setRollingBackId] = useState<string | null>(null)
  const [filterModel, setFilterModel] = useState<string>("")

  const fetchVersions = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const res = await listModelVersions(filterModel || undefined)
      setVersions(res.data || res.versions || [])
    } catch {
      setError("Failed to load model versions")
    } finally {
      setIsLoading(false)
    }
  }, [filterModel])

  useEffect(() => {
    fetchVersions()
  }, [fetchVersions])

  const modelNames = Array.from(new Set(versions.map((v) => v.model_name)))

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id)
  }

  const toggleCompare = (id: string) => {
    setCompareIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : prev.length < 2 ? [...prev, id] : [prev[1], id]
    )
  }

  const handleVerify = async (modelName: string, versionId: string) => {
    setVerifyingId(versionId)
    setError(null)
    try {
      await verifyVersion(modelName, versionId)
      await fetchVersions()
    } catch {
      setError("Verification failed")
    } finally {
      setVerifyingId(null)
    }
  }

  const handleRollback = async (modelName: string, versionId: string) => {
    if (!confirm("Are you sure you want to rollback to this version?")) return
    setRollingBackId(versionId)
    setError(null)
    try {
      await rollbackVersion(modelName, versionId)
      await fetchVersions()
    } catch {
      setError("Rollback failed")
    } finally {
      setRollingBackId(null)
    }
  }

  const comparedVersions = compareIds.length === 2
    ? versions.filter((v) => compareIds.includes(v.id))
    : []

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-on-brand)]">Model Registry</h1>
          <p className="text-sm text-[var(--text-tertiary)] mt-1">Manage model versions, verify integrity, and rollback</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={filterModel}
            onChange={(e) => setFilterModel(e.target.value)}
            className="px-3 py-2 text-sm bg-[var(--bg-app)] border border-[var(--border-default)] focus:border-[var(--border-strong)] rounded-lg text-[var(--text-secondary)] focus:outline-none appearance-none cursor-pointer"
          >
            <option value="">All Models</option>
            {modelNames.map((name) => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
          <button
            onClick={fetchVersions}
            className="flex items-center gap-2 px-3 py-2 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] bg-[var(--bg-hover)] hover:bg-[var(--bg-active)] border border-[var(--bg-hover)] hover:border-[var(--border-strong)] rounded-lg transition-colors cursor-pointer"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 bg-[var(--danger-soft)] border border-[var(--danger-border)] rounded-lg text-sm text-[var(--danger)]">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
          <button onClick={() => setError(null)} className="ml-auto text-[var(--danger)] hover:text-[var(--danger-border)] cursor-pointer">
            ×
          </button>
        </div>
      )}

      {compareIds.length === 2 && comparedVersions.length === 2 && (
        <div className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-[var(--text-primary)]">Version Comparison</h2>
            <button
              onClick={() => setCompareIds([])}
              className="text-xs text-[var(--text-tertiary)] hover:text-[var(--text-primary)] cursor-pointer"
            >
              Clear
            </button>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {comparedVersions.map((v) => (
              <div key={v.id} className="p-4 bg-[var(--bg-app)] border border-[var(--border-default)] rounded-lg space-y-3">
                <div className="font-medium text-[var(--text-primary)]">{v.model_name} v{v.version}</div>
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-[var(--text-tertiary)]">Algorithm</span>
                    <span className="text-[var(--text-secondary)]">{v.algorithm}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[var(--text-tertiary)]">Status</span>
                    <span className={`${
                      v.status === "active" ? "text-[var(--brand)]" : v.status === "training" ? "text-[var(--warning)]" : "text-[var(--text-tertiary)]"
                    }`}>{v.status}</span>
                  </div>
                  {v.metrics && Object.entries(v.metrics).map(([key, val]) => (
                    <div key={key} className="flex justify-between">
                      <span className="text-[var(--text-tertiary)]">{key}</span>
                      <span className="text-[var(--text-secondary)]">{typeof val === "number" ? val.toFixed(4) : String(val)}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl">
        <div className="px-5 py-4 border-b border-[var(--border-default)] flex items-center justify-between">
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">Model Versions</h2>
          <span className="text-xs text-[var(--text-tertiary)]">{versions.length} versions</span>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin h-6 w-6 border-2 border-[var(--brand)] border-t-transparent rounded-full" />
          </div>
        ) : versions.length === 0 ? (
          <div className="text-center py-12 text-[var(--text-tertiary)]">
            <GitBranch className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No model versions found</p>
          </div>
        ) : (
          <div className="divide-y divide-[var(--border-default)]">
            {versions.map((version) => {
              const isExpanded = expandedId === version.id
              const isCompared = compareIds.includes(version.id)
              return (
                <div key={version.id}>
                  <div
                    className={`flex items-center gap-4 px-5 py-3.5 hover:bg-[var(--bg-subtle)] transition-colors ${
                      isCompared ? "bg-[var(--brand-soft)] border-l-2 border-l-[var(--brand)]" : ""
                    }`}
                  >
                    <button
                      onClick={() => toggleExpand(version.id)}
                      className="text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] cursor-pointer"
                    >
                      {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                    </button>

                    <button
                      onClick={() => toggleCompare(version.id)}
                      className={`w-4 h-4 rounded border transition-colors cursor-pointer ${
                        isCompared
                          ? "bg-[var(--brand)] border-[var(--brand)]"
                          : "border-[var(--border-strong)] hover:border-[var(--border-default)]"
                      }`}
                    />

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-[var(--text-primary)]">{version.model_name}</span>
                        <span className="text-xs text-[var(--text-tertiary)]">v{version.version}</span>
                      </div>
                      <p className="text-xs text-[var(--text-tertiary)] mt-0.5">{version.algorithm}</p>
                    </div>

                    <span className={`text-xs px-2 py-0.5 rounded-full border ${
                      version.status === "active"
                        ? "bg-[var(--brand-soft)] text-[var(--brand)] border-[var(--brand-border)]"
                        : version.status === "training"
                          ? "bg-[var(--warning-soft)] text-[var(--warning)] border-[var(--warning-border)]"
                          : "bg-[var(--bg-subtle)] text-[var(--text-tertiary)] border-[var(--border-default)]"
                    }`}>
                      {version.status}
                    </span>

                    <span className="text-xs text-[var(--text-tertiary)]">
                      <Clock className="h-3.5 w-3.5 inline mr-1" />
                      {new Date(version.created_at).toLocaleDateString()}
                    </span>
                  </div>

                  {isExpanded && (
                    <div className="px-5 pb-4 pt-1 bg-[var(--bg-subtle)]">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-3">
                          <div className="p-3 bg-[var(--bg-app)] border border-[var(--border-default)] rounded-lg">
                            <div className="text-xs text-[var(--text-tertiary)] uppercase tracking-wider font-semibold mb-2">Details</div>
                            <div className="space-y-2 text-xs">
                              <div className="flex items-center gap-2">
                                <Hash className="h-3.5 w-3.5 text-[var(--text-tertiary)]" />
                                <span className="text-[var(--text-tertiary)]">ID:</span>
                                <span className="text-[var(--text-secondary)] font-mono">{version.id}</span>
                              </div>
                              {version.sha256 && (
                                <div className="flex items-start gap-2">
                                  <Lock className="h-3.5 w-3.5 text-[var(--text-tertiary)] mt-0.5" />
                                  <div>
                                    <span className="text-[var(--text-tertiary)]">SHA256:</span>
                                    <p className="text-[var(--text-secondary)] font-mono text-[11px] break-all mt-0.5">{version.sha256}</p>
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>

                          {version.metrics && Object.keys(version.metrics).length > 0 && (
                              <div className="p-3 bg-[var(--bg-app)] border border-[var(--border-default)] rounded-lg">
                                <div className="text-xs text-[var(--text-tertiary)] uppercase tracking-wider font-semibold mb-2">Metrics</div>
                                <div className="space-y-1.5">
                                  {Object.entries(version.metrics).map(([key, val]) => (
                                    <div key={key} className="flex justify-between text-xs">
                                      <span className="text-[var(--text-tertiary)]">{key}</span>
                                      <span className="text-[var(--text-secondary)] font-mono">{typeof val === "number" ? val.toFixed(4) : String(val)}</span>
                                    </div>
                                  ))}
                              </div>
                            </div>
                          )}
                        </div>

                        <div className="space-y-3">
                          {version.config && Object.keys(version.config).length > 0 && (
                              <div className="p-3 bg-[var(--bg-app)] border border-[var(--border-default)] rounded-lg">
                                <div className="text-xs text-[var(--text-tertiary)] uppercase tracking-wider font-semibold mb-2">Config</div>
                                <pre className="text-[11px] text-[var(--text-secondary)] font-mono whitespace-pre-wrap overflow-auto max-h-40">
                                {JSON.stringify(version.config, null, 2)}
                              </pre>
                            </div>
                          )}

                          <div className="p-3 bg-[var(--bg-app)] border border-[var(--border-default)] rounded-lg">
                            <div className="text-xs text-[var(--text-tertiary)] uppercase tracking-wider font-semibold mb-3">Actions</div>
                            <div className="flex flex-wrap gap-2">
                              <Button
                                variant="outline"
                                size="sm"
                                loading={verifyingId === version.id}
                                onClick={() => handleVerify(version.model_name, version.id)}
                              >
                                <ShieldCheck className="h-3.5 w-3.5 mr-1.5" />
                                Verify
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                loading={rollingBackId === version.id}
                                onClick={() => handleRollback(version.model_name, version.id)}
                              >
                                <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
                                Rollback
                              </Button>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
