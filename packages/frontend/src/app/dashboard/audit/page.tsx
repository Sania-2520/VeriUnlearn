"use client"

import { useState, useEffect, useCallback, useMemo } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge, statusTone } from "@/components/ui/badge"
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select"
import { SkeletonRows } from "@/components/ui/skeleton"
import { EmptyState, ErrorState } from "@/components/ui/empty-state"
import { PageHeader } from "@/components/ui/page-header"
import { clsx } from "clsx"
import { ShieldCheck, Search } from "lucide-react"
import * as authApi from "@/lib/api/auth"
import type { AuditEvent } from "@/lib/types/auth"
import { formatDate } from "@/lib/utils"

const EVENT_TONE: Record<string, ReturnType<typeof statusTone>> = {
  user_login: "info",
  user_logout: "neutral",
  user_registered: "success",
  email_verified: "success",
  password_changed: "warning",
  password_reset: "warning",
  mfa_enabled: "purple",
  mfa_disabled: "purple",
  mfa_verify: "accent",
  api_key_created: "purple",
  api_key_revoked: "danger",
  unlearning_created: "info",
  unlearning_retry: "warning",
  settings_updated: "warning",
  webhook_created: "info",
  webhook_deleted: "danger",
  permission_denied: "danger",
}

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

function EventRow({ event }: { event: AuditEvent }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div className="overflow-hidden rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] transition-colors hover:border-[var(--border-default)]">
      <button
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        className="flex w-full items-center justify-between gap-3 p-4 text-left transition-colors hover:bg-[var(--bg-hover)]"
      >
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--brand-soft)] text-[var(--brand)]">
            <ShieldCheck className="h-4 w-4" />
          </span>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={EVENT_TONE[event.event_type] ?? "neutral"} dot>
                {event.event_type.replace(/_/g, " ")}
              </Badge>
              <Badge tone={statusTone(event.status)}>{event.status}</Badge>
            </div>
            <p className="mt-1 truncate text-sm text-[var(--text-primary)]">
              <span className="font-medium">{event.action}</span>
              {event.resource.type && (
                <span className="text-[var(--text-secondary)]">
                  {" "}
                  on {event.resource.type}
                  {event.resource.id ? `:${event.resource.id.slice(0, 8)}` : ""}
                </span>
              )}
            </p>
          </div>
        </div>
        <div className="hidden items-center gap-4 text-xs text-[var(--text-tertiary)] sm:flex">
          <span>{formatDate(event.timestamp || event.event_hash)}</span>
          {event.ip_address && <span>{event.ip_address}</span>}
          {event.actor.id && <span>by {event.actor.id.slice(0, 12)}…</span>}
        </div>
        <span className={clsx("text-[var(--text-tertiary)] transition-transform", expanded && "rotate-180")}>▼</span>
      </button>

      {expanded && (
        <div className="border-t border-[var(--border-subtle)] px-4 pb-4 pt-3">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <Detail label="Event ID" value={event.id} mono />
            <Detail label="Version" value={event.event_version} />
            <Detail label="Actor" value={event.actor.id ? `${event.actor.id.slice(0, 16)}… (${event.actor.type})` : "system"} mono />
            <Detail label="Resource" value={event.resource.type || "none"} mono />
            <Detail label="Session ID" value={event.session_id ? `${event.session_id.slice(0, 16)}…` : "—"} mono />
            <Detail label="Request ID" value={event.request_id ? `${event.request_id.slice(0, 16)}…` : "—"} mono />
          </div>

          <div className="mt-4 rounded-lg bg-[var(--bg-subtle)] p-3">
            <p className="mb-2 text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">Chain Hash Verification</p>
            <div className="space-y-2">
              <div>
                <p className="text-xs text-[var(--text-tertiary)]">Previous Hash</p>
                <p className="break-all font-mono text-xs text-[var(--text-secondary)]">
                  {event.previous_event_hash || "— (genesis event)"}
                </p>
              </div>
              <div>
                <p className="text-xs text-[var(--text-tertiary)]">Event Hash</p>
                <p className="break-all font-mono text-xs font-medium text-[var(--info)]">{event.event_hash}</p>
              </div>
            </div>
          </div>

          {event.metadata && Object.keys(event.metadata).length > 0 && (
            <Pre title="Metadata" data={event.metadata} />
          )}
          {event.changes && Object.keys(event.changes).length > 0 && (
            <Pre title="Changes" data={event.changes} />
          )}
        </div>
      )}
    </div>
  )
}

function Detail({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <p className="mb-1 text-xs uppercase tracking-wider text-[var(--text-tertiary)]">{label}</p>
      <p className={clsx("text-xs text-[var(--text-secondary)]", mono && "font-mono break-all")}>{value}</p>
    </div>
  )
}

function Pre({ title, data }: { title: string; data: Record<string, unknown> }) {
  return (
    <div className="mt-3">
      <p className="mb-1 text-xs uppercase tracking-wider text-[var(--text-tertiary)]">{title}</p>
      <pre className="max-h-40 overflow-x-auto rounded-lg bg-[var(--bg-subtle)] p-3 text-xs">
        {JSON.stringify(data, null, 2)}
      </pre>
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

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Audit Log"
        description="Tamper-evident event trail with cryptographic chain verification"
        breadcrumb={[{ label: "Configuration" }, { label: "Audit Log" }]}
        actions={
          <Badge tone="success" dot>
            {total} events
          </Badge>
        }
      />

      <Card>
        <CardContent className="pt-5">
          <div className="mb-4 flex items-center justify-between gap-3">
            <Select value={eventTypeFilter} onValueChange={(v) => { setEventTypeFilter(v); setPage(1) }}>
              <SelectTrigger className="sm:w-56" aria-label="Filter by event type">
                <SelectValue placeholder="All Types" />
              </SelectTrigger>
              <SelectContent>
                {eventTypes.map((t) => (
                  <SelectItem key={t.value} value={t.value}>
                    {t.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {error && <ErrorState title="Couldn't load audit events" description={error} onRetry={loadEvents} className="mb-4" />}

          {loading ? (
            <SkeletonRows rows={8} />
          ) : events.length === 0 ? (
            <EmptyState
              icon={ShieldCheck}
              title="No audit events found"
              description={eventTypeFilter ? "No events match the selected filter." : "Events will appear here as actions are taken across the platform."}
            />
          ) : (
            <div className="space-y-2">
              {events.map((event) => (
                <EventRow key={event.id} event={event} />
              ))}
            </div>
          )}

          {!loading && totalPages > 1 && (
            <div className="mt-6 flex items-center justify-center gap-3">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
                Previous
              </Button>
              <span className="text-sm text-[var(--text-secondary)]">
                Page {page} of {totalPages}
              </span>
              <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
                Next
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
