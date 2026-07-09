"use client"

import { useState, useEffect, useCallback } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { clsx } from "clsx"
import * as authApi from "@/lib/api/auth"
import type { AuditEvent } from "@/lib/types/auth"
import { formatDate } from "@/lib/utils"

const eventColors: Record<string, string> = {
  user_login: "bg-blue-100 text-blue-700",
  user_logout: "bg-gray-100 text-gray-700",
  user_registered: "bg-green-100 text-green-700",
  email_verified: "bg-teal-100 text-teal-700",
  password_changed: "bg-orange-100 text-orange-700",
  password_reset: "bg-orange-100 text-orange-700",
  mfa_enabled: "bg-purple-100 text-purple-700",
  mfa_disabled: "bg-purple-100 text-purple-700",
  mfa_verify: "bg-indigo-100 text-indigo-700",
  api_key_created: "bg-pink-100 text-pink-700",
  api_key_revoked: "bg-pink-100 text-pink-700",
  unlearning_created: "bg-cyan-100 text-cyan-700",
  unlearning_retry: "bg-cyan-100 text-cyan-700",
  settings_updated: "bg-amber-100 text-amber-700",
  webhook_created: "bg-sky-100 text-sky-700",
  webhook_deleted: "bg-sky-100 text-sky-700",
  permission_denied: "bg-red-100 text-red-700",
}

function getEventColor(eventType: string): string {
  return eventColors[eventType] || "bg-gray-100 text-gray-700"
}

function EventRow({ event }: { event: AuditEvent }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="border border-gray-200 rounded-lg">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-50 transition-colors"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={clsx("text-xs px-2 py-0.5 rounded-full font-medium", getEventColor(event.event_type))}>
              {event.event_type.replace(/_/g, " ")}
            </span>
            <span className={clsx(
              "text-xs px-2 py-0.5 rounded-full",
              event.status === "success" ? "bg-green-100 text-green-700" :
              event.status === "denied" ? "bg-red-100 text-red-700" :
              "bg-gray-100 text-gray-600"
            )}>
              {event.status}
            </span>
          </div>
          <p className="text-sm text-gray-900 mt-1">
            <span className="font-medium">{event.action}</span>
            {event.resource.type && (
              <span className="text-gray-500"> on {event.resource.type}{event.resource.id ? `:${event.resource.id.slice(0, 8)}` : ""}</span>
            )}
          </p>
          <div className="flex items-center gap-3 mt-1">
            <p className="text-xs text-gray-500">{formatDate(event.timestamp || event.event_hash)}</p>
            {event.ip_address && <p className="text-xs text-gray-400">{event.ip_address}</p>}
            {event.actor.id && <p className="text-xs text-gray-400">by {event.actor.id.slice(0, 12)}...</p>}
          </div>
        </div>
        <span className={clsx(
          "text-gray-400 transition-transform ml-4",
          expanded && "rotate-180"
        )}>▼</span>
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t border-gray-100 pt-3">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Event ID</p>
              <p className="font-mono text-xs break-all">{event.id}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Version</p>
              <p className="text-xs">{event.event_version}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Actor</p>
              <p className="text-xs">
                {event.actor.id ? `${event.actor.id.slice(0, 16)}...` : "system"}
                <span className="text-gray-400"> ({event.actor.type})</span>
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Resource</p>
              <p className="text-xs">
                {event.resource.type || "none"}
                {event.resource.id && <span className="text-gray-400"> / {event.resource.id.slice(0, 12)}...</span>}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Session ID</p>
              <p className="font-mono text-xs">{event.session_id ? `${event.session_id.slice(0, 16)}...` : "—"}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Request ID</p>
              <p className="font-mono text-xs">{event.request_id ? `${event.request_id.slice(0, 16)}...` : "—"}</p>
            </div>
          </div>

          {/* Chain Hashes */}
          <div className="mt-4 p-3 bg-gray-50 rounded-lg">
            <p className="text-xs font-medium text-gray-700 mb-2">Chain Hash Verification</p>
            <div className="space-y-2">
              <div>
                <p className="text-xs text-gray-500">Previous Hash</p>
                <p className="font-mono text-xs break-all text-gray-700">
                  {event.previous_event_hash || "— (genesis event)"}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Event Hash</p>
                <p className="font-mono text-xs break-all text-blue-700 font-medium">{event.event_hash}</p>
              </div>
            </div>
          </div>

          {/* Metadata */}
          {event.metadata && Object.keys(event.metadata).length > 0 && (
            <div className="mt-3">
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Metadata</p>
              <pre className="text-xs bg-gray-50 p-3 rounded-lg overflow-x-auto max-h-40">
                {JSON.stringify(event.metadata, null, 2)}
              </pre>
            </div>
          )}

          {/* Changes */}
          {event.changes && Object.keys(event.changes).length > 0 && (
            <div className="mt-3">
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Changes</p>
              <pre className="text-xs bg-gray-50 p-3 rounded-lg overflow-x-auto max-h-40">
                {JSON.stringify(event.changes, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [eventTypeFilter, setEventTypeFilter] = useState("")

  const loadEvents = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const params: Record<string, unknown> = { page, page_size: 20 }
      if (eventTypeFilter) params.event_type = eventTypeFilter
      const res = await authApi.getAuditEvents(params as { event_type?: string; page?: number; page_size?: number })
      setEvents(res.data)
      setTotal(res.meta.total)
      setTotalPages(Math.ceil(res.meta.total / res.meta.page_size))
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load audit events")
    } finally {
      setLoading(false)
    }
  }, [page, eventTypeFilter])

  useEffect(() => { loadEvents() }, [loadEvents])

  const eventTypes = [
    { value: "", label: "All Types" },
    { value: "user_login", label: "Login" },
    { value: "user_logout", label: "Logout" },
    { value: "user_registered", label: "Registration" },
    { value: "email_verified", label: "Email Verified" },
    { value: "password_changed", label: "Password Changed" },
    { value: "password_reset", label: "Password Reset" },
    { value: "mfa_enabled", label: "MFA Enabled" },
    { value: "mfa_disabled", label: "MFA Disabled" },
    { value: "api_key_created", label: "API Key Created" },
    { value: "api_key_revoked", label: "API Key Revoked" },
    { value: "unlearning_created", label: "Unlearning Created" },
    { value: "unlearning_retry", label: "Unlearning Retry" },
    { value: "settings_updated", label: "Settings Updated" },
    { value: "webhook_created", label: "Webhook Created" },
    { value: "webhook_deleted", label: "Webhook Deleted" },
    { value: "permission_denied", label: "Permission Denied" },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Audit Log</h1>
        <p className="text-sm text-gray-500 mt-1">
          Tamper-evident event trail with cryptographic chain verification
        </p>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <select
                value={eventTypeFilter}
                onChange={(e) => { setEventTypeFilter(e.target.value); setPage(1) }}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm bg-white"
              >
                {eventTypes.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            <p className="text-sm text-gray-500">{total} total events</p>
          </div>

          {error && <p className="text-sm text-red-600 mb-4">{error}</p>}

          {loading ? (
            <p className="text-sm text-gray-500 py-8 text-center">Loading...</p>
          ) : events.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500 font-medium">No audit events found</p>
              <p className="text-sm text-gray-400 mt-1">
                {eventTypeFilter ? "No events match the selected filter" : "Events will appear here as actions are taken"}
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {events.map((event) => (
                <EventRow key={event.id} event={event} />
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
