"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import * as unlearningApi from "@/lib/api/unlearning"

export default function NewUnlearningRequestPage() {
  const router = useRouter()
  const [modelId, setModelId] = useState("")
  const [targetDataIds, setTargetDataIds] = useState("")
  const [priority, setPriority] = useState<"low" | "medium" | "high" | "critical">("medium")
  const [regulatory, setRegulatory] = useState("gdpr")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setLoading(true)

    const ids = targetDataIds
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean)

    if (ids.length === 0) {
      setError("Enter at least one data ID")
      setLoading(false)
      return
    }

    try {
      const result = await unlearningApi.createRequest({
        model_id: modelId,
        target_data_ids: ids,
        priority,
        regulatory,
      })
      router.push(`/dashboard/unlearning/${result.id}`)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create request")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">New Unlearning Request</h1>
        <p className="text-sm text-[var(--text-secondary)] mt-1">Submit a data deletion request for the Right to be Forgotten</p>
      </div>

      <Card>
        <CardHeader><h3 className="text-lg font-semibold">Request Details</h3></CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4 max-w-lg">
            <Input
              id="model-id"
              label="Model ID"
              value={modelId}
              onChange={(e) => setModelId(e.target.value)}
              placeholder="Enter model identifier"
              required
            />

            <div>
              <label htmlFor="target-ids" className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
                Target Data IDs
              </label>
              <textarea
                id="target-ids"
                value={targetDataIds}
                onChange={(e) => setTargetDataIds(e.target.value)}
                placeholder="One ID per line&#10;data_000001&#10;data_000002"
                rows={5}
                className="w-full rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] text-[var(--text-primary)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)] focus:border-[var(--brand)]"
                required
              />
              <p className="text-xs text-[var(--text-tertiary)] mt-1">Enter one data ID per line</p>
            </div>

            <div>
              <label htmlFor="priority" className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
                Priority
              </label>
              <select
                id="priority"
                value={priority}
                onChange={(e) => setPriority(e.target.value as typeof priority)}
                className="w-full rounded-lg border border-[var(--border-default)] px-3 py-2 text-sm bg-[var(--bg-surface)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>

            <div>
              <label htmlFor="regulatory" className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
                Regulatory Framework
              </label>
              <select
                id="regulatory"
                value={regulatory}
                onChange={(e) => setRegulatory(e.target.value)}
                className="w-full rounded-lg border border-[var(--border-default)] px-3 py-2 text-sm bg-[var(--bg-surface)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              >
                <option value="gdpr">GDPR</option>
                <option value="ccpa">CCPA</option>
                <option value="hipaa">HIPAA</option>
                <option value="ai_act">EU AI Act</option>
              </select>
            </div>

            {error && <p className="text-sm text-[var(--danger)]">{error}</p>}

            <div className="flex gap-3">
              <Button type="submit" loading={loading}>Submit Request</Button>
              <Button type="button" variant="outline" onClick={() => router.back()}>Cancel</Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
