"use client"

import { useState, useEffect, useCallback } from "react"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { clsx } from "clsx"
import * as webhookApi from "@/lib/api/webhooks"
import type { Webhook, WebhookEventLog, WebhookTestResult } from "@/lib/types/webhooks"
import { formatDate } from "@/lib/utils"

const statusColors: Record<string, string> = {
  active: "bg-green-100 text-green-700",
  failing: "bg-red-100 text-red-700",
  disabled: "bg-gray-100 text-gray-600",
}

const eventOptions = [
  "unlearning.completed",
  "unlearning.failed",
  "verification.completed",
  "privacy.evaluation.ready",
  "certificate.generated",
  "settings.updated",
  "audit.event.created",
]

function WebhookForm({
  initial,
  onSave,
  onCancel,
  saving,
}: {
  initial?: Partial<Webhook>
  onSave: (data: { name: string; url: string; events: string[]; retry_count: number; timeout_ms: number }) => void
  onCancel: () => void
  saving: boolean
}) {
  const [name, setName] = useState(initial?.name || "")
  const [url, setUrl] = useState(initial?.url || "")
  const [events, setEvents] = useState<string[]>(initial?.events || [])
  const [retryCount, setRetryCount] = useState(initial?.retry_count ?? 3)
  const [timeoutMs, setTimeoutMs] = useState(initial?.timeout_ms ?? 5000)
  const [error, setError] = useState("")

  const toggleEvent = (event: string) => {
    setEvents((prev) =>
      prev.includes(event) ? prev.filter((e) => e !== event) : [...prev, event]
    )
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) { setError("Name is required"); return }
    if (!url.trim()) { setError("URL is required"); return }
    if (events.length === 0) { setError("Select at least one event"); return }
    setError("")
    onSave({ name: name.trim(), url: url.trim(), events, retry_count: retryCount, timeout_ms: timeoutMs })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Input id="wh-name" label="Webhook Name" value={name} onChange={(e) => setName(e.target.value)} placeholder="My Webhook" required />
      <Input id="wh-url" label="Endpoint URL" type="url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://example.com/webhook" required />

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Subscribe to Events</label>
        <div className="grid grid-cols-2 gap-2">
          {eventOptions.map((event) => (
            <label key={event} className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={events.includes(event)}
                onChange={() => toggleEvent(event)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              {event}
            </label>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Input id="wh-retry" label="Max Retries" type="number" min={1} max={10}
          value={retryCount} onChange={(e) => setRetryCount(Number(e.target.value))} />
        <Input id="wh-timeout" label="Timeout (ms)" type="number" min={1000} max={30000}
          value={timeoutMs} onChange={(e) => setTimeoutMs(Number(e.target.value))} />
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex gap-3">
        <Button type="submit" loading={saving}>{initial?.id ? "Update" : "Create"} Webhook</Button>
        <Button type="button" variant="outline" onClick={onCancel}>Cancel</Button>
      </div>
    </form>
  )
}

function LogViewer({ webhookId, onClose }: { webhookId: string; onClose: () => void }) {
  const [logs, setLogs] = useState<WebhookEventLog[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    webhookApi.getWebhookLogs(webhookId, { page_size: 50 }).then((res) => {
      setLogs(res.data)
    }).catch(() => {}).finally(() => setLoading(false))
  }, [webhookId])

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-sm font-semibold">Delivery Logs</h4>
        <Button variant="ghost" size="sm" onClick={onClose}>Close</Button>
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Loading...</p>
      ) : logs.length === 0 ? (
        <p className="text-sm text-gray-500">No delivery logs yet</p>
      ) : (
        <div className="space-y-2 max-h-80 overflow-y-auto">
          {logs.map((log) => (
            <div key={log.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg text-sm">
              <div>
                <p className="font-medium text-xs">{log.event_type}</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  Attempt {log.attempt_count}/{log.max_attempts}
                  {log.response_code && ` · HTTP ${log.response_code}`}
                  {" · "}{formatDate(log.created_at)}
                </p>
              </div>
              <span className={clsx(
                "text-xs px-2 py-0.5 rounded-full",
                log.status === "delivered" ? "bg-green-100 text-green-700" :
                log.status === "failed" ? "bg-red-100 text-red-700" :
                "bg-yellow-100 text-yellow-700"
              )}>
                {log.status}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function WebhooksPage() {
  const [webhooks, setWebhooks] = useState<Webhook[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<Webhook | null>(null)
  const [saving, setSaving] = useState(false)
  const [testingId, setTestingId] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<WebhookTestResult | null>(null)
  const [logsWebhookId, setLogsWebhookId] = useState<string | null>(null)

  const loadWebhooks = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const res = await webhookApi.listWebhooks()
      setWebhooks(res.data)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load webhooks")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadWebhooks() }, [loadWebhooks])

  const handleCreate = async (data: { name: string; url: string; events: string[]; retry_count: number; timeout_ms: number }) => {
    setSaving(true)
    try {
      await webhookApi.createWebhook(data)
      setShowForm(false)
      await loadWebhooks()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create webhook")
    } finally {
      setSaving(false)
    }
  }

  const handleUpdate = async (data: { name: string; url: string; events: string[]; retry_count: number; timeout_ms: number }) => {
    if (!editing) return
    setSaving(true)
    try {
      await webhookApi.updateWebhook(editing.id, data)
      setEditing(null)
      await loadWebhooks()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to update webhook")
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (webhookId: string) => {
    if (!confirm("Delete this webhook? This cannot be undone.")) return
    try {
      await webhookApi.deleteWebhook(webhookId)
      await loadWebhooks()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to delete webhook")
    }
  }

  const handleTest = async (webhookId: string) => {
    setTestingId(webhookId)
    setTestResult(null)
    try {
      const result = await webhookApi.testWebhook(webhookId)
      setTestResult(result)
      await loadWebhooks()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Test failed")
    } finally {
      setTestingId(null)
    }
  }

  const handleToggleActive = async (webhook: Webhook) => {
    try {
      await webhookApi.updateWebhook(webhook.id, { is_active: !webhook.is_active })
      await loadWebhooks()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to toggle webhook")
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Webhooks</h1>
          <p className="text-sm text-gray-500 mt-1">Manage outgoing webhook endpoints for event notifications</p>
        </div>
        <Button onClick={() => { setShowForm(true); setEditing(null) }}>Add Webhook</Button>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {/* Test Result Toast */}
      {testResult && (
        <Card className={testResult.success ? "border-green-200 bg-green-50" : "border-red-200 bg-red-50"}>
          <CardContent className="flex items-center justify-between py-3">
            <div>
              <p className={clsx("text-sm font-medium", testResult.success ? "text-green-700" : "text-red-700")}>
                {testResult.success ? "✓ Webhook test successful" : "✗ Webhook test failed"}
              </p>
              <p className="text-xs text-gray-600 mt-0.5">
                {testResult.status_code && `HTTP ${testResult.status_code} · `}
                {testResult.duration_ms !== null && `${testResult.duration_ms}ms`}
                {testResult.error && ` · ${testResult.error}`}
              </p>
            </div>
            <Button variant="ghost" size="sm" onClick={() => setTestResult(null)}>Dismiss</Button>
          </CardContent>
        </Card>
      )}

      {/* Create/Edit Form */}
      {(showForm || editing) && (
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold">{editing ? "Edit Webhook" : "New Webhook"}</h3>
          </CardHeader>
          <CardContent>
            <WebhookForm
              initial={editing || undefined}
              onSave={editing ? handleUpdate : handleCreate}
              onCancel={() => { setShowForm(false); setEditing(null) }}
              saving={saving}
            />
          </CardContent>
        </Card>
      )}

      {/* Log Panel */}
      {logsWebhookId && (
        <Card>
          <CardContent className="pt-6">
            <LogViewer webhookId={logsWebhookId} onClose={() => setLogsWebhookId(null)} />
          </CardContent>
        </Card>
      )}

      {/* Webhook List */}
      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <p className="text-sm text-gray-500 py-8 text-center">Loading...</p>
          ) : webhooks.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500 font-medium">No webhooks configured</p>
              <p className="text-sm text-gray-400 mt-1">Create a webhook to receive event notifications</p>
              <Button className="mt-4" onClick={() => setShowForm(true)}>Add Webhook</Button>
            </div>
          ) : (
            <div className="space-y-3">
              {webhooks.map((wh) => (
                <div key={wh.id} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium">{wh.name}</p>
                        <span className={clsx("text-xs px-2 py-0.5 rounded-full", statusColors[wh.status])}>
                          {wh.status}
                        </span>
                        {!wh.is_active && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
                            paused
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5 font-mono break-all">{wh.url}</p>
                      <div className="flex items-center gap-2 mt-1.5">
                        <div className="flex flex-wrap gap-1">
                          {wh.events.slice(0, 3).map((ev) => (
                            <span key={ev} className="text-xs px-1.5 py-0.5 bg-blue-50 text-blue-600 rounded">{ev}</span>
                          ))}
                          {wh.events.length > 3 && (
                            <span className="text-xs px-1.5 py-0.5 bg-gray-50 text-gray-500 rounded">+{wh.events.length - 3}</span>
                          )}
                        </div>
                        <span className="text-xs text-gray-400">
                          {wh.consecutive_failures > 0 && `${wh.consecutive_failures} failures · `}
                          {wh.last_success_at ? `Last OK: ${formatDate(wh.last_success_at)}` : "Never tested"}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1 ml-4 shrink-0">
                      <Button variant="ghost" size="sm" onClick={() => handleTest(wh.id)} loading={testingId === wh.id}>
                        Test
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => setLogsWebhookId(wh.id)}>
                        Logs
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => { setEditing(wh); setShowForm(false) }}>
                        Edit
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => handleToggleActive(wh)}>
                        {wh.is_active ? "Pause" : "Resume"}
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => handleDelete(wh.id)}>
                        Delete
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
