"use client"

import { useState, useEffect, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import * as authApi from "@/lib/api/auth"
import type { ApiKey, ApiKeyCreated } from "@/lib/types/auth"
import { formatDate } from "@/lib/utils"

export function ApiKeyManager() {
  const [keys, setKeys] = useState<ApiKey[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [newKeyName, setNewKeyName] = useState("")
  const [newKeyResult, setNewKeyResult] = useState<ApiKeyCreated | null>(null)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState("")

  const loadKeys = useCallback(async () => {
    try {
      const res = await authApi.listApiKeys()
      setKeys(res.data)
    } catch {
      setError("Failed to load API keys")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadKeys()
  }, [loadKeys])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setCreating(true)
    try {
      const result = await authApi.createApiKey({ name: newKeyName, scopes: ["*"] })
      setNewKeyResult(result)
      setNewKeyName("")
      setShowCreate(false)
      await loadKeys()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create API key")
    } finally {
      setCreating(false)
    }
  }

  const handleRevoke = async (keyId: string) => {
    if (!confirm("Revoke this API key? This cannot be undone.")) return
    try {
      await authApi.revokeApiKey(keyId)
      await loadKeys()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to revoke API key")
    }
  }

  if (newKeyResult) {
    return (
      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold">API Key Created</h3>
          <p className="text-sm text-[var(--warning)] font-medium">
            Copy this key now — you won&apos;t be able to see it again!
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="bg-[var(--bg-subtle)] rounded-lg p-4">
            <code className="text-sm font-mono break-all select-all">{newKeyResult.raw_key}</code>
          </div>
          <Button onClick={() => setNewKeyResult(null)}>Done</Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold">API Keys</h3>
            <p className="text-sm text-[var(--text-secondary)]">Manage API keys for programmatic access</p>
          </div>
          <Button size="sm" onClick={() => setShowCreate(!showCreate)}>
            {showCreate ? "Cancel" : "Create Key"}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && <p className="text-sm text-[var(--danger)]">{error}</p>}

        {showCreate && (
          <form onSubmit={handleCreate} className="flex gap-2 items-end">
            <Input
              id="key-name"
              label="Key Name"
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              placeholder="My API Key"
              required
            />
            <Button type="submit" loading={creating} className="mb-1">
              Create
            </Button>
          </form>
        )}

        {loading ? (
          <p className="text-sm text-[var(--text-secondary)]">Loading...</p>
        ) : keys.length === 0 ? (
          <p className="text-sm text-[var(--text-secondary)]">No API keys yet</p>
        ) : (
          <div className="space-y-2">
            {keys.map((key) => (
              <div key={key.id} className="flex items-center justify-between p-3 bg-[var(--bg-subtle)] rounded-lg">
                <div>
                  <p className="text-sm font-medium">{key.name}</p>
                  <p className="text-xs text-[var(--text-secondary)]">
                    {key.key_prefix}... | Created {formatDate(key.created_at)}
                    {key.last_used_at && ` | Last used ${formatDate(key.last_used_at)}`}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${key.is_active ? "bg-[var(--success-soft)] text-[var(--success)]" : "bg-[var(--danger-soft)] text-[var(--danger)]"}`}>
                    {key.is_active ? "Active" : "Revoked"}
                  </span>
                  {key.is_active && (
                    <Button variant="danger" size="sm" onClick={() => handleRevoke(key.id)}>
                      Revoke
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
