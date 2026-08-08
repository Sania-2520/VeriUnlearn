"use client"

import { useState, useEffect } from "react"
import { useAuthStore } from "@/lib/store/auth-store"
import { apiRequest } from "@/lib/api/client"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Cpu, Plus, RotateCcw, CheckCircle2, XCircle, Loader2, RefreshCw } from "lucide-react"
import { clsx } from "clsx"

interface Adapter {
  adapter_name: string
  version_count: number
  active_version_id: string | null
  active_version_number: number | null
  status: string
  total_requests: number
  avg_latency_ms: number
}

export default function AdaptersPage() {
  const { user } = useAuthStore()
  const [adapters, setAdapters] = useState<Adapter[]>([])
  const [loading, setLoading] = useState(true)
  const [registering, setRegistering] = useState(false)
  const [newName, setNewName] = useState("")
  const [newPath, setNewPath] = useState("")

  const fetchAdapters = async () => {
    setLoading(true)
    try {
      const data = await apiRequest<Adapter[] | { data: Adapter[] }>("/api/v1/adapters")
      setAdapters(Array.isArray(data) ? data : data.data || [])
    } catch (err) { console.error("Failed to fetch adapters:", err) } finally { setLoading(false) }
  }

  useEffect(() => { fetchAdapters() }, [])

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="animate-spin h-8 w-8 border-4 border-[var(--brand)] border-t-transparent rounded-full" />
      </div>
    )
  }

  const registerAdapter = async () => {
    if (!newName || !newPath) return
    setRegistering(true)
    try {
      await apiRequest("/api/v1/adapters/register", {
        method: "POST",
        body: JSON.stringify({ adapter_name: newName, adapter_path: newPath }),
      })
      setNewName("")
      setNewPath("")
      await fetchAdapters()
    } catch (err) { console.error("Failed to register adapter:", err) } finally { setRegistering(false) }
  }

  const rollback = async (name: string) => {
    try {
      await apiRequest(`/api/v1/adapters/${encodeURIComponent(name)}/rollback`, { method: "POST" })
      await fetchAdapters()
    } catch (err) { console.error("Failed to rollback adapter:", err) }
  }

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto w-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Adapter Lifecycle</h1>
          <p className="text-sm text-[var(--text-tertiary)] mt-1">LoRA adapter registry, versioning, canary deployments, and rollback</p>
        </div>
        <button onClick={fetchAdapters} className="p-2 hover:bg-[var(--bg-hover)] rounded-lg text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"><RefreshCw className="h-4 w-4" /></button>
      </div>

      <Card className="bg-[var(--bg-surface)] border-[var(--border-default)]/50">
        <CardHeader className="border-b border-[var(--border-default)]/30 pb-3">
          <h2 className="text-sm font-semibold text-[var(--text-secondary)]">Register New Adapter</h2>
        </CardHeader>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Adapter name" className="flex-1 px-3 py-2 bg-[var(--bg-app)] border border-[var(--border-default)] rounded-lg text-sm text-[var(--text-secondary)] placeholder-[var(--text-tertiary)] outline-none focus:border-[var(--brand)]" />
            <input value={newPath} onChange={(e) => setNewPath(e.target.value)} placeholder="Adapter path" className="flex-1 px-3 py-2 bg-[var(--bg-app)] border border-[var(--border-default)] rounded-lg text-sm text-[var(--text-secondary)] placeholder-[var(--text-tertiary)] outline-none focus:border-[var(--brand)]" />
            <button onClick={registerAdapter} disabled={registering || !newName || !newPath} className="flex items-center gap-1.5 px-4 py-2 bg-[var(--brand)] hover:bg-[var(--brand-strong)] disabled:bg-[var(--brand)]/50 rounded-lg text-xs font-medium text-[var(--text-on-brand)] transition-colors cursor-pointer">
              {registering ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
              Register
            </button>
          </div>
        </CardContent>
      </Card>

      {loading ? (
        <div className="flex items-center justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-[var(--text-tertiary)]" /></div>
      ) : adapters.length === 0 ? (
        <Card className="bg-[var(--bg-surface)] border-[var(--border-default)]/50">
          <CardContent className="pt-8 pb-8 text-center"><Cpu className="h-8 w-8 text-[var(--text-tertiary)] mx-auto mb-3" /><p className="text-sm text-[var(--text-tertiary)]">No adapters registered yet.</p></CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {adapters.map((a) => (
            <Card key={a.adapter_name} className="bg-[var(--bg-surface)] border-[var(--border-default)]/50">
              <CardContent className="pt-4 pb-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Cpu className="h-5 w-5 text-[var(--brand)]" />
                    <div>
                      <p className="text-sm font-medium text-[var(--text-secondary)]">{a.adapter_name}</p>
                      <p className="text-xs text-[var(--text-tertiary)]">v{a.active_version_number || "-"} · {a.version_count} versions</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-1.5 text-xs">
                      {a.status === "active" ? <CheckCircle2 className="h-3.5 w-3.5 text-[var(--brand)]" /> : <XCircle className="h-3.5 w-3.5 text-[var(--text-tertiary)]" />}
                      <span className={clsx(a.status === "active" ? "text-[var(--brand)]" : "text-[var(--text-secondary)]")}>{a.status}</span>
                    </div>
                    <span className="text-xs text-[var(--text-tertiary)]">{a.total_requests} req · {a.avg_latency_ms.toFixed(1)}ms</span>
                    <button onClick={() => rollback(a.adapter_name)} className="flex items-center gap-1 px-2.5 py-1 bg-[var(--bg-app)] hover:bg-[var(--bg-hover)] border border-[var(--border-default)] rounded-lg text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer">
                      <RotateCcw className="h-3 w-3" /> Rollback
                    </button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
