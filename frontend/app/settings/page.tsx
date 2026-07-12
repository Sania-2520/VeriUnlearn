"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "../../store/auth";
import AuthGuard from "../../components/AuthGuard";
import Navbar from "../../components/Navbar";

interface ApiKey {
  id: number;
  name: string;
  prefix: string;
  scopes: string | null;
  is_active: boolean;
  last_used_at: string | null;
  created_at: string;
}

const authHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem("access_token")}`,
  "Content-Type": "application/json",
});

export default function SettingsPage() {
  const { user } = useAuthStore();
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [keyName, setKeyName] = useState("");
  const [createdKey, setCreatedKey] = useState<string | null>(null);

  const { data: apiKeys = [], isLoading } = useQuery<ApiKey[]>({
    queryKey: ["api-keys"],
    queryFn: async () => {
      const res = await fetch("/api/api-keys/", { headers: authHeaders() });
      if (!res.ok) throw new Error("Failed to fetch API keys");
      return res.json();
    },
  });

  const createKey = useMutation({
    mutationFn: async (name: string) => {
      const res = await fetch("/api/api-keys/", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ name }),
      });
      if (!res.ok) throw new Error("Failed to create key");
      return res.json();
    },
    onSuccess: (data) => {
      setCreatedKey(data.key);
      setShowCreate(false);
      setKeyName("");
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
    },
  });

  const revokeKey = useMutation({
    mutationFn: async (keyId: number) => {
      const res = await fetch(`/api/api-keys/${keyId}`, {
        method: "DELETE",
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error("Failed to revoke key");
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["api-keys"] }),
  });

  return (
    <AuthGuard>
      <Navbar />
      <main className="min-h-screen p-8 max-w-3xl mx-auto">
        <div className="space-y-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
            <p className="text-gray-500 mt-1">Account, API keys, and session</p>
          </div>

          <section className="rounded-xl border border-gray-200 bg-white p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Profile</h2>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
                  <input type="text" value={user?.username ?? ""} readOnly className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm bg-gray-50 text-gray-500" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                  <input type="email" value={user?.email ?? ""} readOnly className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm bg-gray-50 text-gray-500" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
                <span className="inline-block text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">{user?.role ?? "user"}</span>
              </div>
            </div>
          </section>

          <section className="rounded-xl border border-gray-200 bg-white p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">API Keys</h2>
              <button onClick={() => { setShowCreate(true); setCreatedKey(null); }} className="text-sm bg-primary-600 text-white px-4 py-1.5 rounded-lg hover:bg-primary-700">
                New Key
              </button>
            </div>

            {showCreate && (
              <div className="mb-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
                <div className="flex gap-3">
                  <input
                    type="text"
                    value={keyName}
                    onChange={(e) => setKeyName(e.target.value)}
                    placeholder="Key name (e.g. CI, dev)"
                    className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                  <button onClick={() => createKey.mutate(keyName)} disabled={!keyName.trim() || createKey.isPending}
                    className="rounded-lg bg-primary-600 px-4 py-2 text-sm text-white disabled:opacity-50">
                    Create
                  </button>
                  <button onClick={() => setShowCreate(false)} className="text-sm text-gray-500 px-2">Cancel</button>
                </div>
              </div>
            )}

            {createdKey && (
              <div className="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                <p className="text-sm font-medium text-yellow-800 mb-1">Key created — copy it now, you won't see it again:</p>
                <div className="flex gap-2">
                  <input type="text" value={createdKey} readOnly className="flex-1 rounded border border-yellow-300 px-3 py-2 text-xs font-mono bg-white" />
                  <button onClick={() => navigator.clipboard.writeText(createdKey)}
                    className="rounded-lg border border-yellow-300 px-3 py-2 text-sm hover:bg-yellow-100">
                    Copy
                  </button>
                </div>
              </div>
            )}

            {isLoading ? (
              <p className="text-gray-400 text-sm">Loading...</p>
            ) : apiKeys.length === 0 ? (
              <p className="text-gray-400 text-sm">No API keys created yet.</p>
            ) : (
              <div className="space-y-2">
                {apiKeys.map((k) => (
                  <div key={k.id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{k.name}</p>
                      <p className="text-xs text-gray-400 font-mono">{k.prefix}...</p>
                    </div>
                    <button onClick={() => { if (confirm('Revoke this key?')) revokeKey.mutate(k.id); }}
                      className="text-xs text-red-500 hover:text-red-600 font-medium">
                      Revoke
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="rounded-xl border border-gray-200 bg-white p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Session</h2>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Access Token</label>
              <div className="flex gap-2">
                <input type="password"
                  value={typeof window !== "undefined" ? (localStorage.getItem("access_token")?.slice(0, 20) + "...") : ""}
                  readOnly
                  className="flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-500 bg-gray-50 font-mono text-xs"
                />
                <button onClick={() => { const t = localStorage.getItem("access_token"); if (t) navigator.clipboard.writeText(t); }}
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50">
                  Copy
                </button>
              </div>
            </div>
          </section>
        </div>
      </main>
    </AuthGuard>
  );
}
