"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import AuthGuard from "../../components/AuthGuard";
import Navbar from "../../components/Navbar";

interface User {
  id: number;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

interface AuditEntry {
  id: number;
  event_type: string;
  event_data: Record<string, unknown>;
  user_id: number | null;
  created_at: string;
}

interface AuditResponse {
  entries: AuditEntry[];
  total: number;
}

const authHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem("access_token")}`,
  "Content-Type": "application/json",
});

type Tab = "users" | "audit";

export default function AdminPage() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<Tab>("users");

  const { data: users = [], isLoading: usersLoading } = useQuery<User[]>({
    queryKey: ["admin", "users"],
    queryFn: async () => {
      const res = await fetch("/api/admin/users", { headers: authHeaders() });
      if (!res.ok) throw new Error("Failed to fetch users");
      return res.json();
    },
  });

  const { data: audit, isLoading: auditLoading } = useQuery<AuditResponse>({
    queryKey: ["admin", "audit"],
    queryFn: async () => {
      const res = await fetch("/api/admin/audit-log?limit=100", { headers: authHeaders() });
      if (!res.ok) throw new Error("Failed to fetch audit log");
      return res.json();
    },
    enabled: tab === "audit",
  });

  const updateRole = useMutation({
    mutationFn: async ({ userId, role }: { userId: number; role: string }) => {
      const res = await fetch(`/api/admin/users/${userId}/role?role=${role}`, {
        method: "PATCH",
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error("Failed to update role");
      return res.json();
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "users"] }),
  });

  const deleteUser = useMutation({
    mutationFn: async (userId: number) => {
      const res = await fetch(`/api/admin/users/${userId}`, {
        method: "DELETE",
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error("Failed to delete user");
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "users"] }),
  });

  return (
    <AuthGuard>
      <Navbar />
      <main className="min-h-screen p-8 max-w-6xl mx-auto">
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Admin Panel</h1>
              <p className="text-gray-500 mt-1">User and system management</p>
            </div>
            <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
              <button
                onClick={() => setTab("users")}
                className={`px-4 py-1.5 text-sm rounded-md ${tab === "users" ? "bg-white shadow-sm text-gray-900" : "text-gray-500"}`}
              >
                Users
              </button>
              <button
                onClick={() => setTab("audit")}
                className={`px-4 py-1.5 text-sm rounded-md ${tab === "audit" ? "bg-white shadow-sm text-gray-900" : "text-gray-500"}`}
              >
                Audit Log
              </button>
            </div>
          </div>

          {tab === "users" && (
            usersLoading ? (
              <p className="text-gray-400">Loading...</p>
            ) : (
              <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200">
                      <th className="text-left px-4 py-3 font-medium text-gray-500">ID</th>
                      <th className="text-left px-4 py-3 font-medium text-gray-500">Username</th>
                      <th className="text-left px-4 py-3 font-medium text-gray-500">Email</th>
                      <th className="text-left px-4 py-3 font-medium text-gray-500">Role</th>
                      <th className="text-left px-4 py-3 font-medium text-gray-500">Status</th>
                      <th className="text-right px-4 py-3 font-medium text-gray-500">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((u) => (
                      <tr key={u.id} className="border-b border-gray-100">
                        <td className="px-4 py-3 text-gray-900">{u.id}</td>
                        <td className="px-4 py-3 text-gray-900">{u.username}</td>
                        <td className="px-4 py-3 text-gray-500">{u.email}</td>
                        <td className="px-4 py-3">
                          <select
                            value={u.role}
                            onChange={(e) => updateRole.mutate({ userId: u.id, role: e.target.value })}
                            className="text-xs border border-gray-200 rounded px-1 py-0.5"
                          >
                            <option value="user">user</option>
                            <option value="admin">admin</option>
                            <option value="auditor">auditor</option>
                          </select>
                        </td>
                        <td className="px-4 py-3">
                          {u.is_active ? (
                            <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">Active</span>
                          ) : (
                            <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">Inactive</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={() => { if (confirm(`Delete user ${u.username}?`)) deleteUser.mutate(u.id); }}
                            className="text-xs text-red-500 hover:text-red-600 font-medium"
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          )}

          {tab === "audit" && (
            auditLoading ? (
              <p className="text-gray-400">Loading...</p>
            ) : (
              <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
                <div className="px-4 py-3 border-b border-gray-200 bg-gray-50 text-sm text-gray-500">
                  {audit?.total ?? 0} total entries
                </div>
                <div className="divide-y divide-gray-100 max-h-[600px] overflow-y-auto">
                  {(audit?.entries ?? []).length === 0 ? (
                    <div className="p-8 text-center text-gray-400">No audit entries yet</div>
                  ) : (
                    (audit?.entries ?? []).map((entry) => (
                      <div key={entry.id} className="px-4 py-3 text-sm">
                        <div className="flex items-center justify-between">
                          <span className="font-medium text-gray-900">{entry.event_type}</span>
                          <span className="text-xs text-gray-400">
                            {new Date(entry.created_at).toLocaleString()}
                          </span>
                        </div>
                        <div className="mt-1 text-xs text-gray-500 font-mono whitespace-pre-wrap">
                          {JSON.stringify(entry.event_data, null, 2)}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )
          )}
        </div>
      </main>
    </AuthGuard>
  );
}
