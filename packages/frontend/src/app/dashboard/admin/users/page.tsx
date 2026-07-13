"use client"

import { useState, useEffect, useCallback } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { clsx } from "clsx"
import * as adminApi from "@/lib/api/admin"
import type { User } from "@/lib/types/auth"
import { formatDate } from "@/lib/utils"

const roleColors: Record<string, string> = {
  admin: "bg-purple-100 text-purple-700",
  compliance_officer: "bg-blue-100 text-blue-700",
  unlearning_auditor: "bg-cyan-100 text-cyan-700",
  member: "bg-green-100 text-green-700",
  viewer: "bg-gray-100 text-gray-600",
}

const roles = ["admin", "compliance_officer", "unlearning_auditor", "member", "viewer"]

export default function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [roleFilter, setRoleFilter] = useState("")
  const [editingUser, setEditingUser] = useState<string | null>(null)
  const [editRole, setEditRole] = useState("")
  const [editActive, setEditActive] = useState(true)
  const [saving, setSaving] = useState(false)

  const loadUsers = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const params: Record<string, unknown> = { page, page_size: 20 }
      if (roleFilter) params.role = roleFilter
      const res = await adminApi.listUsers(params as { page?: number; page_size?: number; role?: string })
      setUsers(res.data)
      setTotal(res.meta.total)
      setTotalPages(Math.ceil(res.meta.total / res.meta.page_size))
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load users")
    } finally {
      setLoading(false)
    }
  }, [page, roleFilter])

  useEffect(() => { loadUsers() }, [loadUsers])

  const startEdit = (user: User) => {
    setEditingUser(user.id)
    setEditRole(user.role)
    setEditActive(user.is_active ?? true)
  }

  const handleSave = async () => {
    if (!editingUser) return
    setSaving(true)
    try {
      await adminApi.updateUser(editingUser, { role: editRole, is_active: editActive })
      setEditingUser(null)
      await loadUsers()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to update user")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Users</h1>
          <p className="text-sm text-gray-500 mt-1">Manage user accounts and roles</p>
        </div>
        <p className="text-sm text-gray-500">{total} total users</p>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-3 mb-4">
            <select
              value={roleFilter}
              onChange={(e) => { setRoleFilter(e.target.value); setPage(1) }}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm bg-white"
            >
              <option value="">All Roles</option>
              {roles.map((r) => (
                <option key={r} value={r}>{r.replace("_", " ")}</option>
              ))}
            </select>
          </div>

          {error && <p className="text-sm text-red-600 mb-4">{error}</p>}

          {loading ? (
            <p className="text-sm text-gray-500 py-8 text-center">Loading...</p>
          ) : users.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500 font-medium">No users found</p>
            </div>
          ) : (
            <div className="space-y-2">
              {users.map((user) => (
                <div key={user.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium">{user.full_name || "—"}</p>
                      <span className={clsx("text-xs px-2 py-0.5 rounded-full", roleColors[user.role] || "bg-gray-100")}>
                        {user.role.replace("_", " ")}
                      </span>
                      {!user.is_active && (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-600">inactive</span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">{user.email}</p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {user.mfa_enabled && "MFA · "}
                      {user.is_email_verified ? "Verified" : "Unverified"}
                      {" · Joined "}{formatDate(user.created_at)}
                    </p>
                  </div>

                  {editingUser === user.id ? (
                    <div className="flex items-center gap-2 ml-4 shrink-0">
                      <select
                        value={editRole}
                        onChange={(e) => setEditRole(e.target.value)}
                        className="rounded-lg border border-gray-300 px-2 py-1 text-sm bg-white"
                      >
                        {roles.map((r) => (
                          <option key={r} value={r}>{r.replace("_", " ")}</option>
                        ))}
                      </select>
                      <label className="flex items-center gap-1 text-xs">
                        <input type="checkbox" checked={editActive} onChange={(e) => setEditActive(e.target.checked)}
                          className="rounded border-gray-300 text-blue-600" />
                        Active
                      </label>
                      <Button size="sm" onClick={handleSave} loading={saving}>Save</Button>
                      <Button size="sm" variant="ghost" onClick={() => setEditingUser(null)}>Cancel</Button>
                    </div>
                  ) : (
                    <Button size="sm" variant="ghost" onClick={() => startEdit(user)} className="ml-4 shrink-0">
                      Edit
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-6">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
                Previous
              </Button>
              <span className="text-sm text-gray-500">Page {page} of {totalPages}</span>
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
