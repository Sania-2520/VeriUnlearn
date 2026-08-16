"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Scale,
  AlertTriangle,
  Timer,
  ArrowRight,
  ShieldCheck,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  AreaChart,
  Area,
} from "recharts";
import { api } from "@/lib/api";
import { StatCard } from "@/components/ui/stat";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge, statusTone } from "@/components/ui/badge";
import { Table, THead, Th, Td, TRow } from "@/components/ui/table";
import { Spinner } from "@/components/ui/progress";
import { formatSeconds, timeAgo } from "@/lib/utils";

type Overview = {
  gdpr: { score: number; status: string };
  dpdp: { score: number; status: string };
  risk: { score: number; level: string };
  requests: { total: number; completed: number; failed: number; pending: number; avg_deletion_seconds: number | null };
  certificates: { total: number; valid: number; invalid: number };
  audit_chain: { verified: boolean; event_count: number };
};

export default function DashboardPage() {
  const { data: overview, isLoading } = useQuery<Overview>({
    queryKey: ["compliance-overview"],
    queryFn: () => api.get("/api/v1/compliance/overview"),
  });

  const { data: certs } = useQuery<Record<string, unknown>[]>({
    queryKey: ["certificates"],
    queryFn: () => api.get("/api/v1/certificates?limit=6"),
  });

  if (isLoading || !overview) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  const barData = [
    { name: "Completed", count: overview.requests.completed, fill: "#34d399" },
    { name: "Pending", count: overview.requests.pending, fill: "#fbbf24" },
    { name: "Failed", count: overview.requests.failed, fill: "#f87171" },
  ];

  const trendData = [
    { day: "Mon", deletions: 3, verifications: 2 },
    { day: "Tue", deletions: 5, verifications: 4 },
    { day: "Wed", deletions: 2, verifications: 2 },
    { day: "Thu", deletions: 8, verifications: 7 },
    { day: "Fri", deletions: 4, verifications: 4 },
    { day: "Sat", deletions: 1, verifications: 1 },
    { day: "Sun", deletions: 2, verifications: 2 },
  ];

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold tracking-tight">Command Center</h1>
        <p className="mt-1 text-sm text-slate-500">
          Real-time posture of your unlearning pipeline and compliance obligations.
        </p>
      </motion.div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="GDPR Score"
          value={overview.gdpr.score}
          icon={<Scale className="h-5 w-5" />}
          sub={`${overview.gdpr.status}`}
          accent="text-emerald-400"
        />
        <StatCard
          label="DPDP Score"
          value={overview.dpdp.score}
          icon={<ShieldCheck className="h-5 w-5" />}
          sub={overview.dpdp.status}
          accent="text-cyan-400"
        />
        <StatCard
          label="Risk"
          value={overview.risk.score}
          icon={<AlertTriangle className="h-5 w-5" />}
          sub={`${overview.risk.level} exposure`}
          accent={overview.risk.level === "low" ? "text-emerald-400" : overview.risk.level === "medium" ? "text-amber-400" : "text-rose-400"}
        />
        <StatCard
          label="Avg. Deletion"
          value={formatSeconds(overview.requests.avg_deletion_seconds)}
          icon={<Timer className="h-5 w-5" />}
          sub={`${overview.requests.total} total requests`}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Deletion Requests</CardTitle>
            <Badge tone="cyan">{overview.audit_chain.event_count} audit events</Badge>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={barData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" stroke="#64748b" fontSize={12} />
                <YAxis allowDecimals={false} stroke="#64748b" fontSize={12} />
                <Tooltip
                  cursor={{ fill: "rgba(34,211,238,0.06)" }}
                  contentStyle={{ background: "#0a0f1c", border: "1px solid #1e293b", borderRadius: 8 }}
                />
                <Bar dataKey="count" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Weekly Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={trendData}>
                <defs>
                  <linearGradient id="del" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="#22d3ee" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="day" stroke="#64748b" fontSize={12} />
                <YAxis allowDecimals={false} stroke="#64748b" fontSize={12} />
                <Tooltip contentStyle={{ background: "#0a0f1c", border: "1px solid #1e293b", borderRadius: 8 }} />
                <Area type="monotone" dataKey="deletions" stroke="#22d3ee" fill="url(#del)" />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Certificate Integrity</CardTitle>
            <Badge tone={overview.audit_chain.verified ? "emerald" : "rose"}>
              {overview.audit_chain.verified ? "chain intact" : "tampered"}
            </Badge>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[
                { label: "Certificates issued", value: overview.certificates.total },
                { label: "Valid", value: overview.certificates.valid },
                { label: "Invalid", value: overview.certificates.invalid },
                { label: "Audit events", value: overview.audit_chain.event_count },
              ].map((row) => (
                <div key={row.label} className="flex items-center justify-between border-b border-slate-800/50 pb-2 text-sm">
                  <span className="text-slate-400">{row.label}</span>
                  <span className="mono font-semibold text-cyan-300">{row.value}</span>
                </div>
              ))}
            </div>
            <Link href="/compliance" className="mt-4 inline-flex items-center gap-1 text-sm text-cyan-400 hover:underline">
              Open compliance <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Latest Certificates</CardTitle>
          <Link href="/certificates" className="flex items-center gap-1 text-sm text-cyan-400 hover:underline">
            View all <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </CardHeader>
        <Table>
          <THead>
            <tr>
              <Th>Certificate</Th>
              <Th>Subject</Th>
              <Th>Type</Th>
              <Th>Method</Th>
              <Th>Records</Th>
              <Th>Status</Th>
              <Th>Issued</Th>
            </tr>
          </THead>
          <tbody>
            {(certs ?? []).map((c) => (
              <TRow key={c.id as string}>
                <Td className="mono text-xs text-cyan-300">{(c.id as string).slice(0, 8)}</Td>
                <Td>{c.subject_user_id as string}</Td>
                <Td>{c.deletion_type as string}</Td>
                <Td className="mono text-xs">{c.method as string}</Td>
                <Td>{c.deleted_record_count as number}</Td>
                <Td>
                  <Badge tone={statusTone(c.verification_status as string)}>{c.verification_status as string}</Badge>
                </Td>
                <Td className="text-xs text-slate-500">{timeAgo(c.created_at as string)}</Td>
              </TRow>
            ))}
            {(certs ?? []).length === 0 && (
              <TRow>
                <Td colSpan={7} className="py-8 text-center text-slate-500">
                  No certificates yet — run a deletion from the{" "}
                  <Link href="/privacy" className="text-cyan-400 hover:underline">
                    Privacy Auditor
                  </Link>
                  .
                </Td>
              </TRow>
            )}
          </tbody>
        </Table>
      </Card>
    </div>
  );
}
