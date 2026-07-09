"use client"

import { useState, useEffect, useCallback } from "react"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import * as authApi from "@/lib/api/auth"
import type { Session } from "@/lib/types/auth"
import { formatDate } from "@/lib/utils"

export default function SessionsPage() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  const loadSessions = useCallback(async () => {
    try {
      const res = await authApi.listSessions()
      setSessions(res.data)
    } catch {
      setError("Failed to load sessions")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  const handleRevoke = async (sessionId: string) => {
    try {
      await authApi.revokeSession(sessionId)
      await loadSessions()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to revoke session")
    }
  }

  const handleRevokeAll = async () => {
    if (!confirm("Revoke all sessions? You will be signed out.")) return
    try {
      await authApi.revokeAllSessions()
      await authApi.logout(true)
      window.location.href = "/auth/login"
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to revoke sessions")
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Sessions</h1>
          <p className="text-sm text-gray-500 mt-1">Manage your active sessions</p>
        </div>
        <Button variant="danger" onClick={handleRevokeAll}>
          Revoke All
        </Button>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <p className="text-sm text-gray-500">Loading...</p>
          ) : sessions.length === 0 ? (
            <p className="text-sm text-gray-500">No active sessions</p>
          ) : (
            <div className="space-y-3">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium">
                        {session.user_agent ? session.user_agent.split(" ")[0] : "Unknown device"}
                      </p>
                      {session.is_current && (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">
                          Current
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-1">
                      {session.ip_address && `${session.ip_address} · `}
                      Created {formatDate(session.created_at)}
                      {session.expires_at && ` · Expires ${formatDate(session.expires_at)}`}
                    </p>
                  </div>
                  {!session.is_current && (
                    <Button variant="ghost" size="sm" onClick={() => handleRevoke(session.id)}>
                      Revoke
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
