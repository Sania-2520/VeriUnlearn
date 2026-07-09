"use client"

import { useState, useEffect, useCallback } from "react"
import Link from "next/link"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { clsx } from "clsx"
import * as unlearningApi from "@/lib/api/unlearning"
import type { UnlearningRequest } from "@/lib/types/unlearning"
import { formatDate } from "@/lib/utils"

const statusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-700",
  in_progress: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  retrying: "bg-orange-100 text-orange-700",
}

const priorityColors: Record<string, string> = {
  low: "bg-gray-100 text-gray-600",
  medium: "bg-blue-50 text-blue-600",
  high: "bg-orange-50 text-orange-600",
  critical: "bg-red-50 text-red-600",
}

export default function UnlearningPage() {
  const [requests, setRequests] = useState<UnlearningRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [statusFilter, setStatusFilter] = useState("")

  const loadRequests = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const params: Record<string, unknown> = { page, page_size: 10 }
      if (statusFilter) params.status = statusFilter
      const res = await unlearningApi.listRequests(params as Parameters<typeof unlearningApi.listRequests>[0])
      setRequests(res.data)
      setTotalPages(res.meta.total_pages)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load requests")
    } finally {
      setLoading(false)
    }
  }, [page, statusFilter])

  useEffect(() => { loadRequests() }, [loadRequests])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Unlearning Requests</h1>
          <p className="text-sm text-gray-500 mt-1">Manage data deletion and right-to-be-forgotten requests</p>
        </div>
        <Link href="/dashboard/unlearning/new">
          <Button>New Request</Button>
        </Link>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-3 mb-4">
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm bg-white"
            >
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="in_progress">In Progress</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
              <option value="retrying">Retrying</option>
            </select>
          </div>

          {error && <p className="text-sm text-red-600 mb-4">{error}</p>}

          {loading ? (
            <p className="text-sm text-gray-500 py-8 text-center">Loading...</p>
          ) : requests.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500 font-medium">No unlearning requests yet</p>
              <p className="text-sm text-gray-400 mt-1">Create your first deletion request to get started</p>
              <Link href="/dashboard/unlearning/new">
                <Button className="mt-4">Create Request</Button>
              </Link>
            </div>
          ) : (
            <div className="space-y-3">
              {requests.map((req) => (
                <Link key={req.id} href={`/dashboard/unlearning/${req.id}`}>
                  <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-blue-50 transition-colors cursor-pointer">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium truncate">
                          {req.target_data_ids.length} record{req.target_data_ids.length !== 1 ? "s" : ""}
                        </p>
                        <span className={clsx("text-xs px-2 py-0.5 rounded-full", statusColors[req.status])}>
                          {req.status.replace("_", " ")}
                        </span>
                        <span className={clsx("text-xs px-2 py-0.5 rounded-full", priorityColors[req.priority])}>
                          {req.priority}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        {req.algorithm ? `Algorithm: ${req.algorithm}` : "Algorithm: pending"}
                        {" · "}
                        {formatDate(req.created_at)}
                        {req.completed_at && ` · Completed ${formatDate(req.completed_at)}`}
                      </p>
                    </div>
                    <span className="text-gray-400 ml-4">→</span>
                  </div>
                </Link>
              ))}
            </div>
          )}

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-6">
              <Button
                variant="outline" size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <span className="text-sm text-gray-500">
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
