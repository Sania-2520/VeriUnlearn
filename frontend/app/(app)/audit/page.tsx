"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ScrollText, ShieldCheck, ShieldAlert, Link2 } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { timeAgo } from "@/lib/utils";

interface Event {
  id: string;
  event_type: string;
  actor: string;
  subject: string | null;
  certificate_id: string | null;
  prev_hash: string | null;
  event_hash: string;
  payload: Record<string, unknown>;
  created_at: string | null;
}

export default function AuditPage() {
  const { data: trail } = useQuery<{ events: Event[] }>({
    queryKey: ["audit"],
    queryFn: () => api.get("/api/v1/audit?limit=200"),
  });

  const { data: chain, refetch, isFetching } = useQuery<{ verified: boolean; event_count: number; broken_event_id: string | null }>({
    queryKey: ["audit-verify"],
    queryFn: () => api.get("/api/v1/audit/verify"),
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Immutable Audit Trail</h1>
          <p className="mt-1 text-sm text-slate-500">
            Every event is chained by hash to the previous one — tamper detection recomputes the whole chain.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {chain && (
            <Badge tone={chain.verified ? "emerald" : "rose"} className="px-3 py-1.5">
              {chain.verified ? <ShieldCheck className="h-3.5 w-3.5" /> : <ShieldAlert className="h-3.5 w-3.5" />}
              {chain.verified ? `${chain.event_count} events · chain intact` : "TAMPERED"}
            </Badge>
          )}
          <Button variant="outline" size="sm" onClick={() => refetch()} loading={isFetching}>
            Re-verify chain
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ScrollText className="h-4 w-4 text-cyan-400" /> Event log
          </CardTitle>
        </CardHeader>
        <div className="relative space-y-0">
          {(trail?.events ?? []).map((e, i) => (
            <motion.div
              key={e.id}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: Math.min(i * 0.02, 0.6) }}
              className="relative flex gap-4 border-b border-slate-800/50 px-5 py-3.5"
            >
              <div className="flex flex-col items-center pt-1">
                <span className={`h-2.5 w-2.5 rounded-full ${i === 0 ? "bg-cyan-400" : "bg-slate-600"}`} />
                {i < (trail?.events.length ?? 0) - 1 && <span className="mt-1 h-full w-px bg-slate-800" />}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="mono text-xs font-semibold text-cyan-300">{e.event_type}</span>
                  <span className="text-xs text-slate-500">by {e.actor}</span>
                  {e.subject && <Badge tone="slate">{e.subject}</Badge>}
                  <span className="ml-auto text-xs text-slate-500">{timeAgo(e.created_at)}</span>
                </div>
                {e.certificate_id && (
                  <p className="mono mt-1 text-[11px] text-violet-300">cert {e.certificate_id.slice(0, 12)}…</p>
                )}
                <div className="mono mt-1.5 flex flex-wrap items-center gap-2 text-[11px] text-slate-600">
                  <span className="flex items-center gap-1">
                    <Link2 className="h-3 w-3" /> {e.prev_hash ? e.prev_hash.slice(0, 16) + "…" : "genesis"}
                  </span>
                  <span>→</span>
                  <span className="text-slate-500">{e.event_hash.slice(0, 16)}…</span>
                </div>
              </div>
            </motion.div>
          ))}
          {(trail?.events ?? []).length === 0 && (
            <p className="py-10 text-center text-sm text-slate-500">No audit events recorded yet.</p>
          )}
        </div>
      </Card>
    </div>
  );
}
