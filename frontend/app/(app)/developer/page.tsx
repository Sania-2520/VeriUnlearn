"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { TerminalSquare, KeyRound, Plus, Copy, Ban, Eye, EyeOff } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/ui/stat";
import { Spinner } from "@/components/ui/progress";
import { timeAgo } from "@/lib/utils";

interface APIKey {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  is_active: boolean;
  expires_at: string | null;
  quota_per_minute: number;
  requests_count: number;
  last_used_at: string | null;
  usage: { at: string; path: string | null; status: number | null }[];
}

export default function DeveloperPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [quota, setQuota] = useState(60);
  const [notice, setNotice] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const [newKey, setNewKey] = useState<string | null>(null);
  const [showUsage, setShowUsage] = useState<string | null>(null);

  const keys = useQuery<{ api_keys: APIKey[] }>({
    queryKey: ["api-keys"],
    queryFn: () => api.get("/api/v1/api-keys"),
  });

  const create = useMutation({
    mutationFn: () =>
      api.post<{ api_key: { key: string; name: string; quota_per_minute: number } }>("/api/v1/api-keys", {
        name,
        quota_per_minute: quota,
        expires_in_days: 90,
      }),
    onSuccess: (d) => {
      setNewKey(d.api_key.key);
      setNotice({ kind: "ok", text: "Key issued — copy it now, it is shown only once." });
      setName("");
      void qc.invalidateQueries({ queryKey: ["api-keys"] });
    },
    onError: (e) => setNotice({ kind: "err", text: e instanceof ApiError ? e.message : "Issuance failed" }),
  });

  const revoke = useMutation({
    mutationFn: (id: string) => api.post(`/api/v1/api-keys/${id}/revoke`),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["api-keys"] }),
  });

  const items = keys.data?.api_keys ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Developer Portal</h1>
        <p className="mt-1 text-sm text-slate-500">
          Programmatic API keys with per-key quotas, rate limiting, usage tracking and request logs.
        </p>
      </div>

      {notice && (
        <div
          className={`rounded-lg border px-4 py-3 text-sm ${
            notice.kind === "ok" ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-rose-500/30 bg-rose-500/10 text-rose-300"
          }`}
        >
          {notice.text}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Active keys" value={items.filter((k) => k.is_active).length} icon={<KeyRound className="h-4 w-4" />} accent="text-cyan-400" />
        <StatCard label="Total requests" value={items.reduce((a, k) => a + k.requests_count, 0)} icon={<TerminalSquare className="h-4 w-4" />} accent="text-violet-400" />
        <StatCard label="Default quota" value={`${quota}/min`} icon={<KeyRound className="h-4 w-4" />} accent="text-emerald-400" />
      </div>

      {newKey && (
        <Card className="border-emerald-500/30">
          <CardHeader>
            <CardTitle className="text-emerald-300">Your new API key</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <code className="mono flex-1 overflow-x-auto rounded-lg border border-emerald-500/30 bg-slate-950/60 px-3 py-2 text-sm text-emerald-300">
                {newKey}
              </code>
              <Button variant="outline" size="sm" onClick={() => { navigator.clipboard?.writeText(newKey); setNotice({ kind: "ok", text: "Copied!" }); }}>
                <Copy className="h-3.5 w-3.5" /> Copy
              </Button>
            </div>
            <p className="mt-2 text-xs text-slate-500">
              Send it as <code className="mono rounded bg-slate-800 px-1 py-0.5">X-API-Key: {newKey.slice(0, 8)}…</code>
            </p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>
            <span className="flex items-center gap-2"><Plus className="h-4 w-4 text-cyan-400" /> Issue a key</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3">
          <div className="flex-1">
            <label className="mb-1 block text-[11px] uppercase tracking-wider text-slate-500">Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. ci-pipeline"
              className="w-full rounded-lg border border-slate-700 bg-slate-900/50 px-3 py-2 text-sm text-slate-200 outline-none focus:border-cyan-400/50"
            />
          </div>
          <div>
            <label className="mb-1 block text-[11px] uppercase tracking-wider text-slate-500">Quota / min</label>
            <input
              type="number"
              value={quota}
              onChange={(e) => setQuota(Number(e.target.value))}
              className="w-28 rounded-lg border border-slate-700 bg-slate-900/50 px-3 py-2 text-sm text-slate-200 outline-none focus:border-cyan-400/50"
            />
          </div>
          <Button disabled={!name.trim()} onClick={() => create.mutate()} loading={create.isPending}>
            <Plus className="h-4 w-4" /> Issue key
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Keys & usage</CardTitle>
        </CardHeader>
        <CardContent>
          {keys.isLoading ? (
            <div className="flex justify-center py-8"><Spinner /></div>
          ) : items.length === 0 ? (
            <p className="py-8 text-center text-sm text-slate-500">No keys yet — issue one above.</p>
          ) : (
            <div className="space-y-2">
              {items.map((k, i) => (
                <motion.div
                  key={k.id}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: Math.min(i * 0.03, 0.4) }}
                  className="rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-3"
                >
                  <div className="flex flex-wrap items-center gap-3">
                    <span className={`h-2 w-2 rounded-full ${k.is_active ? "bg-emerald-400" : "bg-rose-400"}`} />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-slate-200">{k.name}</p>
                      <p className="mono text-xs text-slate-500">{k.key_prefix}…</p>
                    </div>
                    <Badge tone={k.is_active ? "emerald" : "rose"}>{k.is_active ? "active" : "revoked"}</Badge>
                    <Badge tone="slate">{k.quota_per_minute}/min</Badge>
                    <span className="mono text-xs text-slate-500">{k.requests_count} reqs</span>
                    <span className="ml-auto text-xs text-slate-500">{k.last_used_at ? `used ${timeAgo(k.last_used_at)}` : "never used"}</span>
                    <Button variant="outline" size="sm" onClick={() => setShowUsage(showUsage === k.id ? null : k.id)}>
                      {showUsage === k.id ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />} Usage
                    </Button>
                    {k.is_active && (
                      <Button variant="outline" size="sm" className="text-rose-300 hover:border-rose-500/40" onClick={() => revoke.mutate(k.id)}>
                        <Ban className="h-3.5 w-3.5" /> Revoke
                      </Button>
                    )}
                  </div>
                  {showUsage === k.id && (
                    <div className="mt-3 rounded-lg border border-slate-800 bg-slate-950/50 p-3">
                      {k.usage.length === 0 ? (
                        <p className="text-xs text-slate-500">No requests logged yet.</p>
                      ) : (
                        <div className="space-y-1">
                          {[...k.usage].reverse().map((u, j) => (
                            <div key={j} className="mono flex items-center gap-3 text-[11px]">
                              <span className="text-slate-500">{u.at?.replace("T", " ").slice(0, 19)}</span>
                              <span className="text-cyan-300">{u.path ?? "—"}</span>
                              <span className={u.status != null && u.status >= 400 ? "text-rose-300" : "text-emerald-300"}>{u.status ?? "—"}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </motion.div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
