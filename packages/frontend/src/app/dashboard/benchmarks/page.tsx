"use client"

import { useState } from "react"
import { useAuthStore } from "@/lib/store/auth-store"
import { apiRequest } from "@/lib/api/client"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { FlaskConical, Play, Loader2, CheckCircle2, XCircle, BarChart3 } from "lucide-react"
import { clsx } from "clsx"

interface BenchmarkResult {
  dataset: string
  algorithm: string
  data_size: number
  deletion_fraction: number
  trial: number
  metrics: Record<string, number>
  status: string
}

export default function BenchmarksPage() {
  const { user } = useAuthStore()
  const [results, setResults] = useState<BenchmarkResult[]>([])
  const [running, setRunning] = useState(false)
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null)

  if (!user) return null

  const runBenchmarks = async () => {
    setRunning(true)
    setResults([])
    try {
      const data = await apiRequest<{ results: BenchmarkResult[] }>("/api/v1/benchmarks/run", {
        method: "POST",
        body: JSON.stringify({ data_sizes: [100, 500], deletion_fractions: [0.05, 0.1], num_trials: 1 }),
      })
      if (data.results) setResults(data.results)
    } catch { /* ignore */ } finally { setRunning(false) }
  }

  const fetchSummary = async () => {
    try {
      const data = await apiRequest<Record<string, unknown>>("/api/v1/benchmarks/summary")
      setSummary(data)
    } catch { /* ignore */ }
  }

  const algoColors: Record<string, string> = { sisa: "text-blue-400", influence: "text-purple-400", certified_removal: "text-amber-400", hybrid: "text-emerald-400" }

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto w-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-100">Research Benchmarks</h1>
          <p className="text-sm text-gray-500 mt-1">Compare unlearning algorithms across data sizes and deletion fractions</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={fetchSummary} className="px-3 py-1.5 bg-[#171717] border border-[#2f2f2f] rounded-lg text-xs text-gray-400 hover:text-white transition-colors cursor-pointer"><BarChart3 className="h-3.5 w-3.5 inline mr-1" />Summary</button>
          <button onClick={runBenchmarks} disabled={running} className="flex items-center gap-1.5 px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-600/50 rounded-lg text-xs font-medium text-white transition-colors cursor-pointer">
            {running ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
            {running ? "Running..." : "Run Benchmarks"}
          </button>
        </div>
      </div>

      {summary && (
        <Card className="bg-[#171717] border-[#2f2f2f]/50">
          <CardHeader className="border-b border-[#2f2f2f]/30 pb-3"><h2 className="text-sm font-semibold text-gray-200">Summary</h2></CardHeader>
          <CardContent className="pt-4 grid grid-cols-3 gap-4">
            <div className="bg-[#212121] rounded-xl p-3 border border-[#2f2f2f]/30">
              <p className="text-xs text-gray-500">Total Runs</p><p className="text-lg font-semibold text-gray-200">{summary.total_runs as number || 0}</p></div>
            <div className="bg-[#212121] rounded-xl p-3 border border-[#2f2f2f]/30">
              <p className="text-xs text-gray-500">Completed</p><p className="text-lg font-semibold text-emerald-400">{summary.completed as number || 0}</p></div>
            <div className="bg-[#212121] rounded-xl p-3 border border-[#2f2f2f]/30">
              <p className="text-xs text-gray-500">Failed</p><p className="text-lg font-semibold text-red-400">{summary.failed as number || 0}</p></div>
          </CardContent>
        </Card>
      )}

      {results.length > 0 && (
        <Card className="bg-[#171717] border-[#2f2f2f]/50">
          <CardHeader className="border-b border-[#2f2f2f]/30 pb-3"><h2 className="text-sm font-semibold text-gray-200">Results ({results.length})</h2></CardHeader>
          <CardContent className="pt-4 space-y-2">
            {results.map((r, i) => (
              <div key={i} className="flex items-center justify-between bg-[#212121] rounded-xl p-3 border border-[#2f2f2f]/30 text-sm">
                <div className="flex items-center gap-3">
                  <span className={clsx("text-xs font-mono font-medium", algoColors[r.algorithm] || "text-gray-300")}>{r.algorithm}</span>
                  <span className="text-gray-500">|</span>
                  <span className="text-xs text-gray-400">{r.dataset}</span>
                  <span className="text-gray-500">|</span>
                  <span className="text-xs text-gray-400">n={r.data_size} del={r.deletion_fraction}</span>
                </div>
                <div className="flex items-center gap-4">
                  {r.status === "completed" ? (
                    <>
                      {r.metrics.utility_retained !== undefined && <span className="text-xs text-emerald-400">U={r.metrics.utility_retained.toFixed(3)}</span>}
                      {r.metrics.processing_time_ms !== undefined && <span className="text-xs text-gray-400">{r.metrics.processing_time_ms.toFixed(0)}ms</span>}
                      {r.metrics.forgetting_quality !== undefined && <span className="text-xs text-blue-400">F={r.metrics.forgetting_quality.toFixed(3)}</span>}
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                    </>
                  ) : (
                    <XCircle className="h-3.5 w-3.5 text-red-500" />
                  )}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {results.length === 0 && !running && (
        <Card className="bg-[#171717] border-[#2f2f2f]/50">
          <CardContent className="pt-8 pb-8 text-center"><FlaskConical className="h-8 w-8 text-gray-600 mx-auto mb-3" /><p className="text-sm text-gray-500">No benchmark results yet.</p></CardContent>
        </Card>
      )}
    </div>
  )
}
