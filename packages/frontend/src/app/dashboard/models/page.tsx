"use client"

import { useEffect, useState, useCallback } from "react"
import { Button } from "@/components/ui/button"
import {
  listModelVersions,
  getModelVersion,
  rollbackVersion,
  verifyVersion,
} from "@/lib/api/client"
import {
  GitBranch,
  ShieldCheck,
  RotateCcw,
  CheckCircle,
  Archive,
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
          <h1 className="text-2xl font-bold text-white">Model Registry</h1>
          <p className="text-sm text-gray-400 mt-1">Manage model versions, verify integrity, and rollback</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={filterModel}
            onChange={(e) => setFilterModel(e.target.value)}
            className="px-3 py-2 text-sm bg-[#212121] border border-[#2f2f2f] focus:border-gray-500 rounded-lg text-gray-300 focus:outline-none appearance-none cursor-pointer"
          >
            <option value="">All Models</option>
            {modelNames.map((name) => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
          <button
            onClick={fetchVersions}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-300 hover:text-white bg-[#2f2f2f] hover:bg-[#3a3a3a] border border-[#2f2f2f] hover:border-gray-500 rounded-lg transition-colors cursor-pointer"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-950/30 border border-red-900/40 rounded-lg text-sm text-red-400">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
          <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-300 cursor-pointer">
            ×
          </button>
        </div>
      )}

      {compareIds.length === 2 && comparedVersions.length === 2 && (
        <div className="bg-[#171717] border border-[#2f2f2f]/60 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-200">Version Comparison</h2>
            <button
              onClick={() => setCompareIds([])}
              className="text-xs text-gray-400 hover:text-white cursor-pointer"
            >
              Clear
            </button>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {comparedVersions.map((v) => (
              <div key={v.id} className="p-4 bg-[#212121] border border-[#2f2f2f] rounded-lg space-y-3">
                <div className="font-medium text-gray-200">{v.model_name} v{v.version}</div>
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Algorithm</span>
                    <span className="text-gray-300">{v.algorithm}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Status</span>
                    <span className={`${
                      v.status === "active" ? "text-emerald-400" : v.status === "training" ? "text-yellow-400" : "text-gray-400"
                    }`}>{v.status}</span>
                  </div>
                  {v.metrics && Object.entries(v.metrics).map(([key, val]) => (
                    <div key={key} className="flex justify-between">
                      <span className="text-gray-500">{key}</span>
                      <span className="text-gray-300">{typeof val === "number" ? val.toFixed(4) : String(val)}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-[#171717] border border-[#2f2f2f]/60 rounded-xl">
        <div className="px-5 py-4 border-b border-[#2f2f2f]/40 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-200">Model Versions</h2>
          <span className="text-xs text-gray-500">{versions.length} versions</span>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin h-6 w-6 border-2 border-emerald-500 border-t-transparent rounded-full" />
          </div>
        ) : versions.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <GitBranch className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No model versions found</p>
          </div>
        ) : (
          <div className="divide-y divide-[#2f2f2f]/40">
            {versions.map((version) => {
              const isExpanded = expandedId === version.id
              const isCompared = compareIds.includes(version.id)
              return (
                <div key={version.id}>
                  <div
                    className={`flex items-center gap-4 px-5 py-3.5 hover:bg-[#212121]/50 transition-colors ${
                      isCompared ? "bg-emerald-950/10 border-l-2 border-l-emerald-500" : ""
                    }`}
                  >
                    <button
                      onClick={() => toggleExpand(version.id)}
                      className="text-gray-500 hover:text-gray-300 cursor-pointer"
                    >
                      {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                    </button>

                    <button
                      onClick={() => toggleCompare(version.id)}
                      className={`w-4 h-4 rounded border transition-colors cursor-pointer ${
                        isCompared
                          ? "bg-emerald-500 border-emerald-500"
                          : "border-gray-600 hover:border-gray-400"
                      }`}
                    />

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-200">{version.model_name}</span>
                        <span className="text-xs text-gray-500">v{version.version}</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5">{version.algorithm}</p>
                    </div>

                    <span className={`text-xs px-2 py-0.5 rounded-full border ${
                      version.status === "active"
                        ? "bg-emerald-950/30 text-emerald-400 border-emerald-900/40"
                        : version.status === "training"
                          ? "bg-yellow-950/30 text-yellow-400 border-yellow-900/40"
                          : "bg-gray-900/30 text-gray-400 border-gray-700/40"
                    }`}>
                      {version.status}
                    </span>

                    <span className="text-xs text-gray-500">
                      <Clock className="h-3.5 w-3.5 inline mr-1" />
                      {new Date(version.created_at).toLocaleDateString()}
                    </span>
                  </div>

                  {isExpanded && (
                    <div className="px-5 pb-4 pt-1 bg-[#212121]/30">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-3">
                          <div className="p-3 bg-[#212121] border border-[#2f2f2f] rounded-lg">
                            <div className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-2">Details</div>
                            <div className="space-y-2 text-xs">
                              <div className="flex items-center gap-2">
                                <Hash className="h-3.5 w-3.5 text-gray-400" />
                                <span className="text-gray-500">ID:</span>
                                <span className="text-gray-300 font-mono">{version.id}</span>
                              </div>
                              {version.sha256 && (
                                <div className="flex items-start gap-2">
                                  <Lock className="h-3.5 w-3.5 text-gray-400 mt-0.5" />
                                  <div>
                                    <span className="text-gray-500">SHA256:</span>
                                    <p className="text-gray-300 font-mono text-[11px] break-all mt-0.5">{version.sha256}</p>
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>

                          {version.metrics && Object.keys(version.metrics).length > 0 && (
                            <div className="p-3 bg-[#212121] border border-[#2f2f2f] rounded-lg">
                              <div className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-2">Metrics</div>
                              <div className="space-y-1.5">
                                {Object.entries(version.metrics).map(([key, val]) => (
                                  <div key={key} className="flex justify-between text-xs">
                                    <span className="text-gray-500">{key}</span>
                                    <span className="text-gray-300 font-mono">{typeof val === "number" ? val.toFixed(4) : String(val)}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>

                        <div className="space-y-3">
                          {version.config && Object.keys(version.config).length > 0 && (
                            <div className="p-3 bg-[#212121] border border-[#2f2f2f] rounded-lg">
                              <div className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-2">Config</div>
                              <pre className="text-[11px] text-gray-300 font-mono whitespace-pre-wrap overflow-auto max-h-40">
                                {JSON.stringify(version.config, null, 2)}
                              </pre>
                            </div>
                          )}

                          <div className="p-3 bg-[#212121] border border-[#2f2f2f] rounded-lg">
                            <div className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-3">Actions</div>
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
