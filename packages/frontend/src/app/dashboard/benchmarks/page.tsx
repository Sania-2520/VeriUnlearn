"use client"

import { useState } from "react"
import { useAuthStore } from "@/lib/store/auth-store"
import { apiRequest } from "@/lib/api/client"
import { Card, CardHeader, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { PageHeader, StatCard } from "@/components/ui/page-header"
import { SkeletonCards, SkeletonRows } from "@/components/ui/skeleton"
import { EmptyState, ErrorState } from "@/components/ui/empty-state"
import { HelpTip } from "@/components/ui/tooltip"
import {
  FlaskConical,
  Play,
  Loader2,
  CheckCircle2,
  XCircle,
  BarChart3,
  Download,
} from "lucide-react"

interface BenchmarkResult {
  dataset: string
  algorithm: string
  data_size: number
  deletion_fraction: number
  trial: number
  metrics: Record<string, number>
  status: string
}

const ALGO_COLOR: Record<string, string> = {
  sisa: "var(--chart-1)",
  influence: "var(--chart-2)",
  certified_removal: "var(--chart-3)",
  hybrid: "var(--chart-4)",
}
const ALGO_LABEL: Record<string, string> = {
  sisa: "SISA",
  influence: "Influence",
  certified_removal: "Certified",
  hybrid: "Hybrid",
}

function exportData(results: BenchmarkResult[], format: "csv" | "json") {
  if (format === "json") {
    const blob = new Blob([JSON.stringify(results, null, 2)], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "veriunlearn-benchmarks.json"
    a.click()
    URL.revokeObjectURL(url)
    return
  }
  const headers = ["dataset", "algorithm", "data_size", "deletion_fraction", "trial", "status", ...Object.keys(results[0]?.metrics ?? {})]
  const rows = results.map((r) => [
    r.dataset, r.algorithm, r.data_size, r.deletion_fraction, r.trial, r.status,
    ...Object.values(r.metrics).map((v) => (typeof v === "number" ? v.toFixed(4) : v)),
  ])
  const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n")
  const blob = new Blob([csv], { type: "text/csv" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = "veriunlearn-benchmarks.csv"
  a.click()
  URL.revokeObjectURL(url)
}

export default function BenchmarksPage() {
  const { user } = useAuthStore()
  const [results, setResults] = useState<BenchmarkResult[]>([])
  const [running, setRunning] = useState(false)
  const [error, setError] = useState("")
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null)
  const [activeAlgo, setActiveAlgo] = useState<string | null>(null)
  const [hover, setHover] = useState<{ algo: string; value: number; label: string } | null>(null)

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="animate-spin h-8 w-8 border-4 border-[var(--brand)] border-t-transparent rounded-full" />
      </div>
    )
  }

  const runBenchmarks = async () => {
    setRunning(true)
    setError("")
    setResults([])
    try {
      const data = await apiRequest<{ results: BenchmarkResult[] }>("/api/v1/benchmarks/run", {
        method: "POST",
        body: JSON.stringify({ data_sizes: [100, 500], deletion_fractions: [0.05, 0.1], num_trials: 1 }),
      })
      if (data.results) setResults(data.results)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to run benchmarks")
    } finally {
      setRunning(false)
    }
  }

  const fetchSummary = async () => {
    try {
      const data = await apiRequest<Record<string, unknown>>("/api/v1/benchmarks/summary")
      setSummary(data)
    } catch (err) { console.error("Failed to fetch benchmark summary:", err) }
  }

  const completed = results.filter((r) => r.status === "completed")
  const avgUtility = completed.length
    ? completed.reduce((s, r) => s + (r.metrics.utility_retained ?? 0), 0) / completed.length
    : 0

  // Build grouped bars: one group per algorithm, bar height = avg utility retained.
  const byAlgo = new Map<string, number[]>()
  for (const r of completed) {
    if (!byAlgo.has(r.algorithm)) byAlgo.set(r.algorithm, [])
    byAlgo.get(r.algorithm)!.push(r.metrics.utility_retained ?? 0)
  }
  const chartData = Array.from(byAlgo.entries()).map(([algo, vals]) => ({
    algo,
    avg: vals.reduce((a, b) => a + b, 0) / vals.length,
  }))
  const maxVal = Math.max(0.01, ...chartData.map((d) => d.avg))

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Research Benchmarks"
        description="Compare unlearning algorithms across data sizes and deletion fractions"
        breadcrumb={[{ label: "Workspace" }, { label: "Benchmarks" }]}
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={fetchSummary}>
              <BarChart3 className="h-4 w-4" />
              Summary
            </Button>
            <Button size="sm" onClick={runBenchmarks} loading={running}>
              {!running && <Play className="h-4 w-4" />}
              {running ? "Running…" : "Run Benchmarks"}
            </Button>
          </div>
        }
      />

      {error && <ErrorState title="Benchmark run failed" description={error} onRetry={runBenchmarks} />}

      {summary && (
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard label="Total Runs" value={(summary.total_runs as number) || 0} icon={FlaskConical} tone="brand" />
          <StatCard label="Completed" value={(summary.completed as number) || 0} icon={CheckCircle2} tone="success" />
          <StatCard label="Failed" value={(summary.failed as number) || 0} icon={XCircle} tone="danger" />
        </div>
      )}

      <Card>
        <CardHeader
          title="Utility Retained by Algorithm"
          description="Average utility retained after unlearning (higher is better)"
          actions={
            results.length > 0 && (
              <div className="flex items-center gap-1.5">
                <HelpTip text="Exports the current result table as CSV or JSON for your reports.">
                  <Download className="h-4 w-4 text-[var(--text-tertiary)]" />
                </HelpTip>
                <Button variant="ghost" size="sm" onClick={() => exportData(results, "csv")}>
                  <Download className="h-4 w-4" /> CSV
                </Button>
                <Button variant="ghost" size="sm" onClick={() => exportData(results, "json")}>
                  <Download className="h-4 w-4" /> JSON
                </Button>
              </div>
            )
          }
        />
        <CardContent>
          {running ? (
            <div className="space-y-4">
              <SkeletonCards count={3} />
              <SkeletonRows rows={3} />
            </div>
          ) : chartData.length === 0 ? (
            <EmptyState
              icon={BarChart3}
              title="No benchmark results yet"
              description="Run a benchmark suite to compare SISA, Influence, Certified Removal, and Hybrid on utility, forgetting quality, and latency."
            />
          ) : (
            <div>
              <div className="flex h-56 items-end justify-around gap-6 border-b border-[var(--border-subtle)] px-4 pb-0 pt-6">
                {chartData.map((d) => {
                  const isActive = activeAlgo === null || activeAlgo === d.algo
                  return (
                    <button
                      key={d.algo}
                      onMouseEnter={() => { setHover({ algo: d.algo, value: d.avg, label: "Utility retained" }); setActiveAlgo(d.algo) }}
                      onMouseLeave={() => { setHover(null); setActiveAlgo(null) }}
                      onFocus={() => setActiveAlgo(d.algo)}
                      onBlur={() => setActiveAlgo(null)}
                      className="group flex h-full w-full max-w-[80px] flex-col items-center justify-end outline-none"
                      aria-label={`${ALGO_LABEL[d.algo] ?? d.algo}: ${(d.avg * 100).toFixed(1)}% utility retained`}
                    >
                      <span className="mb-2 text-xs font-semibold tabular-nums text-[var(--text-primary)] opacity-0 transition-opacity group-hover:opacity-100 group-focus:opacity-100">
                        {(d.avg * 100).toFixed(1)}%
                      </span>
                      <div
                        className="w-full rounded-t-md transition-all duration-500"
                        style={{
                          height: `${(d.avg / maxVal) * 100}%`,
                          backgroundColor: ALGO_COLOR[d.algo] ?? "var(--chart-5)",
                          opacity: isActive ? 1 : 0.35,
                        }}
                      />
                    </button>
                  )
                })}
              </div>
              <div className="flex justify-around gap-6 px-4 pt-2">
                {chartData.map((d) => (
                  <span key={d.algo} className="max-w-[80px] text-center text-xs font-medium text-[var(--text-secondary)]">
                    {ALGO_LABEL[d.algo] ?? d.algo}
                  </span>
                ))}
              </div>
              {hover && (
                <p className="mt-4 text-center text-xs text-[var(--text-secondary)] animate-fade-up">
                  <span className="font-medium text-[var(--text-primary)]">{ALGO_LABEL[hover.algo] ?? hover.algo}</span>
                  {" · "}
                  {hover.label}: <span className="tabular-nums">{(hover.value * 100).toFixed(2)}%</span>
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {results.length > 0 && (
        <Card>
          <CardHeader title={`Results (${results.length})`} />
          <CardContent className="pt-4">
            <div className="space-y-2">
              {results.map((r, i) => (
                <div
                  key={i}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-subtle)]/40 px-4 py-3 text-sm transition-colors hover:bg-[var(--bg-hover)]"
                >
                  <div className="flex flex-wrap items-center gap-2.5">
                    <Badge tone="purple" dot style={{ color: ALGO_COLOR[r.algorithm] }}>
                      {ALGO_LABEL[r.algorithm] ?? r.algorithm}
                    </Badge>
                    <span className="text-[var(--text-secondary)]">{r.dataset}</span>
                    <span className="text-[var(--text-tertiary)]">·</span>
                    <span className="text-xs text-[var(--text-secondary)]">n={r.data_size} del={r.deletion_fraction}</span>
                  </div>
                  <div className="flex items-center gap-4">
                    {r.status === "completed" ? (
                      <>
                        {r.metrics.utility_retained !== undefined && (
                          <span className="text-xs text-[var(--success)]" title="Utility retained">
                            U={r.metrics.utility_retained.toFixed(3)}
                          </span>
                        )}
                        {r.metrics.processing_time_ms !== undefined && (
                          <span className="text-xs text-[var(--text-secondary)]" title="Processing time">
                            {r.metrics.processing_time_ms.toFixed(0)}ms
                          </span>
                        )}
                        {r.metrics.forgetting_quality !== undefined && (
                          <span className="text-xs text-[var(--info)]" title="Forgetting quality">
                            F={r.metrics.forgetting_quality.toFixed(3)}
                          </span>
                        )}
                        <CheckCircle2 className="h-4 w-4 text-[var(--success)]" />
                      </>
                    ) : (
                      <Badge tone="danger">
                        <XCircle className="h-3.5 w-3.5" /> {r.status}
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {results.length === 0 && !running && !error && (
        <Card>
          <CardContent className="py-10 text-center">
            <p className="text-sm text-[var(--text-secondary)]">
              Tip: combine benchmarks with the Audit Log to evidence SLA-grade deletion guarantees.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
