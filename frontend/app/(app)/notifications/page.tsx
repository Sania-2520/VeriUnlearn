"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Bell, CheckCheck, FileCheck2, Circle } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatCard } from "@/components/ui/stat";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/progress";
import { timeAgo } from "@/lib/utils";

interface Notification {
  id: string;
  event_type: string;
  channel: string;
  title: string;
  body: string;
  payload: Record<string, unknown>;
  is_read: boolean;
  delivered: boolean;
  created_at: string | null;
}

const eventMeta: Record<string, { label: string; tone: "cyan" | "emerald" | "amber" | "rose" | "violet" }> = {
  "deletion.completed": { label: "Deletion", tone: "emerald" },
  "verification.completed": { label: "Verification", tone: "cyan" },
  "certificate.ready": { label: "Certificate", tone: "violet" },
  "experiment.finished": { label: "Experiment", tone: "amber" },
  "system.error": { label: "System error", tone: "rose" },
};

export default function NotificationsPage() {
  const qc = useQueryClient();
  const list = useQuery<{ notifications: Notification[]; unread: number }>({
    queryKey: ["notifications"],
    queryFn: () => api.get("/api/v1/notifications"),
  });

  const markRead = useMutation({
    mutationFn: (id: string) => api.post(`/api/v1/notifications/${id}/read`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const markAll = useMutation({
    mutationFn: () => api.post("/api/v1/notifications/read-all"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const items = list.data?.notifications ?? [];
  const unread = list.data?.unread ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Notifications</h1>
          <p className="mt-1 text-sm text-slate-500">
            Deletion completions, verification results, certificates, experiments and system events.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => markAll.mutate()} disabled={unread === 0 || markAll.isPending}>
          <CheckCheck className="h-3.5 w-3.5" /> Mark all read
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Total" value={items.length} icon={<Bell className="h-4 w-4" />} accent="text-cyan-400" />
        <StatCard label="Unread" value={unread} icon={<Circle className="h-4 w-4" />} accent="text-amber-400" />
        <StatCard label="Delivered (email)" value={items.filter((n) => n.delivered).length} icon={<FileCheck2 className="h-4 w-4" />} accent="text-emerald-400" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Inbox</CardTitle>
        </CardHeader>
        <CardContent>
          {list.isLoading ? (
            <div className="flex justify-center py-10"><Spinner /></div>
          ) : items.length === 0 ? (
            <p className="py-10 text-center text-sm text-slate-500">No notifications yet.</p>
          ) : (
            <div className="space-y-2">
              {items.map((n, i) => {
                const meta = eventMeta[n.event_type] ?? { label: n.event_type, tone: "slate" as const };
                return (
                  <motion.div
                    key={n.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: Math.min(i * 0.03, 0.5) }}
                    className={`flex flex-wrap items-start gap-3 rounded-xl border px-4 py-3 ${
                      n.is_read ? "border-slate-800/70 bg-slate-900/20" : "border-cyan-500/20 bg-cyan-500/5"
                    }`}
                  >
                    <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${n.is_read ? "bg-slate-600" : "bg-cyan-400"}`} />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge tone={meta.tone}>{meta.label}</Badge>
                        {n.channel === "email" && <Badge tone={n.delivered ? "emerald" : "amber"}>{n.delivered ? "email sent" : "email pending"}</Badge>}
                        <span className="ml-auto text-xs text-slate-500">{timeAgo(n.created_at)}</span>
                      </div>
                      <p className={`mt-1 text-sm ${n.is_read ? "text-slate-300" : "font-medium text-slate-100"}`}>{n.title}</p>
                      {n.body && <p className="mt-0.5 text-xs text-slate-500">{n.body}</p>}
                      {Object.keys(n.payload ?? {}).length > 0 && (
                        <p className="mono mt-1 text-[10px] text-slate-600">{JSON.stringify(n.payload)}</p>
                      )}
                    </div>
                    {!n.is_read && (
                      <Button size="sm" variant="outline" onClick={() => markRead.mutate(n.id)} disabled={markRead.isPending}>
                        <CheckCheck className="h-3.5 w-3.5" /> Mark read
                      </Button>
                    )}
                  </motion.div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
