"use client"

import { useState, useEffect, useCallback, useMemo } from "react"
import Link from "next/link"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge, statusTone } from "@/components/ui/badge"
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select"
import { SkeletonRows } from "@/components/ui/skeleton"
import { EmptyState, ErrorState } from "@/components/ui/empty-state"
import { HelpTip } from "@/components/ui/tooltip"
import { PageHeader } from "@/components/ui/page-header"
import { clsx } from "clsx"
import { Search, Trash2, Plus, AlertCircle, ShieldCheck } from "lucide-react"
import * as unlearningApi from "@/lib/api/unlearning"
import type { UnlearningRequest } from "@/lib/types/unlearning"
import { formatDate } from "@/lib/utils"

const PRIORITY_TONE: Record<string, "neutral" | "info" | "warning" | "danger"> = {
  low: "neutral",
  medium: "info",
  high: "warning",
  critical: "danger",
}

export default function UnlearningPage() {
  const [requests, setRequests] = useState<UnlearningRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [statusFilter, setStatusFilter] = useState("")
  const [query, setQuery] = useState("")

  const loadRequests = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const params: Record<string, unknown> = { page, page_size: 10 }
      if (statusFilter) params.status = statusFilter
      const res = await unlearningApi.listRequests(params as Parameters<typeof unlearningApi.listRequests>[0])
      setRequests(res.data)
      setTotal(res.meta.total)
      setTotalPages(res.meta.total_pages)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load requests")
    } finally {
      setLoading(false)
    }
  }, [page, statusFilter])

  useEffect(() => { loadRequests() }, [loadRequests])

  const filtered = useMemo(() => {
    if (!query.trim()) return requests
    const q = query.toLowerCase()
    return requests.filter(
      (r) =>
        r.id.toLowerCase().includes(q) ||
        (r.algorithm ?? "").toLowerCase().includes(q) ||
        r.status.toLowerCase().includes(q),
    )
  }, [requests, query])

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Unlearning Requests"
        description="Manage data deletion and right-to-be-forgotten requests"
        breadcrumb={[{ label: "Workspace" }, { label: "Unlearning" }]}
        actions={
          <Link href="/dashboard/unlearning/new">
            <Button>
              <Plus className="h-4 w-4" />
              New Request
            </Button>
          </Link>
        }
      />

      <Card>
        <CardContent className="pt-5">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-1 flex-col gap-3 sm:flex-row sm:items-center">
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search by ID, algorithm, or status"
                leftIcon={<Search className="h-4 w-4" />}
                className="sm:max-w-xs"
                aria-label="Search unlearning requests"
              />
              <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(1) }}>
                <SelectTrigger className="sm:w-48" aria-label="Filter by status">
                  <SelectValue placeholder="All statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All statuses</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="in_progress">In Progress</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                  <SelectItem value="retrying">Retrying</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <HelpTip text="Requests trigger an unlearning job, then cryptographic verification. Filter by lifecycle status to triage faster.">
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-[var(--border-default)] text-[var(--text-tertiary)]">
                <AlertCircle className="h-4 w-4" />
              </span>
            </HelpTip>
          </div>

          {error && <ErrorState title="Couldn't load requests" description={error} onRetry={loadRequests} className="mb-4" />}

          {loading ? (
            <SkeletonRows rows={6} />
          ) : requests.length === 0 ? (
            <EmptyState
              icon={Trash2}
              title="No unlearning requests yet"
              description="Create your first deletion request to start proving verifiable forgetfulness."
              action="Create Request"
              actionHref="/dashboard/unlearning/new"
            />
          ) : filtered.length === 0 ? (
            <EmptyState icon={Search} title="No matches" description="No requests match your search or filter." />
          ) : (
            <div className="divide-y divide-[var(--border-subtle)]">
              {filtered.map((req) => (
                <Link
                  key={req.id}
                  href={`/dashboard/unlearning/${req.id}`}
                  className="group flex items-center justify-between gap-4 px-2 py-3.5 transition-colors hover:bg-[var(--bg-hover)] sm:px-3"
                >
                  <div className="flex min-w-0 flex-1 items-center gap-3">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--brand-soft)] text-[var(--brand)]">
                      <Trash2 className="h-4 w-4" />
                    </span>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="truncate text-sm font-medium">
                          {req.target_data_ids.length} record{req.target_data_ids.length !== 1 ? "s" : ""}
                        </p>
                        <Badge tone={statusTone(req.status)} dot>
                          {req.status.replace(/_/g, " ")}
                        </Badge>
                        <Badge tone={PRIORITY_TONE[req.priority] ?? "neutral"}>
                          {req.priority}
                        </Badge>
                      </div>
                      <p className="mt-1 truncate text-xs text-[var(--text-secondary)]">
                        {req.algorithm ? `Algorithm: ${req.algorithm}` : "Algorithm: pending"}
                        {" · "}
                        {formatDate(req.created_at)}
                        {req.completed_at && ` · Completed ${formatDate(req.completed_at)}`}
                      </p>
                    </div>
                  </div>
                  <span className="text-[var(--text-tertiary)] transition-transform group-hover:translate-x-0.5">→</span>
                </Link>
              ))}
            </div>
          )}

          {!loading && totalPages > 1 && (
            <div className="mt-6 flex items-center justify-center gap-3">
              <Button
                variant="outline" size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <span className="text-sm text-[var(--text-secondary)]">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="outline" size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
