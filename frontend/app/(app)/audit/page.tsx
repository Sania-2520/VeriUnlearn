"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { motion } from "framer-motion";
import { ScrollText, ShieldCheck, ShieldAlert, Link2, MessageSquare } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, THead, Th, Td, TRow } from "@/components/ui/table";
import { timeAgo } from "@/lib/utils";

interface ChatSession {
  session_id: string;
  name: string;
  content: string;
  sensitive_data: string;
  message_count: number;
  created_at: string | null;
  updated_at: string | null;
}

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

const SENSITIVE_TONES: Record<string, "rose" | "amber" | "violet" | "slate"> = {
  "personal name": "slate",
  email: "amber",
  phone: "amber",
  address: "amber",
  "date of birth": "amber",
  "credit card / financial": "rose",
  "government ID": "rose",
  medical: "rose",
  "password / credentials": "rose",
  biometric: "rose",
  employment: "amber",
  education: "amber",
  legal: "rose",
  "business confidential": "rose",
  "government / military": "rose",
  "intellectual property": "violet",
  "security information": "violet",
  "personal communication": "amber",
  "location data": "amber",
  "children's data": "rose",
  "images / media": "rose",
  "source code secret": "rose",
  "customer / client data": "amber",
  "research data": "amber",
  "corporate credentials": "rose",
  "sensitive attribute": "violet",
  "recovery information": "rose",
  "payment documents": "rose",
  "device information": "slate",
  "access logs": "slate",
  "meeting data": "amber",
  "regulated data": "rose",
  "customer/employee ID": "slate",
};

export default function AuditPage() {
  const [tab, setTab] = useState<"chats" | "events">("chats");

  const { data: chats } = useQuery<{ sessions: ChatSession[] }>({
    queryKey: ["chat-sessions"],
    queryFn: () => api.get("/api/v1/assistant/sessions"),
    refetchInterval: 3000,
  });

  const { data: trail } = useQuery<{ events: Event[] }>({
    queryKey: ["audit"],
    queryFn: () => api.get("/api/v1/audit?limit=200"),
  });

  const { data: chain, refetch, isFetching } = useQuery<{ verified: boolean; event_count: number; broken_event_id: string | null }>({
    queryKey: ["audit-verify"],
    queryFn: () => api.get("/api/v1/audit/verify"),
  });

  const sessions = chats?.sessions ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Audit Trail</h1>
          <p className="mt-1 text-sm text-slate-500">
            Every chat with the Assistant is logged in real time with its transcript and detected sensitive data.
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/60 p-1">
          <button
            onClick={() => setTab("chats")}
            className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              tab === "chats" ? "bg-cyan-500/15 text-cyan-300" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Chat history
          </button>
          <button
            onClick={() => setTab("events")}
            className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              tab === "events" ? "bg-cyan-500/15 text-cyan-300" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Event log
          </button>
        </div>
      </div>

      {tab === "chats" && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-cyan-400" /> Chat history
              <Badge tone="slate">{sessions.length}</Badge>
            </CardTitle>
          </CardHeader>
          <Table>
            <THead>
              <tr>
                <Th>Chat ID</Th>
                <Th>Chat name</Th>
                <Th>Content</Th>
                <Th>Sensitive data</Th>
                <Th></Th>
              </tr>
            </THead>
            <tbody>
              {sessions.map((s) => (
                <TRow key={s.session_id}>
                  <Td>
                    <code className="mono text-[11px] text-cyan-300">{s.session_id.slice(0, 8)}…{s.session_id.slice(-4)}</code>
                    <p className="mono mt-0.5 text-[10px] text-slate-600">{timeAgo(s.updated_at)}</p>
                  </Td>
                  <Td className="max-w-[220px]">
                    <p className="truncate font-medium text-slate-100">{s.name}</p>
                    <p className="mono mt-0.5 text-[10px] text-slate-600">{s.message_count} messages</p>
                  </Td>
                  <Td className="max-w-[380px]">
                    <p className="line-clamp-3 whitespace-pre-wrap text-xs leading-relaxed text-slate-400">
                      {s.content || "—"}
                    </p>
                  </Td>
                  <Td>
                    {s.sensitive_data ? (
                      <div className="flex max-w-[260px] flex-wrap gap-1">
                        {s.sensitive_data.split(",").map((c) => (
                          <Badge key={c} tone={SENSITIVE_TONES[c.trim()] ?? "slate"}>
                            {c.trim()}
                          </Badge>
                        ))}
                      </div>
                    ) : (
                      <span className="text-xs text-slate-600">None detected</span>
                    )}
                  </Td>
                  <Td>
                    <Link href={`/assistant?session=${encodeURIComponent(s.session_id)}`}>
                      <Button variant="ghost" size="sm">Open chat</Button>
                    </Link>
                  </Td>
                </TRow>
              ))}
            </tbody>
          </Table>
          {sessions.length === 0 && (
            <p className="py-10 text-center text-sm text-slate-500">
              No chats yet — start a conversation with the Assistant and it will appear here in real time.
            </p>
          )}
        </Card>
      )}

      {tab === "events" && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ScrollText className="h-4 w-4 text-cyan-400" /> Event log
              <Badge tone={chain?.verified ? "emerald" : "rose"} className="px-3 py-1.5">
                {chain?.verified ? (
                  <>
                    <ShieldCheck className="h-3.5 w-3.5" />
                    {chain.event_count} events · chain intact
                  </>
                ) : (
                  <>
                    <ShieldAlert className="h-3.5 w-3.5" />
                    TAMPERED
                  </>
                )}
              </Badge>
            </CardTitle>
            <div className="flex justify-end">
              <Button variant="outline" size="sm" onClick={() => refetch()} loading={isFetching}>
                Re-verify chain
              </Button>
            </div>
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
      )}
    </div>
  );
}